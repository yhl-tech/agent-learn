"""
知识库 API。

这一层对应前端的“知识库列表”和“创建知识库”操作。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import KnowledgeCreate, KnowledgeRead
from app.services.knowledge_service import create_knowledge, list_knowledges


router = APIRouter(prefix="/api/knowledges", tags=["knowledges"])


@router.post("", response_model=KnowledgeRead)
def create_knowledge_api(payload: KnowledgeCreate, db: Session = Depends(get_db)):
    """
    创建知识库。

    对应技术方案：
    POST /api/knowledges
    """

    return create_knowledge(db, payload)


@router.get("", response_model=list[KnowledgeRead])
def list_knowledges_api(db: Session = Depends(get_db)):
    """
    查询知识库列表。

    对应技术方案：
    GET /api/knowledges
    """

    return list_knowledges(db)
