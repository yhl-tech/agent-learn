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

from app.database import get_db
from app.dependencies import get_embedding_repository, get_embedding_service
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas import (
    ChatRequest,
    ChatResponse,
    RetrievalConfigRead,
    RetrievalTestRequest,
    RetrievalTestResponse,
)
from app.services.chat_service import answer_question, build_references
from app.services.embedding_service import HashEmbeddingService
from app.services.knowledge_service import get_knowledge
from app.services.retrieval_service import (
    resolve_retrieval_config,
    retrieve_paragraphs,
)


router = APIRouter(prefix="/api/knowledges", tags=["chat"])


@router.post("/{knowledge_id}/chat", response_model=ChatResponse)
async def chat_api(
    knowledge_id: str,
    payload: ChatRequest,
    # FastAPI 会调用 get_db，并把 yield 出来的 Session 注入 db；
    # 请求结束后，get_db 的 finally 会自动关闭 Session。
    db: Session = Depends(get_db),
    # 请求进入时，FastAPI 会调用 get_embedding_service()；
    # 函数返回的 HashEmbeddingService 实例会赋给 embedding_service。
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    # 向量后端由配置决定，业务接口只依赖统一仓库协议。
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
    """
    知识库问答。

    对应技术方案：
    POST /api/knowledges/{knowledge_id}/chat
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    config = resolve_retrieval_config(
        knowledge,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        search_mode=payload.search_mode,
        blend_weight=payload.blend_weight,
    )
    retrieved = retrieve_paragraphs(
        db=db,
        knowledge_id=knowledge_id,
        question=payload.question,
        **config,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    try:
        return await answer_question(payload.question, retrieved)
    except Exception as error:
        # 这里主要兜底外部 LLM API 的网络错误或响应格式错误。
        # 检索已经成功时，如果生成失败，需要明确告诉前端是回答生成环节失败。
        raise HTTPException(status_code=502, detail=f"生成回答失败：{error}") from error


@router.post(
    "/{knowledge_id}/retrieval-test",
    response_model=RetrievalTestResponse,
)
def retrieval_test_api(
    knowledge_id: str,
    payload: RetrievalTestRequest,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
    """
    执行检索调试，不调用大模型。

    响应包含本次实际生效的配置、命中类型和各路分数组成。
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    config = resolve_retrieval_config(
        knowledge,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        search_mode=payload.search_mode,
        blend_weight=payload.blend_weight,
    )
    retrieved = retrieve_paragraphs(
        db=db,
        knowledge_id=knowledge_id,
        question=payload.question,
        **config,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    return RetrievalTestResponse(
        config=RetrievalConfigRead.model_validate(config),
        results=build_references(retrieved),
    )
