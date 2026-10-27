"""
Transactional Outbox 写入、发布和 Relay 生命周期。
"""

from __future__ import annotations

import logging
import random
import socket
import threading
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.config import (
    OUTBOX_BATCH_SIZE,
    OUTBOX_LEASE_SECONDS,
    OUTBOX_POLL_INTERVAL_SECONDS,
    TASK_EXECUTOR,
)
from app.database import SessionLocal
from app.models import (
    OUTBOX_EVENT_DOCUMENT_INDEX,
    OUTBOX_STATUS_PENDING,
    OutboxEventModel,
    TaskModel,
    new_id,
)
from app.repositories.outbox_repository import (
    ClaimedOutboxEvent,
    claim_outbox_events,
    mark_outbox_failed,
    mark_outbox_published,
)


logger = logging.getLogger(__name__)
MAX_OUTBOX_ERROR_LENGTH = 1000


class TaskPublisher(Protocol):
    """
    Outbox Relay 可替换的消息发布边界。
    """

    def publish(self, event: ClaimedOutboxEvent) -> str:
        """
        发布事件并返回可用于追踪或撤销投递的 delivery_id。
        """
        ...


def enqueue_document_task_event(
    db: Session,
    task: TaskModel,
    available_at: datetime | None = None,
) -> OutboxEventModel:
    """
    在调用方业务事务内创建文档索引事件，不在此处提交。
    """

    event = OutboxEventModel(
        event_type=OUTBOX_EVENT_DOCUMENT_INDEX,
        task_id=task.id,
        attempt_no=task.attempt_no,
        deduplication_key=f"{OUTBOX_EVENT_DOCUMENT_INDEX}:{task.id}:{task.attempt_no}",
        payload={
            "task_id": task.id,
            "attempt_no": task.attempt_no,
        },
        status=OUTBOX_STATUS_PENDING,
        attempts=0,
        available_at=available_at or datetime.utcnow(),
    )
    db.add(event)
    return event


class CeleryTaskPublisher:
    """
    Relay 到 Redis/Celery 的薄适配器。
    """

    def publish(self, event: ClaimedOutboxEvent) -> str:
        """
        向 Celery 发送最小任务载荷。

        send_task 成功后进程仍可能在 Outbox 回写前退出，因此这里不承诺恰好
        一次投递；重复消息由 Worker 的 attempt 条件认领消化。
        """

        if event.event_type != OUTBOX_EVENT_DOCUMENT_INDEX:
            raise ValueError(f"不支持的 Outbox 事件类型：{event.event_type}")

        from app.celery_app import celery_app

        delivery_id = new_id()
        celery_app.send_task(
            "app.tasks.document_tasks.run_document_index",
            args=[
                str(event.payload["task_id"]),
                int(event.payload["attempt_no"]),
            ],
            task_id=delivery_id,
        )
        return delivery_id


class BackgroundTaskPublisher:
    """
    单机开发执行器。

    Relay 自己就是后台线程，因此这里同步执行任务。只有任务执行返回后才把
    Outbox 标记为 PUBLISHED；进程中途退出时租约会让事件在下次启动后重放。
    """

    def __init__(
        self,
        embedding_service=None,
        vector_store=None,
        worker_id: str | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.worker_id = worker_id or f"background@{socket.gethostname()}"

    def publish(self, event: ClaimedOutboxEvent) -> str:
        """
        在当前 Relay 线程同步执行一次任务，用于无 Redis 的本地开发。
        """

        if event.event_type != OUTBOX_EVENT_DOCUMENT_INDEX:
            raise ValueError(f"不支持的 Outbox 事件类型：{event.event_type}")

        from app.services.task_service import run_document_task

        delivery_id = new_id()
        run_document_task(
            task_id=str(event.payload["task_id"]),
            attempt_no=int(event.payload["attempt_no"]),
            worker_id=self.worker_id,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
        )
        return delivery_id


def get_task_publisher() -> TaskPublisher:
    """
    根据配置选择生产 Celery 或单机后台执行器。
    """

    if TASK_EXECUTOR == "celery":
        return CeleryTaskPublisher()
    return BackgroundTaskPublisher()


def dispatch_outbox_batch(
    publisher: TaskPublisher | None = None,
    session_factory: sessionmaker = SessionLocal,
    batch_size: int = OUTBOX_BATCH_SIZE,
    lease_seconds: int = OUTBOX_LEASE_SECONDS,
) -> int:
    """
    领取并发布一批事件，返回领取数量。

    每个发布结果使用独立短事务落库，单条故障不会阻塞同批其他事件。
    返回领取数量而非成功数量，使 Relay 在有持续积压时立即处理下一批。
    """

    with session_factory() as db:
        events = claim_outbox_events(db, batch_size, lease_seconds)

    if not events:
        return 0

    active_publisher = publisher or get_task_publisher()
    for event in events:
        try:
            delivery_id = active_publisher.publish(event)
        except Exception as error:
            message = (str(error).strip() or error.__class__.__name__)[
                :MAX_OUTBOX_ERROR_LENGTH
            ]
            retry_at = datetime.utcnow() + timedelta(
                seconds=_outbox_retry_delay(event.claim_attempt)
            )
            with session_factory() as db:
                mark_outbox_failed(db, event, message, retry_at)
            logger.exception("Outbox 事件发布失败: event_id=%s", event.id)
            continue

        with session_factory() as db:
            mark_outbox_published(db, event, delivery_id)
    return len(events)


def _outbox_retry_delay(attempt: int) -> float:
    """
    计算带随机抖动的指数退避，最高以 60 秒为基数。
    """

    base = min(60.0, float(2 ** min(max(attempt - 1, 0), 6)))
    return base + random.uniform(0.0, min(base * 0.2, 5.0))


class OutboxRelay:
    """
    可嵌入 Web 开发进程，也可由命令行独立运行的轮询 Relay。
    """

    def __init__(
        self,
        publisher: TaskPublisher | None = None,
        session_factory: sessionmaker = SessionLocal,
        poll_interval: float = OUTBOX_POLL_INTERVAL_SECONDS,
    ) -> None:
        self.publisher = publisher
        self.session_factory = session_factory
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """
        幂等启动内嵌 Relay 守护线程。
        """

        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self.run,
            name="outbox-relay",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """
        通知轮询线程退出，并等待一个有限时间。
        """

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.poll_interval * 2))

    def run(self) -> None:
        """
        持续处理 Outbox；仅在没有可领取事件时等待轮询间隔。

        批次级异常被记录后继续循环，避免单次数据库或 broker 抖动永久终止
        Relay 进程。
        """

        while not self._stop_event.is_set():
            try:
                claimed_count = dispatch_outbox_batch(
                    publisher=self.publisher,
                    session_factory=self.session_factory,
                )
            except Exception:
                logger.exception("Outbox Relay 批次执行失败")
                claimed_count = 0

            if claimed_count == 0:
                self._stop_event.wait(self.poll_interval)
