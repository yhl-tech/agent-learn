"""
召回结果重排。

向量相似度和全文检索 BM25 分数不在同一量纲，不能直接相加。混合模式使用
Reciprocal Rank Fusion（RRF）按各路排名融合，对底层分数尺度不敏感。
"""

from __future__ import annotations

from dataclasses import dataclass, field


RRF_RANK_CONSTANT = 60


@dataclass(frozen=True)
class RetrievalCandidate:
    """
    尚未加载 ORM 业务对象的一条候选段落。
    """

    paragraph_id: str
    score: float
    match_type: str
    score_meta: dict = field(default_factory=dict)


def rerank_single_source(
    candidates: list[RetrievalCandidate],
    top_k: int,
    score_threshold: float,
) -> list[RetrievalCandidate]:
    """
    对单路召回去重、过滤并截断。

    问题向量和段落向量可能同时映射到同一段落，保留分数更高的一条。
    """

    best_by_paragraph: dict[str, RetrievalCandidate] = {}
    for candidate in candidates:
        existing = best_by_paragraph.get(candidate.paragraph_id)
        if existing is None or candidate.score > existing.score:
            best_by_paragraph[candidate.paragraph_id] = candidate

    return [
        candidate
        for candidate in sorted(
            best_by_paragraph.values(),
            key=lambda item: item.score,
            reverse=True,
        )
        if candidate.score >= score_threshold
    ][:top_k]


def rerank_blended(
    embedding_candidates: list[RetrievalCandidate],
    keyword_candidates: list[RetrievalCandidate],
    top_k: int,
    score_threshold: float,
    embedding_weight: float,
) -> list[RetrievalCandidate]:
    """
    用加权 RRF 合并向量和关键词召回。

    最终分数除以理论最大值，使结果落在 0-1。score_meta 同时保留两路原始
    分数和排名，检索测试接口可以解释某条结果为什么排在当前位置。
    """

    keyword_weight = 1.0 - embedding_weight
    merged: dict[str, dict] = {}

    for source, candidates, weight in (
        ("embedding", embedding_candidates, embedding_weight),
        ("keywords", keyword_candidates, keyword_weight),
    ):
        for rank, candidate in enumerate(candidates, start=1):
            item = merged.setdefault(
                candidate.paragraph_id,
                {
                    "rrf_score": 0.0,
                    "sources": {},
                },
            )
            contribution = weight / (RRF_RANK_CONSTANT + rank)
            item["rrf_score"] += contribution
            item["sources"][source] = {
                "rank": rank,
                "score": candidate.score,
                "contribution": contribution,
                **candidate.score_meta,
            }

    theoretical_max = 1.0 / (RRF_RANK_CONSTANT + 1)
    reranked = []
    for paragraph_id, item in merged.items():
        score = item["rrf_score"] / theoretical_max
        sources = item["sources"]
        reranked.append(
            RetrievalCandidate(
                paragraph_id=paragraph_id,
                score=min(score, 1.0),
                match_type=(
                    "blend"
                    if len(sources) > 1
                    else next(iter(sources))
                ),
                score_meta={
                    "algorithm": "weighted_rrf",
                    "embedding_weight": embedding_weight,
                    "keyword_weight": keyword_weight,
                    "sources": sources,
                },
            )
        )

    return [
        candidate
        for candidate in sorted(
            reranked,
            key=lambda item: item.score,
            reverse=True,
        )
        if candidate.score >= score_threshold
    ][:top_k]
