"""v0.6 persistent background tasks

Revision ID: 0002_v06
Revises: 0001_v05
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_v06"
down_revision = "0001_v05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    新增 v0.6 持久化后台任务表。

    本版本记录任务基础状态、错误、重试次数和取消标记；消息投递和单次执行
    历史由后续 v0.7 迁移补充。
    """

    op.create_table(
        "task",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
    )
    op.create_index("ix_task_type", "task", ["type"])
    op.create_index("ix_task_status", "task", ["status"])
    op.create_index("ix_task_document_id", "task", ["document_id"])


def downgrade() -> None:
    """
    删除后台任务表，不影响已完成的文档和索引数据。
    """

    op.drop_table("task")
