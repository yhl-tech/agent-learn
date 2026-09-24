"""
知识库服务。

Knowledge 是整个 RAG 链路的顶层容器。
先有 Knowledge，后面上传的 Document、切出来的 Paragraph、写入的 Embedding
都要归属到某一个 knowledge_id。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeModel
from app.schemas import KnowledgeCreate


def create_knowledge(db: Session, payload: KnowledgeCreate) -> KnowledgeModel:
    """
    创建知识库。

    这里只保存最基础的 name/description。
    MaxKB 里的 workspace、scope、embedding_model 等字段会在后续阶段补齐。
    """

    knowledge = KnowledgeModel(
        name=payload.name,
        description=payload.description,
    )
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)
    return knowledge


def list_knowledges(db: Session) -> list[KnowledgeModel]:
    """
    查询所有知识库。

    第一版是单用户学习项目，不做 workspace/user 过滤。
    后续做权限时，这里会增加 workspace_id 或 user_id 条件。
    """

    statement = select(KnowledgeModel).order_by(KnowledgeModel.created_at.desc())
    return list(db.scalars(statement).all())


def get_knowledge(db: Session, knowledge_id: str) -> KnowledgeModel | None:
    """
    根据 ID 查询知识库。
    """

    return db.get(KnowledgeModel, knowledge_id)
