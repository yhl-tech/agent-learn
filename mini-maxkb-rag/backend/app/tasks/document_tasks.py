"""
Celery 文档任务入口。

消息参数保持最小化；数据库和向量服务都由 Worker 进程自行构造。
"""

from app.celery_app import celery_app
from app.services.task_service import run_document_task


@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.run_document_index",
    ignore_result=True,
)
def run_document_index(self, task_id: str, attempt_no: int) -> None:
    """
    把 Celery 投递上下文转换为数据库任务执行调用。

    消息可能重复或延迟到达，不能在此假设它仍然有效；run_document_task 会用
    task_id、attempt_no 和 worker_id 条件认领，只有认领成功才处理文档。
    """

    worker_id = self.request.hostname or "celery-worker"
    run_document_task(
        task_id=task_id,
        attempt_no=attempt_no,
        worker_id=worker_id,
    )
