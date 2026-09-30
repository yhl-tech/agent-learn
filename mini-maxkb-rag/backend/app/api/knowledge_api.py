"""
知识库 API。

这一层对应前端的“知识库列表”和“创建知识库”操作。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    KnowledgeCreate,
    KnowledgeMove,
    KnowledgeRead,
    RetrievalConfigUpdate,
)
from app.services.knowledge_folder_service import KnowledgeFolderNotFoundError
from app.services.knowledge_service import (
    KnowledgeNotFoundError,
    create_knowledge,
    list_knowledges,
    move_knowledge,
    update_retrieval_config,
)


router = APIRouter(prefix="/api/knowledges", tags=["knowledges"])


@router.post("", response_model=KnowledgeRead)
def create_knowledge_api(payload: KnowledgeCreate, db: Session = Depends(get_db)):
    """
    创建知识库。

    对应技术方案：
    POST /api/knowledges
    """

    try:
        return create_knowledge(db, payload)
    except KnowledgeFolderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("", response_model=list[KnowledgeRead])
def list_knowledges_api(db: Session = Depends(get_db)):
    """
    查询知识库列表。

    对应技术方案：
    GET /api/knowledges
    """

    return list_knowledges(db)


@router.patch("/{knowledge_id}/folder", response_model=KnowledgeRead)
def move_knowledge_api(
    knowledge_id: str,
    payload: KnowledgeMove,
    db: Session = Depends(get_db),
):
    """
    移动知识库到目标文件夹。

    请求中的 folder_id 为 null 时，知识库会回到根级。
    """

    try:
        return move_knowledge(db, knowledge_id, payload)
    except (KnowledgeNotFoundError, KnowledgeFolderNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/{knowledge_id}/retrieval-config", response_model=KnowledgeRead)
def update_retrieval_config_api(
    knowledge_id: str,
    payload: RetrievalConfigUpdate,
    db: Session = Depends(get_db),
):
    """
    局部更新知识库检索模式和阈值。
    """

    try:
        return update_retrieval_config(db, knowledge_id, payload)
    except KnowledgeNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
