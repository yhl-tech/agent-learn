"""
文档数据访问。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DocumentModel, ParagraphModel


def get_document_by_id(
    db: Session,
    document_id: str,
) -> DocumentModel | None:
    """
    按主键查询文档；不存在时返回 None。
    """

    return db.get(DocumentModel, document_id)


def list_documents_with_paragraph_count(
    db: Session,
    knowledge_id: str,
) -> list[tuple[DocumentModel, int]]:
    """
    一次查询返回知识库内文档及其段落数，避免逐文档统计产生 N+1 查询。
    """

    statement = (
        select(DocumentModel, func.count(ParagraphModel.id))
        .outerjoin(ParagraphModel, ParagraphModel.document_id == DocumentModel.id)
        .where(DocumentModel.knowledge_id == knowledge_id)
        .group_by(DocumentModel.id)
        .order_by(DocumentModel.created_at.desc())
    )
    return [
        (document, int(paragraph_count))
        for document, paragraph_count in db.execute(statement).all()
    ]


def get_documents_by_ids(
    db: Session,
    document_ids: set[str],
    knowledge_id: str,
) -> dict[str, DocumentModel]:
    """
    批量加载属于指定知识库的文档，并按 ID 建立索引。

    knowledge_id 条件用于阻止检索结果中的异常 ID 越过知识库隔离边界。
    """

    if not document_ids:
        return {}
    documents = db.scalars(
        select(DocumentModel).where(
            DocumentModel.id.in_(document_ids),
            DocumentModel.knowledge_id == knowledge_id,
        )
    ).all()
    return {document.id: document for document in documents}
