"""
FastAPI 依赖对象。

数据库会话在 database.py 里提供。
这里提供 embedding_service 和 embedding_repository 的单例。

使用 lru_cache 的原因：
1. 每次请求不用重复初始化向量后端。
2. 调用方式仍然是函数依赖，方便测试时替换。
"""

from functools import lru_cache

from app.config import VECTOR_BACKEND
from app.repositories.embedding_repository import (
    EmbeddingRepository,
    PostgresEmbeddingRepository,
)
from app.services.embedding_service import HashEmbeddingService
from app.storage.vector_store import ChromaEmbeddingRepository


@lru_cache
def get_embedding_service() -> HashEmbeddingService:
    """
    获取 embedding 服务实例。
    """

    return HashEmbeddingService()


@lru_cache
def get_embedding_repository() -> EmbeddingRepository:
    """
    根据配置获取向量仓库实例。
    """

    if VECTOR_BACKEND == "pgvector":
        return PostgresEmbeddingRepository()
    return ChromaEmbeddingRepository()


# 兼容 v0.1-v0.4 的依赖覆盖代码；新业务代码统一使用新名称。
get_vector_store = get_embedding_repository
