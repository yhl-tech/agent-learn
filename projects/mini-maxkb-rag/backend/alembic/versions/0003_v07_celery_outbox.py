"""v0.7 celery task delivery and transactional outbox

Revision ID: 0003_v07
Revises: 0002_v06
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_v07"
down_revision = "0002_v06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    把 v0.6 任务升级为 Celery + Transactional Outbox 状态机。

    除新增 attempt、租约和可观测字段外，还会创建 task_attempt 与
    outbox_event。迁移期间遗留的 RUNNING 任务无法证明仍有 Worker 执行，
    因此重置为 PENDING，并为所有活动任务回填一次待发布事件。
    """

    op.add_column("task", sa.Column("error_code", sa.String(80), nullable=True))
    op.add_column(
        "task",
        sa.Column(
            "attempt_no",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "task",
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3"),
        ),
    )
    op.add_column(
        "task",
        sa.Column("celery_task_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "task",
        sa.Column("idempotency_key", sa.String(160), nullable=True),
    )
    op.add_column("task", sa.Column("worker_id", sa.String(255), nullable=True))
    op.add_column("task", sa.Column("queued_at", sa.DateTime(), nullable=True))
    op.add_column("task", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))
    op.add_column(
        "task",
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
    )
    op.add_column("task", sa.Column("next_retry_at", sa.DateTime(), nullable=True))

    op.execute(
        "UPDATE task SET idempotency_key = 'legacy:' || id "
        "WHERE idempotency_key IS NULL"
    )
    op.alter_column("task", "idempotency_key", nullable=False)

    op.create_index("ix_task_error_code", "task", ["error_code"])
    op.create_index("ix_task_celery_task_id", "task", ["celery_task_id"])
    op.create_index(
        "ix_task_idempotency_key",
        "task",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index("ix_task_worker_id", "task", ["worker_id"])
    op.create_index(
        "ix_task_lease_expires_at",
        "task",
        ["lease_expires_at"],
    )
    op.create_index("ix_task_next_retry_at", "task", ["next_retry_at"])

    op.create_table(
        "task_attempt",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("worker_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.UniqueConstraint(
            "task_id",
            "attempt_no",
            name="uq_task_attempt_task_id_attempt_no",
        ),
    )
    op.create_index("ix_task_attempt_task_id", "task_attempt", ["task_id"])
    op.create_index("ix_task_attempt_status", "task_attempt", ["status"])

    op.create_table(
        "outbox_event",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("task_id", sa.String(64), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("deduplication_key", sa.String(200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("leased_until", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.UniqueConstraint(
            "deduplication_key",
            name="uq_outbox_event_deduplication_key",
        ),
    )
    op.create_index(
        "ix_outbox_event_event_type",
        "outbox_event",
        ["event_type"],
    )
    op.create_index("ix_outbox_event_task_id", "outbox_event", ["task_id"])
    op.create_index("ix_outbox_event_status", "outbox_event", ["status"])
    op.create_index(
        "ix_outbox_event_available_at",
        "outbox_event",
        ["available_at"],
    )
    op.create_index(
        "ix_outbox_event_leased_until",
        "outbox_event",
        ["leased_until"],
    )

    op.execute(
        """
        UPDATE task
        SET status = 'PENDING',
            worker_id = NULL,
            heartbeat_at = NULL,
            lease_expires_at = NULL
        WHERE status = 'RUNNING'
        """
    )
    op.execute(
        """
        INSERT INTO outbox_event (
            id,
            event_type,
            task_id,
            attempt_no,
            deduplication_key,
            payload,
            status,
            attempts,
            available_at,
            created_at,
            updated_at
        )
        SELECT
            'migration-' || md5(id || ':' || attempt_no::text),
            'DOCUMENT_INDEX_REQUESTED',
            id,
            attempt_no,
            'DOCUMENT_INDEX_REQUESTED:' || id || ':' || attempt_no::text,
            json_build_object('task_id', id, 'attempt_no', attempt_no),
            'PENDING',
            0,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM task
        WHERE status IN ('PENDING', 'QUEUED', 'RETRYING')
        """
    )


def downgrade() -> None:
    """
    删除 v0.7 投递与执行历史结构，并移除 task 扩展字段。

    回滚不会恢复迁移前 RUNNING 状态，也无法保留 task_attempt/outbox_event
    历史；基础 task 记录仍保留为 v0.6 结构。
    """

    op.drop_table("outbox_event")
    op.drop_table("task_attempt")

    op.drop_index("ix_task_next_retry_at", table_name="task")
    op.drop_index("ix_task_lease_expires_at", table_name="task")
    op.drop_index("ix_task_worker_id", table_name="task")
    op.drop_index("ix_task_idempotency_key", table_name="task")
    op.drop_index("ix_task_celery_task_id", table_name="task")
    op.drop_index("ix_task_error_code", table_name="task")

    op.drop_column("task", "next_retry_at")
    op.drop_column("task", "lease_expires_at")
    op.drop_column("task", "heartbeat_at")
    op.drop_column("task", "queued_at")
    op.drop_column("task", "worker_id")
    op.drop_column("task", "idempotency_key")
    op.drop_column("task", "celery_task_id")
    op.drop_column("task", "max_attempts")
    op.drop_column("task", "attempt_no")
    op.drop_column("task", "error_code")
