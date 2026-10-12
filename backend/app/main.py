from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_assets, routes_models, routes_system, routes_tasks
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import init_db, session_factory
from app.services.model_registry import seed_models
from app.services.task_queue import TaskQueueService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_directories()
    setup_logging(settings.log_dir)
    init_db(settings)

    db = session_factory()()
    try:
        seed_models(db)
    finally:
        db.close()

    queue = TaskQueueService(settings)
    queue.start()
    app.state.settings = settings
    app.state.queue = queue
    try:
        yield
    finally:
        queue.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_system.router, prefix="/api")
    app.include_router(routes_models.router, prefix="/api")
    app.include_router(routes_tasks.router, prefix="/api")
    app.include_router(routes_assets.router, prefix="/api")
    return app


app = create_app()
