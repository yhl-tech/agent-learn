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

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Callable
import uuid

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import TASK_MAX_ATTEMPTS
from app.models import (
    DOCUMENT_STATUS_FAILED,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_PROCESSING,
    DOCUMENT_STATUS_SUCCESS,
    EMBEDDING_SOURCE_PARAGRAPH,
    EMBEDDING_SOURCE_PROBLEM,
    TASK_STATUS_PENDING,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RETRYING,
    TASK_STATUS_RUNNING,
    TASK_TYPE_DOCUMENT_INDEX,
    DocumentModel,
    EmbeddingRefModel,
    FileModel,
    ParagraphModel,
    ProblemModel,
    ProblemParagraphMappingModel,
    TaskModel,
    new_id,
)
from app.repositories.document_repository import (
    get_document_by_id,
    list_documents_with_paragraph_count,
)
from app.repositories.embedding_repository import EmbeddingRepository
from app.services.chunk_service import split_text
from app.services.embedding_service import HashEmbeddingService
from app.services.knowledge_service import get_knowledge
from app.services.outbox_service import enqueue_document_task_event
from app.storage.file_storage import (
    calculate_file_sha256,
    delete_stored_file,
    read_text_file,
    resolve_stored_file_path,
    save_upload_file,
)


MAX_ERROR_MESSAGE_LENGTH = 1000
DOCUMENT_ERROR_CONTENT_INVALID = "CONTENT_INVALID"
DOCUMENT_ERROR_SOURCE_FILE_NOT_FOUND = "SOURCE_FILE_NOT_FOUND"
DOCUMENT_ERROR_TRANSIENT_INFRASTRUCTURE = "TRANSIENT_INFRASTRUCTURE"
DOCUMENT_ERROR_INDEXING_FAILED = "INDEXING_FAILED"


class DocumentContentError(ValueError):
    """
    表示文件格式有效，但文本内容无法进入切分和索引流程。

    这是用户可以修正的输入问题，API 层应返回 400。
    """


class DocumentProcessingError(RuntimeError):
    """
    表示数据库或向量库等内部处理环节失败。

    它和 DocumentContentError 分开，避免把服务端故障错误地返回成用户输入错误。
    """


class DocumentNotFoundError(LookupError):
    """
    表示文档 ID 不存在。

    单独定义异常类型，API 层才能稳定地区分 404 与内部处理失败。
    """


class DocumentStateConflictError(RuntimeError):
    """
    表示文档当前正在处理，不能同时执行重新索引。
    """


class SourceFileNotFoundError(LookupError):
    """
    表示文档存在，但关联的 File 元数据不存在。
    """


class DocumentIndexCancelledError(RuntimeError):
    """
    表示后台任务在阶段边界观察到取消请求。
    """


class DocumentIndexSupersededError(RuntimeError):
    """
    表示当前 Worker 的租约已被其他执行者接管。

    陈旧 Worker 只能回滚自己的数据库事务，不能清理共享的稳定 ID 向量。
    """


class DocumentIndexExecutionError(RuntimeError):
    """
    包装后台索引失败信息，供任务服务同时更新 Task 和 Document。
    """

    def __init__(
        self,
        message: str,
        char_length: int,
        error_code: str = DOCUMENT_ERROR_INDEXING_FAILED,
        transient: bool = False,
    ) -> None:
        super().__init__(message)
        self.char_length = char_length
        self.error_code = error_code
        self.transient = transient


@dataclass
class PreparedDocumentIndex:
    """
    尚未提交的完整索引批次。

    段落 ID 和向量 ID 在写入前一次性生成，使异常处理能够精确删除本批次
    可能已经写入 Chroma 的向量，而不会误删同一文档的旧索引。
    """

    paragraphs: list[ParagraphModel]
    vector_ids: list[str]
    embeddings: list[list[float]]
    documents: list[str]
    metadatas: list[dict]


@dataclass(frozen=True)
class IndexedParagraphSnapshot:
    """
    重新索引或删除前保存的旧索引快照。

    SQLite 和 Chroma 没有共同事务。外部向量删除后如果数据库提交失败，
    可以根据快照重新计算并 upsert 旧向量，恢复到操作前的可用状态。
    """

    vector_id: str
    knowledge_id: str
    document_id: str
    paragraph_id: str
    position: int
    content: str
    source_type: str
    problem_id: str | None


async def create_document_task(
    db: Session,
    knowledge_id: str,
    upload_file: UploadFile,
) -> tuple[DocumentModel, TaskModel]:
    """
    保存原始文件，并在同一事务中创建文档、任务和 Outbox 事件。

    事务提交后即使 API 进程退出，独立 Relay 仍能从数据库发现待投递事件。
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise ValueError("知识库不存在")

    file_path = await save_upload_file(knowledge_id, upload_file)
    file_name = upload_file.filename or file_path.name

    try:
        # File 和 PENDING Document 在同一事务中创建，避免出现只有一侧记录的
        # 半成品。实体文件已先落盘，事务失败时会在 except 中清理。
        source_file = FileModel(
            file_name=file_name,
            file_size=file_path.stat().st_size,
            sha256_hash=calculate_file_sha256(file_path),
            file_path=str(file_path),
        )
        db.add(source_file)
        db.flush()

        document = DocumentModel(
            knowledge_id=knowledge_id,
            source_file_id=source_file.id,
            name=file_name,
            # 兼容旧 SQLite 的 NOT NULL 列；业务读取不再依赖这个字段。
            file_path=str(file_path),
            char_length=0,
            status=DOCUMENT_STATUS_PENDING,
            error_message=None,
        )
        db.add(document)
        db.flush()

        task_id = new_id()
        task = TaskModel(
            id=task_id,
            type=TASK_TYPE_DOCUMENT_INDEX,
            status=TASK_STATUS_PENDING,
            document_id=document.id,
            error_message=None,
            error_code=None,
            retry_count=0,
            attempt_no=1,
            max_attempts=TASK_MAX_ATTEMPTS,
            idempotency_key=f"{TASK_TYPE_DOCUMENT_INDEX}:{document.id}",
            cancel_requested=False,
        )
        db.add(task)
        db.flush()
        enqueue_document_task_event(db, task)
        db.commit()
        db.refresh(document)
        db.refresh(task)
        document.paragraph_count = 0
        return document, task
    except DocumentIndexSupersededError:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        try:
            delete_stored_file(str(file_path))
        except Exception as cleanup_error:
            message = _build_compensated_error_message(error, cleanup_error)
            raise DocumentProcessingError(message) from error
        raise DocumentProcessingError(str(error)) from error


def process_pending_document(
    db: Session,
    document_id: str,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
    is_cancel_requested: Callable[[], bool],
    index_key: str | None = None,
) -> DocumentModel:
    """
    处理已经持久化的 PENDING 文档，但不提交最终成功状态。

    调用方负责把 Task.SUCCESS 与 Document.SUCCESS 一起 commit。失败时本函数
    会回滚段落事务并补偿外部 Chroma，随后抛出包含字符数的稳定异常。
    """

    document = get_document_by_id(db, document_id)
    if document is None:
        raise DocumentIndexExecutionError(
            "文档不存在",
            0,
            error_code=DOCUMENT_ERROR_SOURCE_FILE_NOT_FOUND,
        )
    try:
        _source_file, file_path = _resolve_document_source(db, document)
    except (SourceFileNotFoundError, ValueError) as error:
        raise DocumentIndexExecutionError(
            str(error),
            0,
            error_code=DOCUMENT_ERROR_SOURCE_FILE_NOT_FOUND,
        ) from error

    text_length = 0
    prepared_index: PreparedDocumentIndex | None = None
    try:
        text = read_text_file(file_path)
        text_length = len(text)
        if is_cancel_requested():
            raise DocumentIndexCancelledError("任务已取消")

        prepared_index = _prepare_document_index(
            knowledge_id=document.knowledge_id,
            document_id=document_id,
            text=text,
            embedding_service=embedding_service,
            index_key=index_key,
        )
        if is_cancel_requested():
            raise DocumentIndexCancelledError("任务已取消")

        _add_prepared_index(db, prepared_index, vector_store)
        if is_cancel_requested():
            raise DocumentIndexCancelledError("任务已取消")

        document.char_length = text_length
        document.status = DOCUMENT_STATUS_SUCCESS
        document.error_message = None
        document.paragraph_count = len(prepared_index.paragraphs)
        return document
    except Exception as error:
        db.rollback()
        new_vector_ids = prepared_index.vector_ids if prepared_index is not None else []
        cleanup_error = _delete_partial_vectors(db, vector_store, new_vector_ids)
        error_message = _build_error_message(error, cleanup_error)

        if isinstance(error, DocumentIndexCancelledError):
            raise DocumentIndexCancelledError(error_message) from error
        if isinstance(error, DocumentContentError):
            error_code = DOCUMENT_ERROR_CONTENT_INVALID
            transient = False
        elif isinstance(error, (ConnectionError, OperationalError, TimeoutError)):
            error_code = DOCUMENT_ERROR_TRANSIENT_INFRASTRUCTURE
            transient = True
        else:
            error_code = DOCUMENT_ERROR_INDEXING_FAILED
            transient = False
        raise DocumentIndexExecutionError(
            error_message,
            text_length,
            error_code=error_code,
            transient=transient,
        ) from error


def _prepare_document_index(
    knowledge_id: str,
    document_id: str,
    text: str,
    embedding_service: HashEmbeddingService,
    index_key: str | None = None,
) -> PreparedDocumentIndex:
    """
    在写数据库和 Chroma 前，先准备完整的段落与向量批次。

    提前生成所有 ID 的价值是：即使 Chroma 写入中途失败，调用方也知道
    本批次可能涉及哪些向量，可以按 ID 做精确补偿，而不是整篇文档删除。
    """

    chunks = split_text(text)
    if not chunks:
        raise DocumentContentError("文档内容为空，无法入库")

    batch_key = index_key or new_id()
    paragraphs = []
    for chunk in chunks:
        content_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        paragraph_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"mini-maxkb:paragraph:{batch_key}:{chunk.position}:{content_hash}",
            )
        )
        paragraphs.append(
            ParagraphModel(
                id=paragraph_id,
                knowledge_id=knowledge_id,
                document_id=document_id,
                title=_extract_chunk_title(chunk.content),
                content=chunk.content,
                position=chunk.position,
                chunk_length=len(chunk.content),
            )
        )
    documents = [paragraph.content for paragraph in paragraphs]
    vector_ids = [
        str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"mini-maxkb:vector:{paragraph.id}",
            )
        )
        for paragraph in paragraphs
    ]
    embeddings = embedding_service.embed_texts(documents)
    metadatas = [
        {
            "knowledge_id": knowledge_id,
            "document_id": document_id,
            "paragraph_id": paragraph.id,
            "position": paragraph.position,
            "source_type": EMBEDDING_SOURCE_PARAGRAPH,
        }
        for paragraph in paragraphs
    ]

    return PreparedDocumentIndex(
        paragraphs=paragraphs,
        vector_ids=vector_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def _add_prepared_index(
    db: Session,
    prepared_index: PreparedDocumentIndex,
    vector_store: EmbeddingRepository,
) -> None:
    """
    将准备好的同一批段落分别写入 SQLite 会话和 Chroma。

    SQLite 此时只 flush、不 commit；由上层在所有写入完成后统一提交。
    """

    db.add_all(prepared_index.paragraphs)
    db.flush()

    # Outbox/Celery 是至少一次投递，稳定 ID 配合 upsert 让 Worker 在崩溃重投
    # 时覆盖同一批索引，而不是制造重复向量。
    vector_store.upsert_paragraphs(
        db=db,
        ids=prepared_index.vector_ids,
        embeddings=prepared_index.embeddings,
        documents=prepared_index.documents,
        metadatas=prepared_index.metadatas,
    )


def _delete_partial_vectors(
    db: Session,
    vector_store: EmbeddingRepository,
    vector_ids: list[str],
) -> Exception | None:
    """
    尽最大努力清理失败文档已经写入的向量。

    清理失败不能覆盖最初的处理异常，否则排查时会丢失真正的失败原因。
    返回清理异常，由调用方把两部分信息一起记录到 error_message。
    """

    if vector_store.transactional:
        return None

    try:
        vector_store.delete_by_ids(db, vector_ids)
        return None
    except Exception as error:
        return error


def _build_error_message(error: Exception, cleanup_error: Exception | None) -> str:
    """
    生成适合持久化和返回给调用方的简短错误信息。

    限制长度可以避免第三方服务返回的大段响应无限写入数据库。
    """

    message = str(error).strip() or error.__class__.__name__
    if cleanup_error is not None:
        cleanup_message = str(cleanup_error).strip() or cleanup_error.__class__.__name__
        message = f"{message}；向量清理失败：{cleanup_message}"
    return message[:MAX_ERROR_MESSAGE_LENGTH]


def _load_index_snapshot(
    db: Session,
    document_id: str,
) -> tuple[list[IndexedParagraphSnapshot], list[str], list[str]]:
    """
    读取文档当前的段落 ID 和可恢复向量快照。

    paragraph_ids/problem_ids 包含没有 EmbeddingRef 的异常数据，确保替换索引时
    旧业务记录仍能全部删除；snapshots 只包含可以恢复向量的完整映射。
    """

    paragraphs = list(
        db.scalars(
            select(ParagraphModel)
            .where(ParagraphModel.document_id == document_id)
            .order_by(ParagraphModel.position.asc())
        ).all()
    )
    paragraph_ids = [paragraph.id for paragraph in paragraphs]
    paragraph_by_id = {paragraph.id: paragraph for paragraph in paragraphs}

    refs = list(
        db.scalars(
            select(EmbeddingRefModel).where(EmbeddingRefModel.document_id == document_id)
        ).all()
    )
    mapped_problem_ids = set(
        db.scalars(
            select(ProblemParagraphMappingModel.problem_id).where(
                ProblemParagraphMappingModel.document_id == document_id
            )
        ).all()
    )
    mapped_problem_ids.update(
        ref.problem_id for ref in refs if ref.problem_id is not None
    )
    problems_by_id = {
        problem.id: problem
        for problem in db.scalars(
            select(ProblemModel).where(ProblemModel.id.in_(mapped_problem_ids))
        ).all()
    } if mapped_problem_ids else {}

    snapshots = []
    for ref in refs:
        paragraph = paragraph_by_id.get(ref.paragraph_id)
        if paragraph is None:
            continue
        problem = problems_by_id.get(ref.problem_id) if ref.problem_id else None
        content = (
            problem.content
            if ref.source_type == EMBEDDING_SOURCE_PROBLEM and problem is not None
            else paragraph.content
        )
        snapshots.append(
            IndexedParagraphSnapshot(
                vector_id=ref.vector_id,
                knowledge_id=paragraph.knowledge_id,
                document_id=paragraph.document_id,
                paragraph_id=paragraph.id,
                position=paragraph.position,
                content=content,
                source_type=ref.source_type,
                problem_id=ref.problem_id,
            )
        )

    return snapshots, paragraph_ids, list(mapped_problem_ids)


def _restore_index_vectors(
    db: Session,
    snapshots: list[IndexedParagraphSnapshot],
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
) -> Exception | None:
    """
    在跨存储操作失败时恢复旧向量。

    使用 upsert 而不是 add，是因为向量删除可能只执行了一部分；upsert 对
    “仍存在”和“已删除”的 ID 都能得到相同结果，使补偿操作可以重复执行。
    """

    if not snapshots or vector_store.transactional:
        return None

    documents = [snapshot.content for snapshot in snapshots]
    try:
        vector_store.upsert_paragraphs(
            db=db,
            ids=[snapshot.vector_id for snapshot in snapshots],
            embeddings=embedding_service.embed_texts(documents),
            documents=documents,
            metadatas=[
                {
                    "knowledge_id": snapshot.knowledge_id,
                    "document_id": snapshot.document_id,
                    "paragraph_id": snapshot.paragraph_id,
                    "position": snapshot.position,
                    "source_type": snapshot.source_type,
                    **(
                        {"problem_id": snapshot.problem_id}
                        if snapshot.problem_id is not None
                        else {}
                    ),
                }
                for snapshot in snapshots
            ],
        )
        return None
    except Exception as error:
        return error


def _mark_document_failed(
    db: Session,
    document_id: str,
    error_message: str,
    char_length: int | None = None,
) -> None:
    """
    在独立事务中保存 FAILED 状态。

    调用前必须先 rollback 原处理事务，否则失败事务会阻止后续状态写入。
    """

    document = get_document_by_id(db, document_id)
    if document is None:
        return

    if char_length is not None:
        document.char_length = char_length
    document.status = DOCUMENT_STATUS_FAILED
    document.error_message = error_message
    db.commit()


def _build_compensated_error_message(
    error: Exception,
    *compensation_errors: Exception | None,
) -> str:
    """
    合并原始错误与补偿错误，同时限制最终数据库字段长度。
    """

    message = str(error).strip() or error.__class__.__name__
    details = [
        str(compensation_error).strip() or compensation_error.__class__.__name__
        for compensation_error in compensation_errors
        if compensation_error is not None
    ]
    if details:
        message = f"{message}；补偿处理失败：{'；'.join(details)}"
    return message[:MAX_ERROR_MESSAGE_LENGTH]


def _resolve_document_source(
    db: Session,
    document: DocumentModel,
) -> tuple[FileModel | None, Path]:
    """
    返回 File 记录和经过存储边界校验的实体路径。

    正常数据从 source_file_id 读取。旧数据库迁移不完整时允许回退到
    document.file_path，使用户仍能删除或重新索引旧文档；新写入流程始终会
    创建 File 记录。
    """

    source_file = (
        db.get(FileModel, document.source_file_id)
        if document.source_file_id is not None
        else None
    )
    stored_path = source_file.file_path if source_file is not None else document.file_path
    if not stored_path:
        raise SourceFileNotFoundError("文档缺少原始文件记录")

    return source_file, resolve_stored_file_path(stored_path)


def delete_document(
    db: Session,
    document_id: str,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
) -> None:
    """
    删除文档、段落、向量引用、Chroma 向量和原始文件。

    SQLite 和 Chroma 之间没有分布式事务。这里先记录旧索引快照，再删除
    Chroma 和 SQLite；如果数据库提交失败，则通过 upsert 恢复旧向量。
    """

    document = get_document_by_id(db, document_id)
    if document is None:
        raise DocumentNotFoundError("文档不存在")
    active_task_id = db.scalar(
        select(TaskModel.id).where(
            TaskModel.document_id == document_id,
            TaskModel.status.in_(
                {
                    TASK_STATUS_PENDING,
                    TASK_STATUS_QUEUED,
                    TASK_STATUS_RETRYING,
                    TASK_STATUS_RUNNING,
                }
            ),
        )
    )
    if active_task_id is not None:
        raise DocumentStateConflictError("文档任务尚未结束，不能删除")

    # 在任何破坏性操作前校验 File.file_path，防止异常路径指向上传目录之外。
    try:
        source_file, stored_file_path = _resolve_document_source(db, document)
    except (SourceFileNotFoundError, ValueError) as error:
        raise DocumentProcessingError(str(error)) from error
    snapshots, _paragraph_ids, problem_ids = _load_index_snapshot(db, document_id)
    vectors_touched = False
    delete_source_file = False

    if source_file is not None:
        other_document_count = db.scalar(
            select(func.count(DocumentModel.id)).where(
                DocumentModel.source_file_id == source_file.id,
                DocumentModel.id != document_id,
            )
        )
        delete_source_file = not other_document_count

    try:
        vectors_touched = True
        vector_store.delete_by_document(db, document_id)

        # 显式删除业务子记录，不依赖 SQLite 是否开启外键级联。
        db.execute(
            delete(ProblemParagraphMappingModel).where(
                ProblemParagraphMappingModel.document_id == document_id
            )
        )
        if problem_ids:
            db.execute(
                delete(ProblemModel).where(ProblemModel.id.in_(problem_ids))
            )
        db.execute(delete(ParagraphModel).where(ParagraphModel.document_id == document_id))
        db.delete(document)
        if delete_source_file:
            db.delete(source_file)
        db.commit()
    except Exception as error:
        db.rollback()
        restore_error = None
        if vectors_touched:
            restore_error = _restore_index_vectors(
                db,
                snapshots,
                embedding_service,
                vector_store,
            )
        error_message = _build_compensated_error_message(error, restore_error)
        raise DocumentProcessingError(error_message) from error

    # File 当前不会主动去重，但这里仍保护未来可能共享同一源文件的文档：
    # 只有最后一个引用被删除时才删除元数据和磁盘实体。
    if source_file is None or delete_source_file:
        try:
            delete_stored_file(str(stored_file_path))
        except Exception as error:
            # 此时业务记录与向量已经删除，不能再伪装成可回滚事务。
            # 明确返回“文件清理失败”，便于人工清理孤立文件。
            raise DocumentProcessingError(
                f"文档数据已删除，但原始文件清理失败：{error}"
            ) from error


def reindex_document(
    db: Session,
    document_id: str,
    embedding_service: HashEmbeddingService,
    vector_store: EmbeddingRepository,
) -> DocumentModel:
    """
    使用已保存的原始文件重新切分并替换文档索引。

    新向量先写入，旧向量随后按 ID 精确删除，最后提交 SQLite 中的新旧段落
    替换。如果任一步失败，SQLite 回滚并通过补偿操作恢复旧 Chroma 向量。
    """

    document = get_document_by_id(db, document_id)
    if document is None:
        raise DocumentNotFoundError("文档不存在")
    if document.status in {DOCUMENT_STATUS_PENDING, DOCUMENT_STATUS_PROCESSING}:
        raise DocumentStateConflictError("文档正在处理中，不能重复索引")

    try:
        source_file, file_path = _resolve_document_source(db, document)
    except (SourceFileNotFoundError, ValueError) as error:
        raise DocumentProcessingError(str(error)) from error
    snapshots, old_paragraph_ids, old_problem_ids = _load_index_snapshot(db, document_id)
    old_vector_ids = [snapshot.vector_id for snapshot in snapshots]

    document.status = DOCUMENT_STATUS_PROCESSING
    document.error_message = None
    db.commit()

    prepared_index: PreparedDocumentIndex | None = None
    text_length: int | None = None
    old_vectors_touched = False
    try:
        text = read_text_file(file_path)
        text_length = len(text)
        prepared_index = _prepare_document_index(
            knowledge_id=document.knowledge_id,
            document_id=document_id,
            text=text,
            embedding_service=embedding_service,
        )
        _add_prepared_index(db, prepared_index, vector_store)

        # 新向量已写入后再删除旧向量。如果删除或后续数据库提交失败，
        # except 分支会删除新向量并 upsert 旧快照。
        old_vectors_touched = bool(old_vector_ids)
        vector_store.delete_by_ids(db, old_vector_ids)
        db.execute(
            delete(ProblemParagraphMappingModel).where(
                ProblemParagraphMappingModel.document_id == document_id
            )
        )
        if old_problem_ids:
            db.execute(
                delete(ProblemModel).where(
                    ProblemModel.id.in_(old_problem_ids)
                )
            )
        if old_paragraph_ids:
            db.execute(
                delete(ParagraphModel).where(ParagraphModel.id.in_(old_paragraph_ids))
            )

        document.char_length = text_length
        document.status = DOCUMENT_STATUS_SUCCESS
        document.error_message = None
        if source_file is not None:
            # 测试或后续文件替换能力可能改变磁盘内容。只有新索引完整写入后，
            # 才在同一 SQLite 事务里刷新 File 元数据；失败回滚时保留旧值。
            source_file.file_size = file_path.stat().st_size
            source_file.sha256_hash = calculate_file_sha256(file_path)
        db.commit()
        db.refresh(document)
        document.paragraph_count = len(prepared_index.paragraphs)
        return document
    except Exception as error:
        db.rollback()

        new_vector_ids = prepared_index.vector_ids if prepared_index is not None else []
        cleanup_error = _delete_partial_vectors(db, vector_store, new_vector_ids)
        restore_error = None
        if old_vectors_touched:
            restore_error = _restore_index_vectors(
                db,
                snapshots,
                embedding_service,
                vector_store,
            )

        error_message = _build_compensated_error_message(
            error,
            cleanup_error,
            restore_error,
        )
        _mark_document_failed(
            db,
            document_id=document_id,
            error_message=error_message,
            char_length=text_length,
        )

        if isinstance(error, DocumentContentError):
            raise
        raise DocumentProcessingError(error_message) from error


def list_documents(db: Session, knowledge_id: str) -> list[DocumentModel]:
    """
    查询某个知识库下的文档列表。
    """

    documents = []
    for document, paragraph_count in list_documents_with_paragraph_count(
        db,
        knowledge_id,
    ):
        # paragraph_count 是接口展示字段，不持久化到 document 表。
        # 实时 COUNT 可以避免删除或重新索引后还要同步维护一份重复计数。
        document.paragraph_count = int(paragraph_count)
        documents.append(document)
    return documents


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


def get_document_source_file(
    db: Session,
    document_id: str,
) -> FileModel:
    """
    查询文档关联的原始文件元数据。

    API 只返回 File 表中的名称、大小和摘要，不暴露服务端绝对路径。
    """

    document = get_document_by_id(db, document_id)
    if document is None:
        raise DocumentNotFoundError("文档不存在")
    if document.source_file_id is None:
        raise SourceFileNotFoundError("文档缺少原始文件记录")

    source_file = db.get(FileModel, document.source_file_id)
    if source_file is None:
        raise SourceFileNotFoundError("文档关联的原始文件不存在")
    return source_file


def _extract_chunk_title(content: str) -> str:
    """
    从 Markdown 段落首行提取简短标题。

    普通文本没有可靠标题时返回空字符串，不把内容片段伪装成标题。标题主要用于
    FTS5 提高 Markdown heading 的关键词权重。
    """

    first_line = content.splitlines()[0].strip() if content else ""
    if not first_line.startswith("#"):
        return ""
    return first_line.lstrip("#").strip()[:255]
