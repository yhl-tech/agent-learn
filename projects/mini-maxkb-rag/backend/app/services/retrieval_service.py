"""
统一检索服务。

这一层把向量检索、全文检索和混合重排组织成同一个入口。Chat 和检索测试 API
共享这条链路，避免“测试看到的结果”和“实际回答使用的结果”不一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    EMBEDDING_SOURCE_PARAGRAPH,
    EMBEDDING_SOURCE_PROBLEM,
    SEARCH_MODE_BLEND,
    SEARCH_MODE_EMBEDDING,
    SEARCH_MODE_KEYWORDS,
    DocumentModel,
    KnowledgeModel,
    ParagraphModel,
    ProblemParagraphMappingModel,
    default_retrieval_config,
)
from app.repositories.document_repository import get_documents_by_ids
from app.repositories.embedding_repository import (
    EmbeddingRepository,
    VectorSearchResult,
)
from app.repositories.paragraph_repository import search_paragraphs_by_keywords
from app.services.embedding_service import HashEmbeddingService
from app.services.rerank_service import (
    RetrievalCandidate,
    rerank_blended,
    rerank_single_source,
)


@dataclass(frozen=True)
class RetrievedParagraph:
    """
    一条已回源的召回段落。
    """

    paragraph: ParagraphModel
    document: DocumentModel
    score: float
    match_type: str
    score_meta: dict = field(default_factory=dict)


def resolve_retrieval_config(
    knowledge: KnowledgeModel,
    *,
    top_k: int | None = None,
    score_threshold: float | None = None,
    search_mode: str | None = None,
    blend_weight: float | None = None,
) -> dict:
    """
    合并系统默认值、知识库配置和单次请求覆盖值。

    单次请求只影响本次调用，不写回 Knowledge。数据库中的旧记录若配置缺字段，
    会由默认值补齐，保证后续扩展配置项时仍向后兼容。
    """

    config = default_retrieval_config()
    if isinstance(knowledge.retrieval_config, dict):
        config.update(
            {
                key: value
                for key, value in knowledge.retrieval_config.items()
                if key in config
            }
        )

    overrides = {
        "top_k": top_k,
        "score_threshold": score_threshold,
        "search_mode": search_mode,
        "blend_weight": blend_weight,
    }
    config.update(
        {
            key: value
            for key, value in overrides.items()
            if value is not None
        }
    )
    return config


def retrieve_paragraphs(
    db: Session,
    knowledge_id: str,
    question: str,
    top_k: int,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
    score_threshold: float = 0.0,
    search_mode: str = SEARCH_MODE_EMBEDDING,
    blend_weight: float = 0.5,
) -> list[RetrievedParagraph]:
    """
    根据检索模式召回并重排段落。

    Chroma 查询始终传 knowledge_id，SQLite 回源时再校验一次 knowledge_id，
    形成两层隔离，避免错误 metadata 导致跨知识库引用。
    """

    candidate_limit = min(max(top_k * 3, top_k), 60)
    embedding_candidates: list[RetrievalCandidate] = []
    keyword_candidates: list[RetrievalCandidate] = []

    if search_mode in {SEARCH_MODE_EMBEDDING, SEARCH_MODE_BLEND}:
        query_embedding = embedding_service.embed_text(question)
        vector_results = vector_store.search(
            db=db,
            knowledge_id=knowledge_id,
            query_embedding=query_embedding,
            top_k=candidate_limit if search_mode == SEARCH_MODE_BLEND else top_k,
        )
        embedding_candidates = _build_embedding_candidates(db, vector_results)

    if search_mode in {SEARCH_MODE_KEYWORDS, SEARCH_MODE_BLEND}:
        keyword_results = search_paragraphs_by_keywords(
            db=db,
            knowledge_id=knowledge_id,
            query=question,
            top_k=candidate_limit if search_mode == SEARCH_MODE_BLEND else top_k,
        )
        keyword_candidates = [
            RetrievalCandidate(
                paragraph_id=result.paragraph_id,
                score=result.score,
                match_type=SEARCH_MODE_KEYWORDS,
                score_meta={
                    "keyword_score": result.score,
                    "keyword_raw_score": result.raw_score,
                    "keyword_rank": result.rank,
                },
            )
            for result in keyword_results
        ]

    if search_mode == SEARCH_MODE_BLEND:
        ranked_candidates = rerank_blended(
            embedding_candidates=embedding_candidates,
            keyword_candidates=keyword_candidates,
            top_k=top_k,
            score_threshold=score_threshold,
            embedding_weight=blend_weight,
        )
    elif search_mode == SEARCH_MODE_KEYWORDS:
        ranked_candidates = rerank_single_source(
            keyword_candidates,
            top_k=top_k,
            score_threshold=score_threshold,
        )
    else:
        ranked_candidates = rerank_single_source(
            embedding_candidates,
            top_k=top_k,
            score_threshold=score_threshold,
        )

    return _load_retrieved_paragraphs(
        db=db,
        knowledge_id=knowledge_id,
        candidates=ranked_candidates,
    )


def _build_embedding_candidates(
    db: Session,
    vector_results: list[VectorSearchResult],
) -> list[RetrievalCandidate]:
    """
    把 Chroma 结果批量解析成段落候选。

    PROBLEM 向量通过 mapping 回到段落；历史向量缺少 source_type 时按普通段落
    处理，因此升级 v0.4 不要求重建现有 Chroma 数据。
    """

    problem_ids = {
        result.metadata.get("problem_id")
        for result in vector_results
        if result.metadata.get("source_type") == EMBEDDING_SOURCE_PROBLEM
        and result.metadata.get("problem_id")
    }
    mappings_by_problem: dict[str, list[str]] = {}
    if problem_ids:
        mappings = db.scalars(
            select(ProblemParagraphMappingModel).where(
                ProblemParagraphMappingModel.problem_id.in_(problem_ids)
            )
        ).all()
        for mapping in mappings:
            mappings_by_problem.setdefault(mapping.problem_id, []).append(
                mapping.paragraph_id
            )

    candidates = []
    for rank, result in enumerate(vector_results, start=1):
        source_type = result.metadata.get(
            "source_type",
            EMBEDDING_SOURCE_PARAGRAPH,
        )
        if source_type == EMBEDDING_SOURCE_PROBLEM:
            paragraph_ids = mappings_by_problem.get(
                result.metadata.get("problem_id"),
                [],
            )
            match_type = "problem"
        else:
            paragraph_id = result.metadata.get("paragraph_id")
            paragraph_ids = [paragraph_id] if paragraph_id else []
            match_type = SEARCH_MODE_EMBEDDING

        for paragraph_id in paragraph_ids:
            candidates.append(
                RetrievalCandidate(
                    paragraph_id=paragraph_id,
                    score=result.score,
                    match_type=match_type,
                    score_meta={
                        "vector_id": result.vector_id,
                        "vector_score": result.score,
                        "vector_rank": rank,
                        "source_type": source_type,
                    },
                )
            )
    return candidates


def _load_retrieved_paragraphs(
    db: Session,
    knowledge_id: str,
    candidates: list[RetrievalCandidate],
) -> list[RetrievedParagraph]:
    """
    批量加载候选对应的段落和文档，并保持重排后的顺序。
    """

    if not candidates:
        return []

    paragraph_ids = [candidate.paragraph_id for candidate in candidates]
    paragraphs = {
        paragraph.id: paragraph
        for paragraph in db.scalars(
            select(ParagraphModel).where(ParagraphModel.id.in_(paragraph_ids))
        ).all()
        if paragraph.knowledge_id == knowledge_id
    }
    document_ids = {paragraph.document_id for paragraph in paragraphs.values()}
    documents = get_documents_by_ids(db, document_ids, knowledge_id)

    retrieved = []
    for candidate in candidates:
        paragraph = paragraphs.get(candidate.paragraph_id)
        if paragraph is None:
            continue
        document = documents.get(paragraph.document_id)
        if document is None:
            continue
        retrieved.append(
            RetrievedParagraph(
                paragraph=paragraph,
                document=document,
                score=candidate.score,
                match_type=candidate.match_type,
                score_meta=candidate.score_meta,
            )
        )
    return retrieved
