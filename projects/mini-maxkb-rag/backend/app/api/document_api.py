"""
文档 API。

这里暴露文档管理的核心能力：
1. 上传文档并入库。
2. 查询知识库下的文档列表。
3. 查看文档切分后的段落。
4. 删除文档及其全部存储数据。
5. 使用原始文件重新建立索引。
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_embedding_repository, get_embedding_service
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas import DocumentRead, DocumentUploadRead, FileRead, ParagraphRead
from app.services.document_service import (
    DocumentContentError,
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentStateConflictError,
    SourceFileNotFoundError,
    create_document_task,
    delete_document,
    get_document_source_file,
    list_document_paragraphs,
    list_documents,
    reindex_document,
)
from app.services.embedding_service import HashEmbeddingService
router = APIRouter(tags=["documents"])


@router.post(
    "/api/knowledges/{knowledge_id}/documents",
    response_model=DocumentUploadRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document_api(
    knowledge_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """
    上传文档。

    对应技术方案：
    POST /api/knowledges/{knowledge_id}/documents

    接口只提交文件、任务和 Outbox；耗时索引由 Relay/Worker 异步执行。
    """

    try:
        document, task = await create_document_task(
            db=db,
            knowledge_id=knowledge_id,
            upload_file=file,
        )
        return DocumentUploadRead(
            **DocumentRead.model_validate(document).model_dump(),
            task=task,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except DocumentProcessingError as error:
        # 文件已经通过前置校验，但数据库、Embedding 或 Chroma 处理失败时，
        # 返回 500，并保留数据库里的 FAILED 状态供后续查询和重新索引。
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/knowledges/{knowledge_id}/documents", response_model=list[DocumentRead])
def list_documents_api(knowledge_id: str, db: Session = Depends(get_db)):
    """
    查询知识库下的文档列表。

    对应技术方案：
    GET /api/knowledges/{knowledge_id}/documents
    """

    return list_documents(db, knowledge_id)


@router.get("/api/documents/{document_id}/paragraphs", response_model=list[ParagraphRead])
def list_document_paragraphs_api(document_id: str, db: Session = Depends(get_db)):
    """
    查询文档段落。

    这是调试 RAG 非常重要的接口。
    如果问答效果不好，第一步通常就是看切出来的段落是否合理。
    """

    return list_document_paragraphs(db, document_id)


@router.get("/api/documents/{document_id}/file", response_model=FileRead)
def get_document_source_file_api(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    查询文档对应的原始文件元数据。
    """

    try:
        return get_document_source_file(db, document_id)
    except (DocumentNotFoundError, SourceFileNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_api(
    document_id: str,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
    """
    删除文档及其关联的段落、向量引用、Chroma 向量和原始文件。

    204 表示删除成功且响应没有正文。
    """

    try:
        delete_document(
            db=db,
            document_id=document_id,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DocumentProcessingError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/documents/{document_id}/reindex", response_model=DocumentRead)
def reindex_document_api(
    document_id: str,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
    """
    使用已保存的原始文件重新切分并替换文档索引。
    """

    try:
        return reindex_document(
            db=db,
            document_id=document_id,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DocumentContentError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except DocumentProcessingError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
