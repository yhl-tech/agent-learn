"""
检索服务。

Retrieval 是 RAG 里的 R：
用户提问后，系统先从知识库中找出最相关的段落，再把这些段落交给模型生成回答。
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import DocumentModel, ParagraphModel
from app.services.embedding_service import HashEmbeddingService
from app.storage.vector_store import ChromaVectorStore


@dataclass
class RetrievedParagraph:
    """
    一条召回段落。

    这里把 paragraph、document、score 聚合在一起，
    chat_service 生成回答时就不用再关心向量库的返回格式。
    """

    paragraph: ParagraphModel
    document: DocumentModel
    score: float


def retrieve_paragraphs(
    db: Session,
    knowledge_id: str,
    question: str,
    top_k: int,
    embedding_service: HashEmbeddingService,
    vector_store: ChromaVectorStore,
) -> list[RetrievedParagraph]:
    """
    根据问题检索相关段落。

    流程：
    1. 把 question 转成向量。
    2. 到 Chroma 里按 knowledge_id 检索 top_k。
    3. 根据 metadata.paragraph_id 回 SQLite 查业务数据。
    4. 返回 paragraph + document + score。
    """

    query_embedding = embedding_service.embed_text(question)
    vector_results = vector_store.search(
        knowledge_id=knowledge_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )

    retrieved: list[RetrievedParagraph] = []
    for result in vector_results:
        paragraph_id = result.metadata.get("paragraph_id")
        if not paragraph_id:
            continue

        paragraph = db.get(ParagraphModel, paragraph_id)
        if paragraph is None:
            continue

        document = db.get(DocumentModel, paragraph.document_id)
        if document is None:
            continue

        retrieved.append(
            RetrievedParagraph(
                paragraph=paragraph,
                document=document,
                score=result.score,
            )
        )

    return retrieved
