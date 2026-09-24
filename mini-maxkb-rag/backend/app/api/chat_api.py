"""
问答 API。

这个文件对应 RAG 的查询链路：

用户问题
-> 生成问题向量
-> 检索相关段落
-> 组装回答和引用
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEFAULT_TOP_K
from app.database import get_db
from app.dependencies import get_embedding_service, get_vector_store
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import answer_question
from app.services.embedding_service import HashEmbeddingService
from app.services.knowledge_service import get_knowledge
from app.services.retrieval_service import retrieve_paragraphs
from app.storage.vector_store import ChromaVectorStore


router = APIRouter(prefix="/api/knowledges", tags=["chat"])


@router.post("/{knowledge_id}/chat", response_model=ChatResponse)
async def chat_api(
    knowledge_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
):
    """
    知识库问答。

    对应技术方案：
    POST /api/knowledges/{knowledge_id}/chat
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    top_k = payload.top_k or DEFAULT_TOP_K
    retrieved = retrieve_paragraphs(
        db=db,
        knowledge_id=knowledge_id,
        question=payload.question,
        top_k=top_k,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    try:
        return await answer_question(payload.question, retrieved)
    except Exception as error:
        # 这里主要兜底外部 LLM API 的网络错误或响应格式错误。
        # 检索已经成功时，如果生成失败，需要明确告诉前端是回答生成环节失败。
        raise HTTPException(status_code=502, detail=f"生成回答失败：{error}") from error
