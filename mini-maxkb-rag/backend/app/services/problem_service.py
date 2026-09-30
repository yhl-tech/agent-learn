"""
问题增强服务。

一条 Problem 保存“用户可能如何提问”，并通过 Mapping 指回原始段落。
问题文本会单独生成向量；检索命中后不直接把问题当上下文，而是回到段落，
这样回答仍然有原文依据。
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    EMBEDDING_SOURCE_PROBLEM,
    DocumentModel,
    EmbeddingRefModel,
    ParagraphModel,
    ProblemModel,
    ProblemParagraphMappingModel,
    new_id,
)
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas import ProblemCreate, ProblemRead
from app.services.embedding_service import HashEmbeddingService


class ProblemNotFoundError(LookupError):
    """
    表示问题记录不存在。
    """


class ProblemParagraphNotFoundError(LookupError):
    """
    表示目标段落或所属文档不存在。
    """


class ProblemConflictError(RuntimeError):
    """
    表示同一段落已关联相同问题。
    """


class ProblemContentError(ValueError):
    """
    表示问题文本不能用于向量化。
    """


class ProblemProcessingError(RuntimeError):
    """
    表示 SQLite 与 Chroma 的问题索引写入或删除失败。
    """


def create_problem_for_paragraph(
    db: Session,
    paragraph_id: str,
    payload: ProblemCreate,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
) -> ProblemRead:
    """
    创建问题、段落映射和问题向量。

    三类 SQLite 记录在一个事务中提交；Chroma 写入发生在 commit 前。任何环节
    失败都会回滚 SQLite，并按预生成 vector_id 清理可能已写入的问题向量。
    """

    if not payload.content.strip():
        raise ProblemContentError("问题内容不能为空")

    paragraph = db.get(ParagraphModel, paragraph_id)
    if paragraph is None:
        raise ProblemParagraphNotFoundError("段落不存在")
    document = db.get(DocumentModel, paragraph.document_id)
    if document is None:
        raise ProblemParagraphNotFoundError("段落所属文档不存在")

    duplicate = db.scalar(
        select(ProblemModel.id)
        .join(
            ProblemParagraphMappingModel,
            ProblemParagraphMappingModel.problem_id == ProblemModel.id,
        )
        .where(
            ProblemParagraphMappingModel.paragraph_id == paragraph_id,
            ProblemModel.content == payload.content,
        )
    )
    if duplicate is not None:
        raise ProblemConflictError("该段落已存在相同问题")

    problem_id = new_id()
    problem = ProblemModel(
        id=problem_id,
        knowledge_id=paragraph.knowledge_id,
        content=payload.content,
    )
    mapping = ProblemParagraphMappingModel(
        knowledge_id=paragraph.knowledge_id,
        document_id=paragraph.document_id,
        problem_id=problem_id,
        paragraph_id=paragraph.id,
    )
    vector_id = new_id()

    try:
        db.add(problem)
        db.add(mapping)
        db.flush()

        vector_store.add_paragraphs(
            db=db,
            ids=[vector_id],
            embeddings=[embedding_service.embed_text(payload.content)],
            documents=[payload.content],
            metadatas=[
                {
                    "knowledge_id": paragraph.knowledge_id,
                    "document_id": paragraph.document_id,
                    "paragraph_id": paragraph.id,
                    "problem_id": problem.id,
                    "position": paragraph.position,
                    "source_type": EMBEDDING_SOURCE_PROBLEM,
                }
            ],
        )
        db.commit()
        db.refresh(problem)
    except Exception as error:
        db.rollback()
        cleanup_error = _delete_problem_vectors(db, vector_store, [vector_id])
        message = _build_problem_error(error, cleanup_error)
        raise ProblemProcessingError(message) from error

    return _to_problem_read(problem, [paragraph.id])


def list_paragraph_problems(
    db: Session,
    paragraph_id: str,
) -> list[ProblemRead]:
    """
    查询一个段落关联的全部问题。
    """

    if db.get(ParagraphModel, paragraph_id) is None:
        raise ProblemParagraphNotFoundError("段落不存在")

    problems = list(
        db.scalars(
            select(ProblemModel)
            .join(
                ProblemParagraphMappingModel,
                ProblemParagraphMappingModel.problem_id == ProblemModel.id,
            )
            .where(ProblemParagraphMappingModel.paragraph_id == paragraph_id)
            .order_by(ProblemModel.created_at.asc())
        ).all()
    )
    if not problems:
        return []

    problem_ids = [problem.id for problem in problems]
    mappings = list(
        db.scalars(
            select(ProblemParagraphMappingModel)
            .where(ProblemParagraphMappingModel.problem_id.in_(problem_ids))
            .order_by(ProblemParagraphMappingModel.created_at.asc())
        ).all()
    )
    paragraph_ids_by_problem: dict[str, list[str]] = {
        problem_id: [] for problem_id in problem_ids
    }
    for mapping in mappings:
        paragraph_ids_by_problem[mapping.problem_id].append(mapping.paragraph_id)

    return [
        _to_problem_read(problem, paragraph_ids_by_problem[problem.id])
        for problem in problems
    ]


def delete_problem(
    db: Session,
    problem_id: str,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
) -> None:
    """
    删除问题、映射和问题向量。

    与文档删除相同，SQLite 和 Chroma 没有共同事务。若向量删除后数据库提交
    失败，会使用原问题内容和映射元数据 upsert 恢复向量。
    """

    problem = db.get(ProblemModel, problem_id)
    if problem is None:
        raise ProblemNotFoundError("问题不存在")

    mappings = list(
        db.scalars(
            select(ProblemParagraphMappingModel).where(
                ProblemParagraphMappingModel.problem_id == problem_id
            )
        ).all()
    )
    refs = list(
        db.scalars(
            select(EmbeddingRefModel).where(
                EmbeddingRefModel.problem_id == problem_id
            )
        ).all()
    )
    vector_ids = [ref.vector_id for ref in refs]
    primary_mapping = mappings[0] if mappings else None
    primary_paragraph = (
        db.get(ParagraphModel, primary_mapping.paragraph_id)
        if primary_mapping is not None
        else None
    )

    try:
        vector_store.delete_by_ids(db, vector_ids)
        db.execute(
            delete(ProblemParagraphMappingModel).where(
                ProblemParagraphMappingModel.problem_id == problem_id
            )
        )
        db.delete(problem)
        db.commit()
    except Exception as error:
        db.rollback()
        restore_error = _restore_problem_vectors(
            problem=problem,
            refs=refs,
            mapping=primary_mapping,
            paragraph=primary_paragraph,
            db=db,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        message = _build_problem_error(error, restore_error)
        raise ProblemProcessingError(message) from error


def _to_problem_read(
    problem: ProblemModel,
    paragraph_ids: list[str],
) -> ProblemRead:
    """
    将 ORM 对象转换成包含关联段落 ID 的 API 结构。
    """

    return ProblemRead(
        id=problem.id,
        knowledge_id=problem.knowledge_id,
        content=problem.content,
        paragraph_ids=paragraph_ids,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
    )


def _delete_problem_vectors(
    db: Session,
    vector_store: EmbeddingRepository,
    vector_ids: list[str],
) -> Exception | None:
    """
    尽最大努力清理一次失败写入涉及的问题向量。
    """

    if vector_store.transactional:
        return None

    try:
        vector_store.delete_by_ids(db, vector_ids)
        return None
    except Exception as error:
        return error


def _restore_problem_vectors(
    problem: ProblemModel,
    refs: list[EmbeddingRefModel],
    mapping: ProblemParagraphMappingModel | None,
    paragraph: ParagraphModel | None,
    db: Session,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
) -> Exception | None:
    """
    删除事务失败时恢复问题向量。

    映射或段落本身缺失时无法构造可信 metadata，此时返回明确异常并保留原始
    数据库记录，避免写入无法回到业务段落的悬空向量。
    """

    if not refs or vector_store.transactional:
        return None
    if mapping is None or paragraph is None:
        return RuntimeError("问题缺少可恢复的段落映射")

    try:
        vector_store.upsert_paragraphs(
            db=db,
            ids=[ref.vector_id for ref in refs],
            embeddings=[
                embedding_service.embed_text(problem.content)
                for _ref in refs
            ],
            documents=[problem.content for _ref in refs],
            metadatas=[
                {
                    "knowledge_id": problem.knowledge_id,
                    "document_id": mapping.document_id,
                    "paragraph_id": mapping.paragraph_id,
                    "problem_id": problem.id,
                    "position": paragraph.position,
                    "source_type": EMBEDDING_SOURCE_PROBLEM,
                }
                for _ref in refs
            ],
        )
        return None
    except Exception as error:
        return error


def _build_problem_error(
    error: Exception,
    compensation_error: Exception | None,
) -> str:
    """
    合并原始错误和补偿错误，避免后者覆盖真正失败原因。
    """

    message = str(error).strip() or error.__class__.__name__
    if compensation_error is not None:
        detail = (
            str(compensation_error).strip()
            or compensation_error.__class__.__name__
        )
        message = f"{message}；向量补偿失败：{detail}"
    return message[:1000]
