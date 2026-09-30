"""
数据库驱动的文档索引任务状态机。

Task/TaskAttempt 是执行状态的唯一事实来源。Celery 只提供至少一次消息投递，
因此每次 Worker 执行都必须先按 task_id + attempt_no 条件认领。
"""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timedelta

from billiard.exceptions import SoftTimeLimitExceeded
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import (
    TASK_HEARTBEAT_INTERVAL_SECONDS,
    TASK_LEASE_SECONDS,
    TASK_MAX_ATTEMPTS,
    TASK_RETRY_BASE_SECONDS,
    TASK_RETRY_MAX_SECONDS,
)
from app.database import SessionLocal
from app.models import (
    DOCUMENT_STATUS_CANCELLED,
    DOCUMENT_STATUS_FAILED,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_PROCESSING,
    TASK_ATTEMPT_STATUS_CANCELLED,
    TASK_ATTEMPT_STATUS_FAILED,
    TASK_ATTEMPT_STATUS_RUNNING,
    TASK_ATTEMPT_STATUS_SUCCESS,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RETRYING,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    TASK_TYPE_DOCUMENT_INDEX,
    DocumentModel,
    TaskAttemptModel,
    TaskModel,
)
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.outbox_repository import discard_unpublished_task_events
from app.services.document_service import (
    DocumentIndexCancelledError,
    DocumentIndexExecutionError,
    DocumentIndexSupersededError,
    MAX_ERROR_MESSAGE_LENGTH,
    process_pending_document,
)
from app.services.embedding_service import HashEmbeddingService
from app.services.outbox_service import enqueue_document_task_event


TASK_ERROR_DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
TASK_ERROR_INDEXING_FAILED = "INDEXING_FAILED"
TASK_ERROR_TRANSIENT_INFRASTRUCTURE = "TRANSIENT_INFRASTRUCTURE"

TASK_RUN_SUCCESS = "SUCCESS"
TASK_RUN_RETRY_SCHEDULED = "RETRY_SCHEDULED"
TASK_RUN_FAILED = "FAILED"
TASK_RUN_CANCELLED = "CANCELLED"
TASK_RUN_IGNORED = "IGNORED"


class TaskNotFoundError(LookupError):
    """
    表示任务 ID 不存在。
    """


class TaskStateConflictError(RuntimeError):
    """
    表示当前任务状态不允许重试或取消。
    """


def get_task(db: Session, task_id: str) -> TaskModel:
    """
    查询任务，不存在时转换成 API 层可识别的领域异常。
    """

    task = db.get(TaskModel, task_id)
    if task is None:
        raise TaskNotFoundError("任务不存在")
    return task


def retry_task(db: Session, task_id: str) -> TaskModel:
    """
    为失败或已取消任务创建一个新的 attempt 和 Outbox 事件。

    人工重试会重新授予完整的自动重试额度，同时旧消息因 attempt_no 不匹配而
    失效。
    """

    task = get_task(db, task_id)
    if task.type != TASK_TYPE_DOCUMENT_INDEX:
        raise TaskStateConflictError("当前任务类型不支持重试")
    if task.status not in {TASK_STATUS_FAILED, TASK_STATUS_CANCELLED}:
        raise TaskStateConflictError("只有失败或已取消的任务可以重试")

    document = db.get(DocumentModel, task.document_id)
    if document is None:
        raise TaskStateConflictError("任务关联的文档不存在")

    task.attempt_no += 1
    task.max_attempts = max(
        task.max_attempts,
        task.attempt_no + TASK_MAX_ATTEMPTS - 1,
    )
    task.retry_count += 1
    task.status = TASK_STATUS_RETRYING
    task.error_code = None
    task.error_message = None
    task.started_at = None
    task.finished_at = None
    task.celery_task_id = None
    task.worker_id = None
    task.queued_at = None
    task.heartbeat_at = None
    task.lease_expires_at = None
    task.next_retry_at = datetime.utcnow()
    task.cancel_requested = False

    document.status = DOCUMENT_STATUS_PENDING
    document.error_message = None
    enqueue_document_task_event(db, task, task.next_retry_at)
    db.commit()
    db.refresh(task)
    return task


def cancel_task(db: Session, task_id: str) -> TaskModel:
    """
    记录取消请求。

    未执行任务直接进入 CANCELLED；RUNNING 任务只写取消标记，由 Worker 在阶段
    边界清理并落终态。Redis revoke 只是减少无效消费，数据库标记才是最终判断。
    """

    task = get_task(db, task_id)
    if task.status == TASK_STATUS_CANCELLED:
        return task
    if task.status not in {
        TASK_STATUS_PENDING,
        TASK_STATUS_QUEUED,
        TASK_STATUS_RETRYING,
        TASK_STATUS_RUNNING,
    }:
        raise TaskStateConflictError("当前任务状态不允许取消")

    task.cancel_requested = True
    discard_unpublished_task_events(db, task.id, task.attempt_no)

    if task.status != TASK_STATUS_RUNNING:
        task.status = TASK_STATUS_CANCELLED
        task.finished_at = datetime.utcnow()
        task.lease_expires_at = None
        document = db.get(DocumentModel, task.document_id)
        if document is not None:
            document.status = DOCUMENT_STATUS_CANCELLED
            document.error_message = None
    db.commit()
    db.refresh(task)
    return task


def revoke_task_delivery(celery_task_id: str | None) -> None:
    """
    尽力撤销尚未开始的 Celery 消息，绝不强杀正在运行的 Worker。
    """

    if not celery_task_id:
        return
    try:
        from app.celery_app import celery_app

        celery_app.control.revoke(celery_task_id, terminate=False)
    except Exception:
        # 取消标记已持久化。Broker 暂时不可用时，后续 Worker 仍会在认领前拒绝
        # 该任务，因此这里不能把成功的业务取消回滚成 API 失败。
        return


def run_document_task(
    task_id: str,
    attempt_no: int,
    worker_id: str,
    embedding_service: HashEmbeddingService | None = None,
    vector_store: EmbeddingRepository | None = None,
    session_factory: sessionmaker = SessionLocal,
) -> str:
    """
    条件认领并执行一次文档索引。

    返回值只用于测试和本地观察；Celery 已关闭 result backend，不依赖此结果。
    """

    if embedding_service is None or vector_store is None:
        from app.dependencies import (
            get_embedding_repository,
            get_embedding_service,
        )

        embedding_service = embedding_service or get_embedding_service()
        vector_store = vector_store or get_embedding_repository()

    with session_factory() as db:
        document_id = _claim_task(
            db,
            task_id=task_id,
            attempt_no=attempt_no,
            worker_id=worker_id,
        )
        if document_id is None:
            return TASK_RUN_IGNORED

        document = db.get(DocumentModel, document_id)
        if document is None:
            db.rollback()
            _mark_task_failed(
                db,
                task_id=task_id,
                attempt_no=attempt_no,
                worker_id=worker_id,
                error_code=TASK_ERROR_DOCUMENT_NOT_FOUND,
                error_message="任务关联的文档不存在",
                char_length=0,
            )
            return TASK_RUN_FAILED

        control = _TaskExecutionControl(
            task_id=task_id,
            attempt_no=attempt_no,
            worker_id=worker_id,
            session_factory=session_factory,
        )
        control.start()
        try:
            process_pending_document(
                db=db,
                document_id=document.id,
                embedding_service=embedding_service,
                vector_store=vector_store,
                is_cancel_requested=control.check_cancelled_and_heartbeat,
                index_key=task_id,
            )

            success_result = db.execute(
                update(TaskModel)
                .where(
                    TaskModel.id == task_id,
                    TaskModel.attempt_no == attempt_no,
                    TaskModel.status == TASK_STATUS_RUNNING,
                    TaskModel.worker_id == worker_id,
                    TaskModel.cancel_requested.is_(False),
                )
                .values(
                    status=TASK_STATUS_SUCCESS,
                    error_code=None,
                    error_message=None,
                    heartbeat_at=datetime.utcnow(),
                    lease_expires_at=None,
                    next_retry_at=None,
                    finished_at=datetime.utcnow(),
                )
            )
            if success_result.rowcount != 1:
                # 另一个同 attempt 的重投可能已经完成。此时只回滚当前数据库
                # 事务，不清理稳定 ID 向量，避免删除获胜执行者的结果。
                db.rollback()
                return TASK_RUN_IGNORED

            _finish_attempt(
                db,
                task_id,
                attempt_no,
                TASK_ATTEMPT_STATUS_SUCCESS,
            )
            db.commit()
            return TASK_RUN_SUCCESS
        except DocumentIndexSupersededError:
            db.rollback()
            return TASK_RUN_IGNORED
        except DocumentIndexCancelledError:
            db.rollback()
            if not _owns_task_attempt(db, task_id, attempt_no, worker_id):
                return TASK_RUN_IGNORED
            cleanup_error = _cleanup_cancelled_vectors(
                db,
                document.id,
                vector_store,
            )
            _mark_task_cancelled(
                db,
                task_id,
                attempt_no,
                worker_id,
                cleanup_error,
            )
            return TASK_RUN_CANCELLED
        except DocumentIndexExecutionError as error:
            db.rollback()
            return _handle_task_failure(
                db,
                task_id=task_id,
                attempt_no=attempt_no,
                worker_id=worker_id,
                error_code=error.error_code,
                error_message=str(error),
                char_length=error.char_length,
                transient=error.transient,
            )
        except Exception as error:
            db.rollback()
            message = (str(error).strip() or error.__class__.__name__)[
                :MAX_ERROR_MESSAGE_LENGTH
            ]
            return _handle_task_failure(
                db,
                task_id=task_id,
                attempt_no=attempt_no,
                worker_id=worker_id,
                error_code=(
                    TASK_ERROR_TRANSIENT_INFRASTRUCTURE
                    if _is_transient_error(error)
                    else TASK_ERROR_INDEXING_FAILED
                ),
                error_message=message,
                char_length=0,
                transient=_is_transient_error(error),
            )
        finally:
            control.stop()


def _claim_task(
    db: Session,
    task_id: str,
    attempt_no: int,
    worker_id: str,
) -> str | None:
    """
    用单条条件 UPDATE 原子认领当前 attempt。

    可认领范围包括待执行状态和租约已过期的 RUNNING 状态。attempt_no、
    cancel_requested、重试时间和 worker 租约共同阻止旧消息或并发 Worker
    重复执行。认领结果先提交，再开始耗时索引，避免长时间持有任务行锁。
    """

    current_time = datetime.utcnow()
    lease_expires_at = current_time + timedelta(seconds=TASK_LEASE_SECONDS)
    claimable_state = or_(
        TaskModel.status.in_(
            {TASK_STATUS_PENDING, TASK_STATUS_QUEUED, TASK_STATUS_RETRYING}
        ),
        and_(
            TaskModel.status == TASK_STATUS_RUNNING,
            TaskModel.lease_expires_at <= current_time,
        ),
    )
    retry_is_available = or_(
        TaskModel.status != TASK_STATUS_RETRYING,
        TaskModel.next_retry_at.is_(None),
        TaskModel.next_retry_at <= current_time,
    )
    claim_result = db.execute(
        update(TaskModel)
        .where(
            TaskModel.id == task_id,
            TaskModel.type == TASK_TYPE_DOCUMENT_INDEX,
            TaskModel.attempt_no == attempt_no,
            TaskModel.cancel_requested.is_(False),
            claimable_state,
            retry_is_available,
        )
        .values(
            status=TASK_STATUS_RUNNING,
            worker_id=worker_id,
            started_at=current_time,
            finished_at=None,
            error_code=None,
            error_message=None,
            heartbeat_at=current_time,
            lease_expires_at=lease_expires_at,
        )
    )
    if claim_result.rowcount != 1:
        db.rollback()
        return None

    task = db.get(TaskModel, task_id)
    if task is None:
        db.rollback()
        return None

    attempt = db.scalar(
        select(TaskAttemptModel).where(
            TaskAttemptModel.task_id == task_id,
            TaskAttemptModel.attempt_no == attempt_no,
        )
    )
    if attempt is None:
        attempt = TaskAttemptModel(
            task_id=task_id,
            attempt_no=attempt_no,
            status=TASK_ATTEMPT_STATUS_RUNNING,
            worker_id=worker_id,
            started_at=current_time,
            heartbeat_at=current_time,
        )
        db.add(attempt)
    else:
        attempt.status = TASK_ATTEMPT_STATUS_RUNNING
        attempt.worker_id = worker_id
        attempt.heartbeat_at = current_time
        attempt.finished_at = None
        attempt.error_code = None
        attempt.error_message = None

    document = db.get(DocumentModel, task.document_id)
    if document is not None:
        document.status = DOCUMENT_STATUS_PROCESSING
        document.error_message = None
    db.commit()
    return task.document_id


class _TaskExecutionControl:
    """
    长任务的租约续期与协作式取消控制器。

    心跳使用独立 Session，不能提交或回滚正文索引事务。阶段边界检查还会验证
    attempt 和 worker 所有权，租约接管后旧 Worker 会停止继续写入。
    """

    def __init__(
        self,
        task_id: str,
        attempt_no: int,
        worker_id: str,
        session_factory: sessionmaker,
    ) -> None:
        self.task_id = task_id
        self.attempt_no = attempt_no
        self.worker_id = worker_id
        self.session_factory = session_factory
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """
        启动守护心跳线程。
        """

        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"task-heartbeat-{self.task_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """
        停止心跳并短暂等待线程退出。
        """

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _heartbeat_loop(self) -> None:
        """
        按固定间隔续租；所有权丢失后立即结束。
        """

        while not self._stop_event.wait(TASK_HEARTBEAT_INTERVAL_SECONDS):
            if not self._heartbeat():
                return

    def check_cancelled_and_heartbeat(self) -> bool:
        """
        使用独立 Session 读取取消标记。

        心跳线程也使用独立事务，避免续租意外提交正文索引事务。
        """

        with self.session_factory() as db:
            task = db.get(TaskModel, self.task_id)
            if task is None:
                raise DocumentIndexSupersededError("任务已不存在")
            if (
                task.attempt_no != self.attempt_no
                or task.status != TASK_STATUS_RUNNING
                or task.worker_id != self.worker_id
            ):
                raise DocumentIndexSupersededError("任务已由其他 Worker 接管")
            if task.cancel_requested:
                return True

            return False

    def _heartbeat(self) -> bool:
        """
        条件更新任务租约和 attempt 心跳，返回当前 Worker 是否仍有所有权。
        """

        current_time = datetime.utcnow()
        lease_expires_at = current_time + timedelta(seconds=TASK_LEASE_SECONDS)
        with self.session_factory() as db:
            try:
                result = db.execute(
                    update(TaskModel)
                    .where(
                        TaskModel.id == self.task_id,
                        TaskModel.attempt_no == self.attempt_no,
                        TaskModel.status == TASK_STATUS_RUNNING,
                        TaskModel.worker_id == self.worker_id,
                        TaskModel.cancel_requested.is_(False),
                    )
                    .values(
                        heartbeat_at=current_time,
                        lease_expires_at=lease_expires_at,
                    )
                )
                if result.rowcount != 1:
                    db.rollback()
                    return False
                db.execute(
                    update(TaskAttemptModel)
                    .where(
                        TaskAttemptModel.task_id == self.task_id,
                        TaskAttemptModel.attempt_no == self.attempt_no,
                    )
                    .values(heartbeat_at=current_time)
                )
                db.commit()
                return True
            except OperationalError:
                # SQLite 在索引事务持有写锁时可能无法续租。生产 PostgreSQL
                # 不受此限制；开发任务会在下一个周期继续尝试。
                db.rollback()
                return True


def _cleanup_cancelled_vectors(
    db: Session,
    document_id: str,
    vector_store: EmbeddingRepository,
) -> Exception | None:
    """
    清理取消执行可能写入的外部向量，并以返回值保留补偿失败详情。

    pgvector 与业务数据共享事务，rollback 已完成清理；只有 Chroma 等非事务
    后端需要显式删除。
    """

    if vector_store.transactional:
        return None
    try:
        vector_store.delete_by_document(db, document_id)
        return None
    except Exception as error:
        db.rollback()
        return error


def _mark_task_cancelled(
    db: Session,
    task_id: str,
    attempt_no: int,
    worker_id: str,
    cleanup_error: Exception | None,
) -> None:
    """
    在当前 Worker 仍拥有 attempt 时写入任务、文档和执行记录的取消终态。

    向量补偿失败不会把取消改成失败，但会写入 error_message 供人工治理。
    """

    task = db.get(TaskModel, task_id)
    if (
        task is None
        or task.attempt_no != attempt_no
        or task.status != TASK_STATUS_RUNNING
        or task.worker_id != worker_id
    ):
        return
    document = db.get(DocumentModel, task.document_id)
    message = None
    if cleanup_error is not None:
        detail = str(cleanup_error).strip() or cleanup_error.__class__.__name__
        message = f"任务已取消；向量清理失败：{detail}"[:MAX_ERROR_MESSAGE_LENGTH]

    task.status = TASK_STATUS_CANCELLED
    task.cancel_requested = True
    task.error_message = message
    task.error_code = None
    task.lease_expires_at = None
    task.finished_at = datetime.utcnow()
    if document is not None:
        document.status = DOCUMENT_STATUS_CANCELLED
        document.error_message = message
    _finish_attempt(
        db,
        task_id,
        attempt_no,
        TASK_ATTEMPT_STATUS_CANCELLED,
        error_message=message,
    )
    db.commit()


def _handle_task_failure(
    db: Session,
    task_id: str,
    attempt_no: int,
    worker_id: str,
    error_code: str,
    error_message: str,
    char_length: int,
    transient: bool,
) -> str:
    """
    按错误类型和重试额度推进失败状态机。

    临时错误会在同一事务内结束旧 attempt、递增 attempt_no 并创建延迟 Outbox
    事件；永久错误或额度耗尽则同步把 Task 和 Document 写入 FAILED。
    """

    task = db.get(TaskModel, task_id)
    if (
        task is None
        or task.attempt_no != attempt_no
        or task.status != TASK_STATUS_RUNNING
        or task.worker_id != worker_id
    ):
        return TASK_RUN_IGNORED
    if task.cancel_requested:
        _mark_task_cancelled(db, task_id, attempt_no, worker_id, None)
        return TASK_RUN_CANCELLED

    message = error_message[:MAX_ERROR_MESSAGE_LENGTH]
    document = db.get(DocumentModel, task.document_id)
    _finish_attempt(
        db,
        task_id,
        attempt_no,
        TASK_ATTEMPT_STATUS_FAILED,
        error_code=error_code,
        error_message=message,
    )

    if transient and attempt_no < task.max_attempts:
        next_attempt = attempt_no + 1
        retry_at = datetime.utcnow() + timedelta(
            seconds=_task_retry_delay(task.id, attempt_no)
        )
        task.status = TASK_STATUS_RETRYING
        task.attempt_no = next_attempt
        task.retry_count += 1
        task.error_code = error_code
        task.error_message = message
        task.worker_id = None
        task.celery_task_id = None
        task.queued_at = None
        task.heartbeat_at = None
        task.lease_expires_at = None
        task.next_retry_at = retry_at
        task.finished_at = None
        if document is not None:
            document.char_length = char_length
            document.status = DOCUMENT_STATUS_PENDING
            document.error_message = message
        enqueue_document_task_event(db, task, retry_at)
        db.commit()
        return TASK_RUN_RETRY_SCHEDULED

    task.status = TASK_STATUS_FAILED
    task.error_code = error_code
    task.error_message = message
    task.lease_expires_at = None
    task.next_retry_at = None
    task.finished_at = datetime.utcnow()
    if document is not None:
        document.char_length = char_length
        document.status = DOCUMENT_STATUS_FAILED
        document.error_message = message
    db.commit()
    return TASK_RUN_FAILED


def _mark_task_failed(
    db: Session,
    task_id: str,
    attempt_no: int,
    worker_id: str,
    error_code: str,
    error_message: str,
    char_length: int,
) -> None:
    """
    将无法恢复的前置错误直接落为失败，不进入自动重试。
    """

    _handle_task_failure(
        db,
        task_id=task_id,
        attempt_no=attempt_no,
        worker_id=worker_id,
        error_code=error_code,
        error_message=error_message,
        char_length=char_length,
        transient=False,
    )


def _owns_task_attempt(
    db: Session,
    task_id: str,
    attempt_no: int,
    worker_id: str,
) -> bool:
    """
    回滚索引事务后重新确认当前 Worker 是否仍拥有该 attempt。
    """

    task = db.get(TaskModel, task_id)
    if task is None:
        return False
    db.refresh(
        task,
        attribute_names=[
            "attempt_no",
            "status",
            "worker_id",
            "cancel_requested",
        ],
    )
    return (
        task.attempt_no == attempt_no
        and task.status == TASK_STATUS_RUNNING
        and task.worker_id == worker_id
    )


def _finish_attempt(
    db: Session,
    task_id: str,
    attempt_no: int,
    status: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """
    更新单次执行历史；事务提交由外层状态转换统一负责。
    """

    attempt = db.scalar(
        select(TaskAttemptModel).where(
            TaskAttemptModel.task_id == task_id,
            TaskAttemptModel.attempt_no == attempt_no,
        )
    )
    if attempt is None:
        return
    attempt.status = status
    attempt.finished_at = datetime.utcnow()
    attempt.error_code = error_code
    attempt.error_message = error_message


def _task_retry_delay(task_id: str, attempt_no: int) -> float:
    """
    计算指数退避，并用任务标识生成可重复的 0-20% 抖动。

    确定性抖动既分散同批故障任务，又让测试和问题复现保持稳定。
    """

    exponential = min(
        TASK_RETRY_MAX_SECONDS,
        TASK_RETRY_BASE_SECONDS * (2 ** max(attempt_no - 1, 0)),
    )
    digest = hashlib.sha256(f"{task_id}:{attempt_no}".encode("utf-8")).digest()
    jitter_ratio = int.from_bytes(digest[:2], "big") / 65535
    return exponential + exponential * 0.2 * jitter_ratio


def _is_transient_error(error: Exception) -> bool:
    """
    仅把明确的连接、数据库或超时故障归为可自动重试。
    """

    return isinstance(
        error,
        (
            ConnectionError,
            OperationalError,
            SoftTimeLimitExceeded,
            TimeoutError,
        ),
    )
