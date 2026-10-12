from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbDep, QueueDep
from app.schemas.api import TaskCreateRequest

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(db: DbDep, queue: QueueDep) -> dict:
    return {"tasks": [queue.serialize(t) for t in queue.list_tasks(db)]}


@router.post("")
def create_task(body: TaskCreateRequest, db: DbDep, queue: QueueDep) -> dict:
    task = queue.create_task(
        db,
        task_type=body.task_type,
        model_id=body.model_id,
        parameters=body.parameters,
        input_files=body.input_files,
    )
    return queue.serialize(task)


@router.get("/{task_id}")
def get_task(task_id: str, db: DbDep, queue: QueueDep) -> dict:
    task = queue.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return queue.serialize(task)


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, db: DbDep, queue: QueueDep) -> dict:
    try:
        task = queue.cancel_task(db, task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return queue.serialize(task)


@router.post("/{task_id}/retry")
def retry_task(task_id: str, db: DbDep, queue: QueueDep) -> dict:
    try:
        task = queue.retry_task(db, task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return queue.serialize(task)
