"""
接口数据结构。

SQLAlchemy 模型描述“数据库怎么存”。
Pydantic Schema 描述“API 怎么收、怎么返回”。

把两者分开，是为了避免数据库字段变化直接泄漏给前端。
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class KnowledgeCreate(BaseModel):
    """
    创建知识库时前端传入的数据。
    """

    name: str = Field(min_length=1, max_length=150)
    description: str = ""


class KnowledgeRead(BaseModel):
    """
    返回给前端的知识库数据。
    """

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    # from_attributes=True 允许 Pydantic 直接从 SQLAlchemy 对象读取字段。
    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    """
    返回给前端的文档数据。
    """

    id: str
    knowledge_id: str
    name: str
    char_length: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParagraphRead(BaseModel):
    """
    返回给前端的段落数据。
    """

    id: str
    knowledge_id: str
    document_id: str
    content: str
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """
    知识库问答请求。
    """

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)


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


class ChatResponse(BaseModel):
    """
    知识库问答响应。
    """

    answer: str
    references: List[ReferenceRead]
