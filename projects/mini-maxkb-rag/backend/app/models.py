"""
业务数据模型。

这里定义 SQLite/PostgreSQL 共用的业务表。
它们和 MaxKB 源码中的模型是简化映射关系：

KnowledgeFolder -> KnowledgeFolderModel
Knowledge       -> KnowledgeModel
File            -> FileModel
Document        -> DocumentModel
Paragraph       -> ParagraphModel
Embedding       -> EmbeddingRefModel + Chroma 中的真实向量
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import EMBEDDING_DIMENSION, TASK_MAX_ATTEMPTS
from app.database import Base


# 文档处理状态暂时使用字符串常量，而不是数据库 Enum。
# SQLite 修改 Enum 约束比较麻烦；学习版先保持字段简单，等迁移到 PostgreSQL
# 和 Alembic 后，再根据需要收紧为数据库枚举。
DOCUMENT_STATUS_PENDING = "PENDING"
DOCUMENT_STATUS_PROCESSING = "PROCESSING"
DOCUMENT_STATUS_SUCCESS = "SUCCESS"
DOCUMENT_STATUS_FAILED = "FAILED"
DOCUMENT_STATUS_CANCELLED = "CANCELLED"

TASK_TYPE_DOCUMENT_INDEX = "DOCUMENT_INDEX"
TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_QUEUED = "QUEUED"
TASK_STATUS_RETRYING = "RETRYING"
TASK_STATUS_RUNNING = "RUNNING"
TASK_STATUS_SUCCESS = "SUCCESS"
TASK_STATUS_FAILED = "FAILED"
TASK_STATUS_CANCELLED = "CANCELLED"

TASK_ATTEMPT_STATUS_RUNNING = "RUNNING"
TASK_ATTEMPT_STATUS_SUCCESS = "SUCCESS"
TASK_ATTEMPT_STATUS_FAILED = "FAILED"
TASK_ATTEMPT_STATUS_CANCELLED = "CANCELLED"

OUTBOX_EVENT_DOCUMENT_INDEX = "DOCUMENT_INDEX_REQUESTED"
OUTBOX_STATUS_PENDING = "PENDING"
OUTBOX_STATUS_PUBLISHING = "PUBLISHING"
OUTBOX_STATUS_PUBLISHED = "PUBLISHED"
OUTBOX_STATUS_DISCARDED = "DISCARDED"

# EmbeddingRef 同时记录段落向量和问题增强向量。
# 字符串常量与 Chroma metadata 保持一致，检索层据此决定如何回到业务段落。
EMBEDDING_SOURCE_PARAGRAPH = "PARAGRAPH"
EMBEDDING_SOURCE_PROBLEM = "PROBLEM"

SEARCH_MODE_EMBEDDING = "embedding"
SEARCH_MODE_KEYWORDS = "keywords"
SEARCH_MODE_BLEND = "blend"


def default_retrieval_config() -> dict:
    """
    返回知识库默认检索参数。

    使用函数而不是模块级 dict，避免多个 ORM 对象共享同一个可变默认值。
    """

    return {
        "top_k": 4,
        "score_threshold": 0.0,
        "search_mode": SEARCH_MODE_EMBEDDING,
        "blend_weight": 0.5,
    }


def new_id() -> str:
    """
    生成字符串主键。

    MaxKB 里很多主键是 UUIDField 或 CharField。
    学习项目里统一用 uuid4 字符串，便于前端、SQLite 和 Chroma 共同使用。
    """

    return str(uuid.uuid4())


def now() -> datetime:
    """
    返回当前时间。

    SQLAlchemy 的 default/update 默认值可以接收函数。
    这里不要写 now()，而是传 now，让 ORM 在写入或更新时再调用。
    """

    return datetime.utcnow()


class KnowledgeFolderModel(Base):
    """
    知识库文件夹表。

    parent_id 指向同一张表中的父文件夹，形成任意层级的目录树。
    数据库外键只能保证“父节点存在”，不能保证“不形成环”；创建和移动目录时，
    service 层还会沿父链检查一次，避免 A -> B -> A 这样的循环结构。
    """

    __tablename__ = "knowledge_folder"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("knowledge_folder.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    parent: Mapped[Optional["KnowledgeFolderModel"]] = relationship(
        back_populates="children",
        remote_side="KnowledgeFolderModel.id",
    )
    # 不配置 delete-orphan/cascade：删除目录必须由 service 显式确认目录为空，
    # 防止一次误操作连带删除整个子树或其中的知识库。
    children: Mapped[list["KnowledgeFolderModel"]] = relationship(
        back_populates="parent",
    )
    knowledges: Mapped[list["KnowledgeModel"]] = relationship(
        back_populates="folder",
    )


class KnowledgeModel(Base):
    """
    知识库表。

    一条 Knowledge 是 RAG 数据的顶层容器。
    后续 Document、Paragraph、Embedding 都会通过 knowledge_id 归属到某个知识库。
    """

    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    folder_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("knowledge_folder.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    retrieval_config: Mapped[dict] = mapped_column(
        JSON,
        default=default_retrieval_config,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    folder: Mapped[Optional[KnowledgeFolderModel]] = relationship(
        back_populates="knowledges",
    )
    # relationship 只影响 ORM 对象之间的访问，不会改变业务含义。
    # 有了它以后，可以通过 knowledge.documents 拿到文档列表。
    documents: Mapped[list["DocumentModel"]] = relationship(
        back_populates="knowledge",
        cascade="all, delete-orphan",
    )


class FileModel(Base):
    """
    原始文件元数据表。

    文件二进制仍保存在本地磁盘，这张表只保存可查询、可校验的元数据。
    Document 通过 source_file_id 引用它，后续切换到对象存储时只需替换 file_path
    的含义，不必修改文档和索引模型。
    """

    __tablename__ = "file"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    file_name: Mapped[str] = mapped_column(String(255), index=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256_hash: Mapped[str] = mapped_column(String(64), default="")
    file_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    documents: Mapped[list["DocumentModel"]] = relationship(
        back_populates="source_file",
    )


class DocumentModel(Base):
    """
    文档表。

    用户上传的 txt/md 文件会先落成 Document。
    后续切分出来的 Paragraph 都挂在这条 Document 下面。
    """

    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    knowledge_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    source_file_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("file.id"),
        nullable=True,
        index=True,
    )
    # v0.3 起业务读取统一走 source_file.file_path。该列暂时保留并继续双写，
    # 是为了兼容旧 SQLite 表中不可直接移除的 NOT NULL file_path。
    file_path: Mapped[str] = mapped_column(String(1024))
    char_length: Mapped[int] = mapped_column(Integer, default=0)
    # 上传接口异步受理后，Worker 通过该字段暴露文档处理生命周期。
    status: Mapped[str] = mapped_column(String(20), default=DOCUMENT_STATUS_PENDING)
    # 只在 FAILED 状态保存错误摘要；处理成功后必须保持为 None。
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    knowledge: Mapped[KnowledgeModel] = relationship(back_populates="documents")
    source_file: Mapped[Optional[FileModel]] = relationship(
        back_populates="documents",
    )
    paragraphs: Mapped[list["ParagraphModel"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list["TaskModel"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class ParagraphModel(Base):
    """
    段落表。

    Paragraph 是 RAG 检索时最核心的业务粒度。
    文档不会整篇直接丢给模型，而是先切成多个段落，再对段落建向量索引。
    """

    __tablename__ = "paragraph"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    knowledge_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge.id"), index=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("document.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, index=True)
    # 第一版按字符切分，因此这里记录字符数，而不是 token 数。
    # 它用于直接观察每个 chunk 是否符合切分参数预期。
    chunk_length: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    document: Mapped[DocumentModel] = relationship(back_populates="paragraphs")
    embedding_refs: Mapped[list["EmbeddingRefModel"]] = relationship(
        back_populates="paragraph",
        cascade="all, delete-orphan",
    )
    problem_mappings: Mapped[list["ProblemParagraphMappingModel"]] = relationship(
        back_populates="paragraph",
        cascade="all, delete-orphan",
    )


class ProblemModel(Base):
    """
    问题增强表。

    content 保存一条与知识段落语义等价、但更接近用户提问方式的问题。
    检索命中它的向量后，通过 ProblemParagraphMapping 回到原始段落作为回答依据。
    """

    __tablename__ = "problem"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    knowledge_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge.id"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    paragraph_mappings: Mapped[list["ProblemParagraphMappingModel"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
    )
    embedding_ref: Mapped[Optional["EmbeddingRefModel"]] = relationship(
        back_populates="problem",
    )


class ProblemParagraphMappingModel(Base):
    """
    问题与段落的关联表。

    独立映射表允许同一个标准问题关联多个段落。当前 API 从单个段落创建问题，
    但数据模型不把这个学习阶段的交互限制固化成一对一关系。
    """

    __tablename__ = "problem_paragraph_mapping"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    knowledge_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge.id"),
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document.id"),
        index=True,
    )
    problem_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("problem.id"),
        index=True,
    )
    paragraph_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("paragraph.id"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    problem: Mapped[ProblemModel] = relationship(back_populates="paragraph_mappings")
    paragraph: Mapped[ParagraphModel] = relationship(back_populates="problem_mappings")


class EmbeddingRefModel(Base):
    """
    向量引用表。

    Chroma 负责保存真正的向量。
    SQLite 保存业务来源与 vector_id 的对应关系。

    这样做的原因是：
    1. 业务查询走 SQLite，容易理解。
    2. 相似度检索走 Chroma，职责清晰。
    3. 后续迁移到 pgvector 时，可以把这张表演进成真正的 Embedding 表。
    """

    __tablename__ = "embedding_ref"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    knowledge_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge.id"), index=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("document.id"), index=True)
    paragraph_id: Mapped[str] = mapped_column(String(64), ForeignKey("paragraph.id"), index=True)
    # 问题向量仍保存一个主 paragraph_id，以兼容旧 SQLite 中该列的 NOT NULL
    # 约束；真实来源由 source_type + problem_id 明确表达。
    source_type: Mapped[str] = mapped_column(
        String(20),
        default=EMBEDDING_SOURCE_PARAGRAPH,
        index=True,
    )
    problem_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("problem.id"),
        nullable=True,
        unique=True,
        index=True,
    )
    # 保存索引侧稳定的调试元数据。每次检索产生的动态分数只随 API 响应返回，
    # 不写回共享记录，避免并发查询互相覆盖。
    score_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    vector_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    # SQLite + Chroma 模式下该列保持为空；PostgreSQL + pgvector 模式把真实向量
    # 保存在同一行，使业务数据和向量索引共享数据库事务。
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    paragraph: Mapped[ParagraphModel] = relationship(back_populates="embedding_refs")
    problem: Mapped[Optional[ProblemModel]] = relationship(
        back_populates="embedding_ref",
    )


class TaskModel(Base):
    """
    后台任务表。

    数据库是任务状态的唯一事实来源。Celery/Redis 只负责传递 task_id 和
    attempt_no；重复消息、旧尝试消息和 Worker 重启都通过这里的条件状态转换
    判定是否允许执行。
    """

    __tablename__ = "task"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=TASK_STATUS_PENDING,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document.id"),
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=TASK_MAX_ATTEMPTS)
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(160),
        unique=True,
        index=True,
    )
    worker_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    document: Mapped[DocumentModel] = relationship(back_populates="tasks")
    attempts: Mapped[list["TaskAttemptModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    outbox_events: Mapped[list["OutboxEventModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskAttemptModel(Base):
    """
    每次任务执行的审计记录。

    TaskModel 保存当前快照；这里保留每次自动或人工重试的 Worker、耗时和错误，
    便于排查重复投递与进程异常。
    """

    __tablename__ = "task_attempt"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "attempt_no",
            name="uq_task_attempt_task_id_attempt_no",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task.id"),
        index=True,
    )
    attempt_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), index=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    task: Mapped[TaskModel] = relationship(back_populates="attempts")


class OutboxEventModel(Base):
    """
    与业务写入同事务创建的待投递事件。

    Relay 在提交后发布事件。若发布成功但来不及标记 PUBLISHED，租约到期后会
    再次发布；Worker 的 attempt_no 条件认领负责消化这种至少一次投递。
    """

    __tablename__ = "outbox_event"
    __table_args__ = (
        UniqueConstraint(
            "deduplication_key",
            name="uq_outbox_event_deduplication_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("task.id"),
        index=True,
    )
    attempt_no: Mapped[int] = mapped_column(Integer)
    deduplication_key: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20),
        default=OUTBOX_STATUS_PENDING,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    leased_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    task: Mapped[TaskModel] = relationship(back_populates="outbox_events")
