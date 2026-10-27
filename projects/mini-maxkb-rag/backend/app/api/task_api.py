"""
后台任务 API。

接口只读取或推动数据库中的任务状态机，不直接执行文档索引。任务重试通过
同一事务写入 Task 和 OutboxEvent，取消则以数据库标记为准；Redis/Celery
只负责消息投递，不是任务状态的事实来源。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TaskRead
from app.services.task_service import (
    TaskNotFoundError,
    TaskStateConflictError,
    cancel_task,
    get_task,
    revoke_task_delivery,
    retry_task,
)


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskRead)
def get_task_api(task_id: str, db: Session = Depends(get_db)):
    """
    查询任务当前状态。

    状态直接来自数据库；任务不存在时返回 404。
    """

    try:
        return get_task(db, task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{task_id}/retry",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_task_api(
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    为失败或已取消任务创建新一轮执行，成功受理后返回 202。

    service 会原子更新任务 attempt 并写入 Outbox 事件，API 不直接向 Redis
    发消息。任务不存在返回 404，当前状态不允许重试返回 409。
    """

    try:
        task = retry_task(db, task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except TaskStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return task


@router.post("/{task_id}/cancel", response_model=TaskRead)
def cancel_task_api(task_id: str, db: Session = Depends(get_db)):
    """
    请求取消尚未结束的任务。

    service 先持久化 cancel_requested 或直接写入 CANCELLED；随后对 Celery
    消息执行尽力撤销。即使 broker 暂时不可用，Worker 仍会以数据库标记拒绝
    或中止执行。任务不存在返回 404，终态冲突返回 409。
    """

    try:
        task = cancel_task(db, task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except TaskStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    revoke_task_delivery(task.celery_task_id)
    return task
