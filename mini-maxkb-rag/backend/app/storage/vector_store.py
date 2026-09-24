"""
向量库封装。

Chroma 是第一版的向量存储。
这个文件把 Chroma 的 API 包起来，避免业务服务里直接散落 Chroma 调用。

后续如果切换到 PostgreSQL + pgvector，优先替换这个文件，而不是全项目搜索修改。
"""

from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from app.config import CHROMA_DIR


COLLECTION_NAME = "mini_maxkb_paragraphs"


@dataclass
class VectorSearchResult:
    """
    向量检索结果。

    vector_id 是 Chroma 中的向量 ID。
    score 是相似度分数，越大表示越相关。
    metadata 用来带回 knowledge_id、document_id、paragraph_id 等业务信息。
    """

    vector_id: str
    score: float
    metadata: dict
    document: str


class ChromaVectorStore:
    """
    Chroma 向量库客户端。

    这个类只处理向量库读写，不负责数据库表，也不负责生成 embedding。
    """

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

    def search(self, knowledge_id: str, query_embedding: list[float], top_k: int) -> list[VectorSearchResult]:
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

    def delete_by_document(self, document_id: str) -> None:
        """
        删除某个文档对应的全部向量。

        v0.1 暂时没有暴露删除文档接口，但先把底层能力放好。
        v0.2 做文档删除时会直接用到。
        """

        self.collection.delete(where={"document_id": document_id})
