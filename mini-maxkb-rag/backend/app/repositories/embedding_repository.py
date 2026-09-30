"""
向量索引仓库边界。

业务服务只依赖 EmbeddingRepository。SQLite 默认实现由 Chroma 适配器提供；
PostgreSQL 实现把向量直接保存在 embedding_ref.embedding 中。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import EmbeddingRefModel


@dataclass(frozen=True)
class VectorSearchResult:
    """
    向量检索返回给业务层的统一结构。
    """

    vector_id: str
    score: float
    metadata: dict
    document: str


class EmbeddingRepository(Protocol):
    """
    向量后端必须实现的最小接口。

    transactional 表示向量是否和当前 SQLAlchemy Session 共享事务。外部存储
    失败时需要补偿；pgvector 则可以直接依赖数据库 rollback。
    """

    transactional: bool

    def add_paragraphs(
        self,
        db: Session,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        在调用方事务中新增一批向量。
        """
        ...

    def upsert_paragraphs(
        self,
        db: Session,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        按稳定 vector_id 新增或更新一批向量。
        """
        ...

    def search(
        self,
        db: Session,
        knowledge_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[VectorSearchResult]:
        """
        在单个知识库边界内执行向量相似度检索。
        """
        ...

    def delete_by_document(self, db: Session, document_id: str) -> None:
        """
        删除文档关联的全部向量。
        """
        ...

    def delete_by_ids(self, db: Session, vector_ids: list[str]) -> None:
        """
        按 vector_id 批量删除向量。
        """
        ...


class PostgresEmbeddingRepository:
    """
    PostgreSQL + pgvector 实现。

    所有写入都使用调用方传入的 Session，不在仓库内部 commit，因此文档、
    段落和向量能够作为一个事务提交或回滚。
    """

    transactional = True

    def add_paragraphs(
        self,
        db: Session,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        新增 pgvector 记录；重复 ID 由数据库唯一约束拒绝。
        """

        _validate_batch(ids, embeddings, documents, metadatas)
        db.add_all(
            [
                build_embedding_ref(vector_id, embedding, metadata)
                for vector_id, embedding, metadata in zip(
                    ids,
                    embeddings,
                    metadatas,
                )
            ]
        )

    def upsert_paragraphs(
        self,
        db: Session,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        按 vector_id 更新已有记录，不存在时插入。

        稳定 ID 让同一任务 attempt 的重复执行得到相同结果，而不是产生重复向量。
        """

        _validate_batch(ids, embeddings, documents, metadatas)
        existing_refs = {
            ref.vector_id: ref
            for ref in db.scalars(
                select(EmbeddingRefModel).where(
                    EmbeddingRefModel.vector_id.in_(ids)
                )
            ).all()
        }
        for vector_id, embedding, metadata in zip(ids, embeddings, metadatas):
            ref = existing_refs.get(vector_id)
            if ref is None:
                db.add(build_embedding_ref(vector_id, embedding, metadata))
                continue
            _apply_metadata(ref, metadata)
            ref.embedding = embedding

    def search(
        self,
        db: Session,
        knowledge_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[VectorSearchResult]:
        """
        使用 pgvector 余弦距离召回，并转换成越大越相关的 0-1 分数。
        """

        distance = EmbeddingRefModel.embedding.cosine_distance(query_embedding)
        rows = db.execute(
            select(EmbeddingRefModel, distance.label("distance"))
            .where(
                EmbeddingRefModel.knowledge_id == knowledge_id,
                EmbeddingRefModel.embedding.is_not(None),
            )
            .order_by(distance.asc())
            .limit(top_k)
        ).all()

        return [
            VectorSearchResult(
                vector_id=ref.vector_id,
                score=max(0.0, min(1.0, 1.0 - float(raw_distance))),
                metadata=_metadata_from_ref(ref),
                document="",
            )
            for ref, raw_distance in rows
        ]

    def delete_by_document(self, db: Session, document_id: str) -> None:
        """
        在当前事务中删除文档全部向量引用。
        """

        db.execute(
            delete(EmbeddingRefModel).where(
                EmbeddingRefModel.document_id == document_id
            )
        )

    def delete_by_ids(self, db: Session, vector_ids: list[str]) -> None:
        """
        在当前事务中按稳定向量 ID 批量删除。
        """

        if not vector_ids:
            return
        db.execute(
            delete(EmbeddingRefModel).where(
                EmbeddingRefModel.vector_id.in_(vector_ids)
            )
        )


def _validate_batch(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """
    阻止错位批次写入错误的业务引用。
    """

    if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
        raise ValueError("向量批次的 ID、向量、文本和元数据数量必须一致")


def build_embedding_ref(
    vector_id: str,
    embedding: list[float] | None,
    metadata: dict,
) -> EmbeddingRefModel:
    """
    由统一 metadata 构造 pgvector ORM 记录。
    """

    ref = EmbeddingRefModel(vector_id=vector_id, embedding=embedding)
    _apply_metadata(ref, metadata)
    return ref


def _apply_metadata(ref: EmbeddingRefModel, metadata: dict) -> None:
    """
    将跨后端统一 metadata 映射到关系字段。
    """

    ref.knowledge_id = metadata["knowledge_id"]
    ref.document_id = metadata["document_id"]
    ref.paragraph_id = metadata["paragraph_id"]
    ref.problem_id = metadata.get("problem_id")
    ref.source_type = metadata["source_type"]
    ref.score_meta = {"source_type": metadata["source_type"]}


def _metadata_from_ref(ref: EmbeddingRefModel) -> dict:
    """
    将关系字段还原成跨向量后端统一的 metadata。
    """

    metadata = {
        "knowledge_id": ref.knowledge_id,
        "document_id": ref.document_id,
        "paragraph_id": ref.paragraph_id,
        "source_type": ref.source_type,
    }
    if ref.problem_id is not None:
        metadata["problem_id"] = ref.problem_id
    return metadata
