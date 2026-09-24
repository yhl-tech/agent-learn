"""
文档服务。

这个文件负责文档入库主流程：

上传文件
-> 保存原始文件
-> 读取文本
-> 创建 Document
-> 切分 Paragraph
-> 生成 Embedding
-> 写入 Chroma
-> 保存 EmbeddingRef
"""

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentModel, EmbeddingRefModel, ParagraphModel, new_id
from app.services.chunk_service import split_text
from app.services.embedding_service import HashEmbeddingService
from app.services.knowledge_service import get_knowledge
from app.storage.file_storage import read_text_file, save_upload_file
from app.storage.vector_store import ChromaVectorStore


async def upload_document(
    db: Session,
    knowledge_id: str,
    upload_file: UploadFile,
    embedding_service: HashEmbeddingService,
    vector_store: ChromaVectorStore,
) -> DocumentModel:
    """
    上传并索引文档。

    这里为了学习清晰，先用同步流程：
    API 请求会一直等到文件保存、切分、向量写入全部完成。

    生产项目中，这段逻辑通常会拆成异步任务：
    上传接口只保存文件和创建任务，Worker 再慢慢处理向量化。
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise ValueError("知识库不存在")

    file_path = await save_upload_file(knowledge_id, upload_file)
    text = read_text_file(file_path)
    chunks = split_text(text)

    if not chunks:
        raise ValueError("文档内容为空，无法入库")

    document = DocumentModel(
        knowledge_id=knowledge_id,
        name=upload_file.filename or file_path.name,
        file_path=str(file_path),
        char_length=len(text),
    )
    db.add(document)
    db.flush()

    paragraphs: list[ParagraphModel] = []
    for chunk in chunks:
        paragraph = ParagraphModel(
            knowledge_id=knowledge_id,
            document_id=document.id,
            content=chunk.content,
            position=chunk.position,
        )
        db.add(paragraph)
        paragraphs.append(paragraph)

    # flush 会把上面新增的 paragraph 写到数据库会话中，并生成 paragraph.id。
    # 这里还没有 commit；如果后面的向量写入失败，仍然可以 rollback。
    db.flush()

    vector_ids = [new_id() for _ in paragraphs]
    embeddings = embedding_service.embed_texts([paragraph.content for paragraph in paragraphs])
    metadatas = [
        {
            "knowledge_id": knowledge_id,
            "document_id": document.id,
            "paragraph_id": paragraph.id,
            "position": paragraph.position,
        }
        for paragraph in paragraphs
    ]

    vector_store.add_paragraphs(
        ids=vector_ids,
        embeddings=embeddings,
        documents=[paragraph.content for paragraph in paragraphs],
        metadatas=metadatas,
    )

    for vector_id, paragraph in zip(vector_ids, paragraphs):
        db.add(
            EmbeddingRefModel(
                knowledge_id=knowledge_id,
                document_id=document.id,
                paragraph_id=paragraph.id,
                vector_id=vector_id,
            )
        )

    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, knowledge_id: str) -> list[DocumentModel]:
    """
    查询某个知识库下的文档列表。
    """

    statement = (
        select(DocumentModel)
        .where(DocumentModel.knowledge_id == knowledge_id)
        .order_by(DocumentModel.created_at.desc())
    )
    return list(db.scalars(statement).all())


def list_document_paragraphs(db: Session, document_id: str) -> list[ParagraphModel]:
    """
    查询文档切分后的段落。

    这个接口属于 v0.2 的能力，但对调试非常有帮助，所以后端先实现。
    """

    statement = (
        select(ParagraphModel)
        .where(ParagraphModel.document_id == document_id)
        .order_by(ParagraphModel.position.asc())
    )
    return list(db.scalars(statement).all())
