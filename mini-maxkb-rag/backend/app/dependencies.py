"""
FastAPI 依赖对象。

数据库会话在 database.py 里提供。
这里提供 embedding_service 和 vector_store 的单例。

使用 lru_cache 的原因：
1. 每次请求不用重复初始化 Chroma。
2. 调用方式仍然是函数依赖，方便测试时替换。
"""

from functools import lru_cache

from app.services.embedding_service import HashEmbeddingService
from app.storage.vector_store import ChromaVectorStore


@lru_cache
def get_embedding_service() -> HashEmbeddingService:
    """
    获取 embedding 服务实例。
    """

    return HashEmbeddingService()


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    """
    获取 Chroma 向量库实例。
    """

    return ChromaVectorStore()
