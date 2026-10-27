"""
接口数据结构。

SQLAlchemy 模型描述“数据库怎么存”。
Pydantic Schema 描述“API 怎么收、怎么返回”。

把两者分开，是为了避免数据库字段变化直接泄漏给前端。
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SearchMode = Literal["embedding", "keywords", "blend"]


class RetrievalConfigRead(BaseModel):
    """
    知识库生效中的检索参数。
    """

    top_k: int = Field(ge=1, le=20)
    score_threshold: float = Field(ge=0.0, le=1.0)
    search_mode: SearchMode
    # blend_weight 表示混合检索中向量召回所占权重，剩余部分属于关键词召回。
    blend_weight: float = Field(ge=0.0, le=1.0)


class RetrievalConfigUpdate(BaseModel):
    """
    局部更新知识库检索参数。
    """

    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    search_mode: Optional[SearchMode] = None
    blend_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class KnowledgeFolderCreate(BaseModel):
    """
    创建知识库文件夹时传入的数据。

    parent_id 为空表示根目录；传入文件夹 ID 则创建为它的直接子目录。
    """

    name: str = Field(min_length=1, max_length=150)
    description: str = ""
    parent_id: Optional[str] = None


class KnowledgeFolderUpdate(BaseModel):
    """
    修改文件夹自身信息或移动文件夹。

    parent_id 显式传 null 表示移动到根目录；完全不传则保持原父目录不变。
    service 会通过 model_fields_set 区分这两种情况。
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    parent_id: Optional[str] = None


class KnowledgeFolderRead(BaseModel):
    """
    文件夹树节点。

    children 由查询服务在内存中组装，不是数据库中的冗余 JSON 字段。
    """

    id: str
    name: str
    description: str
    parent_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    children: list["KnowledgeFolderRead"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class KnowledgeCreate(BaseModel):
    """
    创建知识库时前端传入的数据。
    """

    name: str = Field(min_length=1, max_length=150)
    description: str = ""
    folder_id: Optional[str] = None


class KnowledgeMove(BaseModel):
    """
    把知识库移动到另一个文件夹。

    folder_id 为 null 表示移回根级。
    """

    folder_id: Optional[str] = None


class KnowledgeRead(BaseModel):
    """
    返回给前端的知识库数据。
    """

    id: str
    folder_id: Optional[str]
    name: str
    description: str
    retrieval_config: RetrievalConfigRead
    created_at: datetime
    updated_at: datetime

    # from_attributes=True 允许 Pydantic 直接从 SQLAlchemy 对象读取字段。
    model_config = {"from_attributes": True}


class FileRead(BaseModel):
    """
    返回给前端的原始文件元数据。

    file_path 是服务端内部存储位置，不通过 API 暴露。
    """

    id: str
    file_name: str
    file_size: int
    sha256_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    """
    返回给前端的文档数据。
    """

    id: str
    knowledge_id: str
    source_file_id: Optional[str]
    name: str
    char_length: int
    paragraph_count: int = 0
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskRead(BaseModel):
    """
    可轮询的后台任务状态。
    """

    id: str
    type: str
    status: str
    document_id: str
    error_message: Optional[str]
    error_code: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    retry_count: int
    attempt_no: int
    max_attempts: int
    celery_task_id: Optional[str]
    idempotency_key: str
    worker_id: Optional[str]
    queued_at: Optional[datetime]
    heartbeat_at: Optional[datetime]
    lease_expires_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadRead(DocumentRead):
    """
    上传受理结果。

    顶层保留文档字段以兼容已有客户端，task 用于前端轮询真实处理结果。
    """

    task: TaskRead


class ParagraphRead(BaseModel):
    """
    返回给前端的段落数据。
    """

    id: str
    knowledge_id: str
    document_id: str
    content: str
    position: int
    title: str
    chunk_length: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProblemCreate(BaseModel):
    """
    为段落创建一条问题增强语料。
    """

    content: str = Field(min_length=1, max_length=2000)


class ProblemRead(BaseModel):
    """
    问题及其关联段落。
    """

    id: str
    knowledge_id: str
    content: str
    paragraph_ids: list[str]
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    """
    知识库问答请求。
    """

    question: str = Field(min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    search_mode: Optional[SearchMode] = None
    blend_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ReferenceRead(BaseModel):
    """
    回答引用来源。

    真实 RAG 产品里，引用来源非常重要。
    它让用户知道答案依据来自哪份文档、哪个段落，而不是只看到模型生成的文本。
    """

    document_id: str
    document_name: str
    paragraph_id: str
    content: str
    score: float
    match_type: str
    score_meta: dict = Field(default_factory=dict)


class RetrievalTestRequest(ChatRequest):
    """
    只执行检索、不调用大模型的调试请求。
    """


class RetrievalTestResponse(BaseModel):
    """
    检索测试响应。
    """

    config: RetrievalConfigRead
    results: List[ReferenceRead]


class ChatResponse(BaseModel):
    """
    知识库问答响应。
    """

    answer: str
    references: List[ReferenceRead]
