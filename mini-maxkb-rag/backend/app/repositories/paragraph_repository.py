"""
段落查询仓库。

SQLite 使用 FTS5，PostgreSQL 使用 tsvector。两种实现都返回统一的
KeywordSearchResult，检索服务不需要知道底层全文检索方言。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class KeywordSearchResult:
    """
    一条关键词召回结果。

    score 在当前结果集内归一化到 0-1；raw_score 保留数据库原始相关度，
    供检索测试面板定位排序差异。
    """

    paragraph_id: str
    score: float
    raw_score: float
    rank: int


def search_paragraphs_by_keywords(
    db: Session,
    knowledge_id: str,
    query: str,
    top_k: int,
) -> list[KeywordSearchResult]:
    """
    按当前数据库方言执行全文检索。
    """

    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        rows = _search_sqlite_fts(db, knowledge_id, query, top_k)
    elif dialect == "postgresql":
        rows = _search_postgresql_fts(db, knowledge_id, query, top_k)
    else:
        rows = _search_portable_like(db, knowledge_id, query, top_k)

    if not rows:
        return []

    max_raw_score = max(row["raw_score"] for row in rows)
    return [
        KeywordSearchResult(
            paragraph_id=row["paragraph_id"],
            score=(
                row["raw_score"] / max_raw_score
                if max_raw_score > 0
                else 1.0 / (index + 1)
            ),
            raw_score=row["raw_score"],
            rank=index + 1,
        )
        for index, row in enumerate(rows)
    ]


def _search_sqlite_fts(
    db: Session,
    knowledge_id: str,
    query: str,
    top_k: int,
) -> list[dict]:
    """
    使用 SQLite FTS5 BM25 排序。

    用户输入不能直接作为 MATCH 表达式，否则引号、减号等符号会改变语法甚至
    触发查询错误。这里先提取字母数字词和连续中日韩文本，再把每个词作为
    FTS phrase 用 OR 连接。
    """

    match_query = _build_fts5_query(query)
    if not match_query:
        return []

    rows = db.execute(
        text(
            """
            SELECT
                paragraph_id,
                bm25(paragraph_fts, 0.0, 0.0, 5.0, 1.0) AS bm25_rank
            FROM paragraph_fts
            WHERE paragraph_fts MATCH :match_query
              AND knowledge_id = :knowledge_id
            ORDER BY bm25_rank ASC
            LIMIT :top_k
            """
        ),
        {
            "match_query": match_query,
            "knowledge_id": knowledge_id,
            "top_k": top_k,
        },
    ).mappings()
    return [
        {
            "paragraph_id": row["paragraph_id"],
            # FTS5 的 bm25 越小越相关，并通常返回负数。
            "raw_score": max(-float(row["bm25_rank"]), 0.0),
        }
        for row in rows
    ]


def _search_postgresql_fts(
    db: Session,
    knowledge_id: str,
    query: str,
    top_k: int,
) -> list[dict]:
    """
    使用 PostgreSQL tsvector/tsquery 查询。

    simple 配置不会做英文词干变化，行为更接近 SQLite 的字面关键词检索。
    """

    rows = db.execute(
        text(
            """
            SELECT
                id AS paragraph_id,
                ts_rank_cd(
                    search_vector,
                    plainto_tsquery('simple', :query)
                ) AS raw_score
            FROM paragraph
            WHERE knowledge_id = :knowledge_id
              AND search_vector @@ plainto_tsquery('simple', :query)
            ORDER BY raw_score DESC
            LIMIT :top_k
            """
        ),
        {
            "query": query,
            "knowledge_id": knowledge_id,
            "top_k": top_k,
        },
    ).mappings()
    return [
        {
            "paragraph_id": row["paragraph_id"],
            "raw_score": float(row["raw_score"]),
        }
        for row in rows
    ]


def _search_portable_like(
    db: Session,
    knowledge_id: str,
    query: str,
    top_k: int,
) -> list[dict]:
    """
    未支持方言的保底实现。

    它不提供全文索引性能，只保证 repository 接口仍可用。
    """

    escaped_query = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    rows = db.execute(
        text(
            """
            SELECT id AS paragraph_id
            FROM paragraph
            WHERE knowledge_id = :knowledge_id
              AND (
                    title LIKE :pattern ESCAPE '\\'
                    OR content LIKE :pattern ESCAPE '\\'
                  )
            ORDER BY position ASC
            LIMIT :top_k
            """
        ),
        {
            "knowledge_id": knowledge_id,
            "pattern": f"%{escaped_query}%",
            "top_k": top_k,
        },
    ).mappings()
    return [
        {"paragraph_id": row["paragraph_id"], "raw_score": 1.0}
        for row in rows
    ]


def _build_fts5_query(query: str) -> str:
    """
    将自然语言安全转换为 FTS5 phrase OR 查询。
    """

    terms = re.findall(r"[0-9A-Za-z_]+|[\u3400-\u9fff]+", query)
    unique_terms = list(dict.fromkeys(term for term in terms if term))
    return " OR ".join(
        f'"{term.replace(chr(34), chr(34) * 2)}"'
        for term in unique_terms
    )
