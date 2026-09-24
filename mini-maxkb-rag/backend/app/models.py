"""
业务数据模型。

这里定义的是 SQLite 里的业务表。
它们和 MaxKB 源码中的模型是简化映射关系：

Knowledge  -> KnowledgeModel
Document   -> DocumentModel
Paragraph  -> ParagraphModel
Embedding  -> EmbeddingRefModel + Chroma 中的真实向量

注意：第一版不单独做 File 表，原始文件路径直接存在 DocumentModel.file_path。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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


class KnowledgeModel(Base):
    """
    知识库表。

    一条 Knowledge 是 RAG 数据的顶层容器。
    后续 Document、Paragraph、Embedding 都会通过 knowledge_id 归属到某个知识库。
    """

    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    # relationship 只影响 ORM 对象之间的访问，不会改变业务含义。
    # 有了它以后，可以通过 knowledge.documents 拿到文档列表。
    documents: Mapped[list["DocumentModel"]] = relationship(
        back_populates="knowledge",
        cascade="all, delete-orphan",
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
    file_path: Mapped[str] = mapped_column(String(1024))
    char_length: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    knowledge: Mapped[KnowledgeModel] = relationship(back_populates="documents")
    paragraphs: Mapped[list["ParagraphModel"]] = relationship(
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
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    document: Mapped[DocumentModel] = relationship(back_populates="paragraphs")
    embedding_ref: Mapped["EmbeddingRefModel"] = relationship(
        back_populates="paragraph",
        cascade="all, delete-orphan",
    )


class EmbeddingRefModel(Base):
    """
    向量引用表。

    Chroma 负责保存真正的向量。
    SQLite 只保存 paragraph_id 和 vector_id 的对应关系。

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
    vector_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    paragraph: Mapped[ParagraphModel] = relationship(back_populates="embedding_ref")
