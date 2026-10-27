"""
知识库数据访问。

service 负责业务校验和事务提交，repository 只组织可复用查询。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeModel


def add_knowledge(db: Session, knowledge: KnowledgeModel) -> None:
    """
    将知识库加入当前事务；提交由 service 统一负责。
    """

    db.add(knowledge)


def get_knowledge_by_id(
    db: Session,
    knowledge_id: str,
) -> KnowledgeModel | None:
    """
    按主键查询知识库；不存在时返回 None。
    """

    return db.get(KnowledgeModel, knowledge_id)


def list_all_knowledges(db: Session) -> list[KnowledgeModel]:
    """
    按创建时间倒序返回全部知识库。
    """

    statement = select(KnowledgeModel).order_by(KnowledgeModel.created_at.desc())
    return list(db.scalars(statement).all())
