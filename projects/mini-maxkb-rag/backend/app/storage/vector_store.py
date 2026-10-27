"""
Chroma 向量仓库实现。

Chroma 保存真实向量，SQLAlchemy Session 保存 EmbeddingRef。仓库统一维护两边
的引用关系，业务服务不再直接感知具体向量后端。
"""

import chromadb
from chromadb.config import Settings
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import CHROMA_DIR
from app.models import EmbeddingRefModel
from app.repositories.embedding_repository import (
    VectorSearchResult,
    build_embedding_ref,
)


COLLECTION_NAME = "mini_maxkb_paragraphs"


class ChromaEmbeddingRepository:
    """
    Chroma 向量库客户端。

    这个类只处理向量库读写，不负责数据库表，也不负责生成 embedding。
    """

    transactional = False

    def __init__(self) -> None:
        # 关闭匿名 telemetry。
        # 学习项目里我们更希望终端输出只保留和业务有关的信息。
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)

    def add_paragraphs(
        self,
        db: Session,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        将段落向量写入 Chroma。

        参数必须一一对应：
        ids[0]、embeddings[0]、documents[0]、metadatas[0] 描述同一个段落。
        """

        if not ids:
            return

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        db.add_all(
            [
                build_embedding_ref(vector_id, None, metadata)
                for vector_id, metadata in zip(ids, metadatas)
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
        新增或覆盖指定 ID 的段落向量。

        正常入库使用 add，避免意外覆盖已有向量；删除或重新索引发生中途失败时，
        补偿逻辑使用 upsert 恢复旧向量，即使部分旧向量仍存在也可以安全执行。
        """

        if not ids:
            return

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        existing_ids = set(
            db.scalars(
                select(EmbeddingRefModel.vector_id).where(
                    EmbeddingRefModel.vector_id.in_(ids)
                )
            ).all()
        )
        db.add_all(
            [
                build_embedding_ref(vector_id, None, metadata)
                for vector_id, metadata in zip(ids, metadatas)
                if vector_id not in existing_ids
            ]
        )

    def search(
        self,
        db: Session,
        knowledge_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[VectorSearchResult]:
        """
        在某个知识库内检索最相关的段落。

        where={"knowledge_id": knowledge_id} 是关键过滤条件。
        没有这个过滤，不同知识库之间的内容会互相串。
        """

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"knowledge_id": knowledge_id},
        )

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        documents = result.get("documents", [[]])[0]

        search_results: list[VectorSearchResult] = []
        for vector_id, distance, metadata, document in zip(ids, distances, metadatas, documents):
            # Chroma 返回的是 distance，不同索引的含义可能略有差异。
            # 这里转成一个简单 score，便于前端展示：分数越高越相似。
            score = 1.0 / (1.0 + float(distance))
            search_results.append(
                VectorSearchResult(
                    vector_id=vector_id,
                    score=score,
                    metadata=metadata or {},
                    document=document or "",
                )
            )

        return search_results

    def delete_by_document(self, db: Session, document_id: str) -> None:
        """
        删除某个文档对应的全部向量。

        v0.1 暂时没有暴露删除文档接口，但先把底层能力放好。
        v0.2 做文档删除时会直接用到。
        """

        self.collection.delete(where={"document_id": document_id})
        db.execute(
            delete(EmbeddingRefModel).where(
                EmbeddingRefModel.document_id == document_id
            )
        )

    def delete_by_ids(self, db: Session, vector_ids: list[str]) -> None:
        """
        精确删除一组向量。

        重新索引时新旧向量会短暂共存，不能使用 document_id 整批删除，
        否则会把刚写入的新向量一并移除。
        """

        if not vector_ids:
            return

        self.collection.delete(ids=vector_ids)
        db.execute(
            delete(EmbeddingRefModel).where(
                EmbeddingRefModel.vector_id.in_(vector_ids)
            )
        )


# 保留旧名称，避免外部学习代码在升级时立即失效。
ChromaVectorStore = ChromaEmbeddingRepository
