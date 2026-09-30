"""
Transactional Outbox 的数据库访问层。

生产 PostgreSQL 使用 ``FOR UPDATE SKIP LOCKED`` 让多个 Relay 并发领取事件；
SQLite 开发模式保持相同状态机，但不承诺多 Relay 并发。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.models import (
    OUTBOX_STATUS_DISCARDED,
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_PUBLISHED,
    OUTBOX_STATUS_PUBLISHING,
    TASK_STATUS_PENDING,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RETRYING,
    OutboxEventModel,
    TaskModel,
)


@dataclass(frozen=True)
class ClaimedOutboxEvent:
    """
    Relay 在短事务中取得的事件快照。

    发布阶段不持有 ORM Session；claim_attempt 用于防止租约过期的旧 Relay
    覆盖后来领取者写入的结果。
    """

    id: str
    event_type: str
    task_id: str
    attempt_no: int
    payload: dict
    claim_attempt: int


def claim_outbox_events(
    db: Session,
    batch_size: int,
    lease_seconds: int,
) -> list[ClaimedOutboxEvent]:
    """
    短事务领取一批可投递事件。

    网络发布发生在事务外，因此不会长期占用数据库行锁。Relay 在发布后崩溃时，
    PUBLISHING 事件会在租约到期后重新进入可领取范围。
    """

    current_time = datetime.utcnow()
    statement = (
        select(OutboxEventModel)
        .where(
            OutboxEventModel.available_at <= current_time,
            or_(
                OutboxEventModel.status == OUTBOX_STATUS_PENDING,
                and_(
                    OutboxEventModel.status == OUTBOX_STATUS_PUBLISHING,
                    OutboxEventModel.leased_until <= current_time,
                ),
            ),
        )
        .order_by(OutboxEventModel.available_at, OutboxEventModel.created_at)
        .limit(batch_size)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)

    events = list(db.scalars(statement).all())
    lease_expires_at = current_time + timedelta(seconds=lease_seconds)
    claimed = []
    for event in events:
        event.status = OUTBOX_STATUS_PUBLISHING
        event.leased_until = lease_expires_at
        event.attempts += 1
        claimed.append(
            ClaimedOutboxEvent(
                id=event.id,
                event_type=event.event_type,
                task_id=event.task_id,
                attempt_no=event.attempt_no,
                payload=dict(event.payload),
                claim_attempt=event.attempts,
            )
        )
    db.commit()
    return claimed


def mark_outbox_published(
    db: Session,
    event: ClaimedOutboxEvent,
    delivery_id: str,
) -> bool:
    """
    标记发布成功，并尽力把对应任务推进到 QUEUED。

    Worker 可能在此事务前已经完成，因此任务更新带状态条件，绝不覆盖 RUNNING
    或终态。Outbox 自身以 claim_attempt 防止过期 Relay 覆盖新一轮领取结果。
    """

    current_time = datetime.utcnow()
    result = db.execute(
        update(OutboxEventModel)
        .where(
            OutboxEventModel.id == event.id,
            OutboxEventModel.status == OUTBOX_STATUS_PUBLISHING,
            OutboxEventModel.attempts == event.claim_attempt,
        )
        .values(
            status=OUTBOX_STATUS_PUBLISHED,
            published_at=current_time,
            leased_until=None,
            last_error=None,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        return False

    db.execute(
        update(TaskModel)
        .where(
            TaskModel.id == event.task_id,
            TaskModel.attempt_no == event.attempt_no,
        )
        .values(celery_task_id=delivery_id)
    )
    db.execute(
        update(TaskModel)
        .where(
            TaskModel.id == event.task_id,
            TaskModel.attempt_no == event.attempt_no,
            TaskModel.status.in_({TASK_STATUS_PENDING, TASK_STATUS_RETRYING}),
            TaskModel.cancel_requested.is_(False),
        )
        .values(
            status=TASK_STATUS_QUEUED,
            queued_at=current_time,
        )
    )
    db.commit()
    return True


def mark_outbox_failed(
    db: Session,
    event: ClaimedOutboxEvent,
    error_message: str,
    retry_at: datetime,
) -> bool:
    """
    把发布失败事件退回 PENDING，并设置下一次可领取时间。

    只有当前 claim_attempt 仍然拥有租约时才更新；否则回滚并返回 False。
    """

    result = db.execute(
        update(OutboxEventModel)
        .where(
            OutboxEventModel.id == event.id,
            OutboxEventModel.status == OUTBOX_STATUS_PUBLISHING,
            OutboxEventModel.attempts == event.claim_attempt,
        )
        .values(
            status=OUTBOX_STATUS_PENDING,
            available_at=retry_at,
            leased_until=None,
            last_error=error_message,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        return False
    db.commit()
    return True


def discard_unpublished_task_events(
    db: Session,
    task_id: str,
    attempt_no: int,
) -> None:
    """
    将指定 attempt 尚未发布的事件标记为丢弃。

    此函数参与调用方的取消事务，不自行 commit。即使 Relay 已取得事件快照，
    Worker 后续仍需通过任务状态条件认领阻止已取消任务执行。
    """

    db.execute(
        update(OutboxEventModel)
        .where(
            OutboxEventModel.task_id == task_id,
            OutboxEventModel.attempt_no == attempt_no,
            OutboxEventModel.status.in_(
                {OUTBOX_STATUS_PENDING, OUTBOX_STATUS_PUBLISHING}
            ),
        )
        .values(
            status=OUTBOX_STATUS_DISCARDED,
            leased_until=None,
        )
    )
