"""
Celery 应用配置。

Redis 只承担 broker；任务结果和状态统一读取 PostgreSQL 的 task 表。
Worker 使用 late ack 和单任务预取，消息可能因进程退出或可见性超时而重投，
因此任务函数必须依赖数据库 attempt 条件认领来保证幂等。
"""

from celery import Celery

from app.config import (
    CELERY_BROKER_URL,
    CELERY_TASK_SOFT_TIME_LIMIT,
    CELERY_TASK_TIME_LIMIT,
    CELERY_VISIBILITY_TIMEOUT,
)


celery_app = Celery(
    "mini_maxkb_rag",
    broker=CELERY_BROKER_URL,
    backend=None,
    include=["app.tasks.document_tasks"],
)
celery_app.conf.update(
    # 消息只携带 task_id 和 attempt_no，限制为 JSON 可避免传递 Session、
    # ORM 对象等无法跨进程安全序列化的运行时对象。
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_ignore_result=True,
    task_store_errors_even_if_ignored=False,
    # 任务完成后再确认消息。Worker 异常退出时 broker 会重新投递，由数据库
    # 状态机识别重复消息或接管租约已过期的执行。
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": CELERY_VISIBILITY_TIMEOUT,
    },
    task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=CELERY_TASK_TIME_LIMIT,
    enable_utc=True,
    timezone="UTC",
)
