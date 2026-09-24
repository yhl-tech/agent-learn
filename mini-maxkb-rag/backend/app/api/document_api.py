"""
文档 API。

这里暴露两个核心能力：
1. 上传文档并入库。
2. 查询知识库下的文档列表。

另外提供一个段落查看接口，便于学习时观察文本是怎么被切分的。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_embedding_service, get_vector_store
from app.schemas import DocumentRead, ParagraphRead
from app.services.document_service import list_document_paragraphs, list_documents, upload_document
from app.services.embedding_service import HashEmbeddingService
from app.storage.vector_store import ChromaVectorStore


router = APIRouter(tags=["documents"])


@router.post("/api/knowledges/{knowledge_id}/documents", response_model=DocumentRead)
async def upload_document_api(
    knowledge_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
):
    """
    上传文档。

    对应技术方案：
    POST /api/knowledges/{knowledge_id}/documents

    这个接口内部会完成：
    保存文件、读取文本、切分段落、生成向量、写入向量库、保存向量引用。
    """

    try:
        return await upload_document(
            db=db,
            knowledge_id=knowledge_id,
            upload_file=file,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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
