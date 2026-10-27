"""
知识库文件夹 API。

这一层只负责 HTTP 状态码和参数转换；目录树校验、非空删除限制等业务规则
统一放在 knowledge_folder_service 中，便于接口测试和后续复用。
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    KnowledgeFolderCreate,
    KnowledgeFolderRead,
    KnowledgeFolderUpdate,
)
from app.services.knowledge_folder_service import (
    KnowledgeFolderConflictError,
    KnowledgeFolderNotFoundError,
    KnowledgeFolderValidationError,
    create_knowledge_folder,
    delete_knowledge_folder,
    list_knowledge_folder_tree,
    update_knowledge_folder,
)


router = APIRouter(prefix="/api/knowledge-folders", tags=["knowledge-folders"])


@router.post("", response_model=KnowledgeFolderRead)
def create_knowledge_folder_api(
    payload: KnowledgeFolderCreate,
    db: Session = Depends(get_db),
):
    """
    创建根文件夹或子文件夹。
    """

    try:
        return create_knowledge_folder(db, payload)
    except KnowledgeFolderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except KnowledgeFolderValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except KnowledgeFolderConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[KnowledgeFolderRead])
def list_knowledge_folder_tree_api(db: Session = Depends(get_db)):
    """
    查询完整文件夹树。
    """

    return list_knowledge_folder_tree(db)


@router.patch("/{folder_id}", response_model=KnowledgeFolderRead)
def update_knowledge_folder_api(
    folder_id: str,
    payload: KnowledgeFolderUpdate,
    db: Session = Depends(get_db),
):
    """
    修改文件夹信息或移动文件夹。
    """

    try:
        return update_knowledge_folder(db, folder_id, payload)
    except KnowledgeFolderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except KnowledgeFolderValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except KnowledgeFolderConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_folder_api(
    folder_id: str,
    db: Session = Depends(get_db),
):
    """
    删除一个不含子目录和知识库的空文件夹。
    """

    try:
        delete_knowledge_folder(db, folder_id)
    except KnowledgeFolderNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except KnowledgeFolderConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
