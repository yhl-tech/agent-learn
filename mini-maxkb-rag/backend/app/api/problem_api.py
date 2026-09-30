"""
问题增强 API。

当前学习版通过显式问题文本创建增强语料。后续接入问题生成模型时，可以复用
同一 service 写入链路，只替换问题文本的来源。
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_embedding_repository, get_embedding_service
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas import ProblemCreate, ProblemRead
from app.services.embedding_service import HashEmbeddingService
from app.services.problem_service import (
    ProblemConflictError,
    ProblemContentError,
    ProblemNotFoundError,
    ProblemParagraphNotFoundError,
    ProblemProcessingError,
    create_problem_for_paragraph,
    delete_problem,
    list_paragraph_problems,
)


router = APIRouter(tags=["problems"])


@router.post(
    "/api/paragraphs/{paragraph_id}/problems",
    response_model=ProblemRead,
)
def create_problem_for_paragraph_api(
    paragraph_id: str,
    payload: ProblemCreate,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
    """
    为段落创建一条问题增强语料并建立向量索引。
    """

    try:
        return create_problem_for_paragraph(
            db=db,
            paragraph_id=paragraph_id,
            payload=payload,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
    except ProblemParagraphNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProblemContentError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ProblemConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ProblemProcessingError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get(
    "/api/paragraphs/{paragraph_id}/problems",
    response_model=list[ProblemRead],
)
def list_paragraph_problems_api(
    paragraph_id: str,
    db: Session = Depends(get_db),
):
    """
    查询段落关联的问题。
    """

    try:
        return list_paragraph_problems(db, paragraph_id)
    except ProblemParagraphNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/api/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem_api(
    problem_id: str,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
    """
    删除问题、段落映射和问题向量。
    """

    try:
        delete_problem(
            db=db,
            problem_id=problem_id,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
    except ProblemNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProblemProcessingError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
