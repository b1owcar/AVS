from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.services.assets import AssetService
from app.services.task_queue import TaskQueueService


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
DbDep = Annotated[Session, Depends(get_session)]


def queue_dep(request: Request) -> TaskQueueService:
    return request.app.state.queue


def assets_dep(settings: SettingsDep) -> AssetService:
    return AssetService(settings)


QueueDep = Annotated[TaskQueueService, Depends(queue_dep)]
AssetsDep = Annotated[AssetService, Depends(assets_dep)]
