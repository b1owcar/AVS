from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.base import ModelAdapter
from app.adapters.comfyui_adapter import ComfySdxlAdapter, ComfyUIAdapter
from app.adapters.mock_adapter import MockImageAdapter, UnimplementedNativeAdapter
from app.adapters.sdxl_adapter import SdxlNativeAdapter
from app.core.config import Settings
from app.db.models import AssetRecord, TaskRecord
from app.db.session import session_factory

logger = logging.getLogger(__name__)

TERMINAL = {"completed", "failed", "cancelled"}
ACTIVE = {"pending", "preparing", "running", "cancelling"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskQueueService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._adapters: dict[str, ModelAdapter] = {
            "mock-demo": MockImageAdapter(),
            "sdxl-base-1.0": SdxlNativeAdapter(settings),
            "sdxl-comfyui": ComfySdxlAdapter(
                settings.comfyui_url,
                settings.comfyui_timeout_seconds,
                output_dir=settings.output_dir,
                default_checkpoint=settings.comfyui_checkpoint,
                comfy_output_dir=settings.comfyui_output_dir,
            ),
            "wan2.1-t2v-1.3b": UnimplementedNativeAdapter(
                "wan2.1-t2v-1.3b",
                "Wan 2.1 T2V 1.3B",
                ["text_to_video"],
            ),
            "comfyui-bridge": ComfyUIAdapter(
                settings.comfyui_url,
                settings.comfyui_timeout_seconds,
                output_dir=settings.output_dir,
                default_checkpoint=settings.comfyui_checkpoint,
                comfy_output_dir=settings.comfyui_output_dir,
            ),
        }
        self._cancel_flags: dict[str, bool] = {}

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._loop, name="lavs-task-worker", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=2)

    def create_task(
        self,
        db: Session,
        *,
        task_type: str,
        model_id: str,
        parameters: dict[str, Any],
        input_files: list[str] | None = None,
    ) -> TaskRecord:
        adapter = self._adapters.get(model_id)
        is_simulation = model_id == "mock-demo"
        cancellation = model_id in {"mock-demo", "sdxl-comfyui", "comfyui-bridge"}

        task = TaskRecord(
            id=str(uuid.uuid4()),
            task_type=task_type,
            model_id=model_id,
            status="pending",
            progress=0.0,
            parameters_json=json.dumps(parameters, ensure_ascii=False),
            input_files_json=json.dumps(input_files or [], ensure_ascii=False),
            output_files_json="[]",
            logs="",
            cancellation_supported=cancellation,
            is_simulation=is_simulation,
        )
        if adapter is None:
            task.cancellation_supported = False

        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def list_tasks(self, db: Session) -> list[TaskRecord]:
        return db.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()

    def get_task(self, db: Session, task_id: str) -> TaskRecord | None:
        return db.get(TaskRecord, task_id)

    def cancel_task(self, db: Session, task_id: str) -> TaskRecord:
        task = db.get(TaskRecord, task_id)
        if task is None:
            raise KeyError("task not found")
        if task.status in TERMINAL:
            raise ValueError(f"task already {task.status}")
        if task.status == "pending":
            task.status = "cancelled"
            task.finished_at = _utcnow()
            task.logs = (task.logs or "") + "\ncancelled while pending"
            db.commit()
            db.refresh(task)
            return task
        if not task.cancellation_supported:
            raise ValueError("cancellation not supported for this running task/model")
        task.status = "cancelling"
        self._cancel_flags[task_id] = True
        adapter = self._adapters.get(task.model_id)
        if adapter is not None:
            adapter.cancel()
        db.commit()
        db.refresh(task)
        return task

    def retry_task(self, db: Session, task_id: str) -> TaskRecord:
        old = db.get(TaskRecord, task_id)
        if old is None:
            raise KeyError("task not found")
        if old.status != "failed":
            raise ValueError("only failed tasks can be retried")
        return self.create_task(
            db,
            task_type=old.task_type,
            model_id=old.model_id,
            parameters=json.loads(old.parameters_json),
            input_files=json.loads(old.input_files_json),
        )

    def serialize(self, task: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": task.id,
            "task_type": task.task_type,
            "model_id": task.model_id,
            "status": task.status,
            "progress": task.progress,
            "parameters": json.loads(task.parameters_json),
            "input_files": json.loads(task.input_files_json),
            "output_files": json.loads(task.output_files_json),
            "logs": task.logs,
            "error_message": task.error_message,
            "cancellation_supported": task.cancellation_supported,
            "is_simulation": task.is_simulation,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        }

    def _append_log(self, db: Session, task: TaskRecord, line: str) -> None:
        task.logs = (task.logs or "") + ("\n" if task.logs else "") + line
        db.commit()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._process_next()
            except Exception:  # noqa: BLE001
                logger.exception("task worker iteration failed")
            self._stop.wait(0.4)

    def _adapter_ready(self, adapter: ModelAdapter) -> tuple[bool, str]:
        if isinstance(adapter, UnimplementedNativeAdapter):
            return False, "adapter unimplemented"
        if isinstance(adapter, MockImageAdapter):
            return True, "mock"
        try:
            env = adapter.validate_environment()
            if env.get("ok"):
                return True, str(env.get("message") or "ready")
            issues = env.get("issues") or [env.get("message") or "not ready"]
            if isinstance(issues, list):
                return False, "; ".join(str(i) for i in issues)
            return False, str(issues)
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _process_next(self) -> None:
        SessionLocal = session_factory()
        db = SessionLocal()
        try:
            running = (
                db.query(TaskRecord)
                .filter(TaskRecord.status.in_(["preparing", "running", "cancelling"]))
                .count()
            )
            if running >= self.settings.max_concurrent_gpu_tasks:
                return

            task = (
                db.query(TaskRecord)
                .filter(TaskRecord.status == "pending")
                .order_by(TaskRecord.created_at.asc())
                .first()
            )
            if task is None:
                return

            task.status = "preparing"
            task.started_at = _utcnow()
            db.commit()

            adapter = self._adapters.get(task.model_id)
            if adapter is None:
                task.status = "failed"
                task.error_message = f"No adapter registered for model_id={task.model_id}"
                task.finished_at = _utcnow()
                db.commit()
                return

            ready, reason = self._adapter_ready(adapter)
            if not ready:
                task.status = "failed"
                task.error_message = (
                    f"Model '{task.model_id}' is not ready: {reason}. "
                    "Install via scripts/windows/install-phase2.ps1 on D:\\avs."
                )
                task.finished_at = _utcnow()
                task.progress = 0.0
                self._append_log(db, task, task.error_message)
                return

            task.status = "running"
            db.commit()

            params = json.loads(task.parameters_json)
            out_dir = self.settings.output_dir / task.id
            params = {**params, "output_dir": str(out_dir)}

            def progress_cb(value: float, message: str) -> None:
                SessionLocal2 = session_factory()
                db2 = SessionLocal2()
                try:
                    t = db2.get(TaskRecord, task.id)
                    if t is None:
                        return
                    if self._cancel_flags.get(task.id):
                        return
                    t.progress = float(value)
                    t.logs = (t.logs or "") + f"\n{message}"
                    db2.commit()
                finally:
                    db2.close()

            try:
                result = adapter.execute(params, progress_cb=progress_cb)
                if self._cancel_flags.get(task.id):
                    task.status = "cancelled"
                    task.error_message = "cancelled"
                    task.finished_at = _utcnow()
                    db.commit()
                    return

                outputs = result.get("output_files", [])
                task.output_files_json = json.dumps(outputs, ensure_ascii=False)
                task.progress = 1.0
                task.status = "completed"
                task.finished_at = _utcnow()
                task.is_simulation = bool(result.get("is_simulation", task.is_simulation))
                self._append_log(db, task, result.get("message", "completed"))

                for path in outputs:
                    p = Path(path)
                    asset = AssetRecord(
                        id=str(uuid.uuid4()),
                        file_path=str(p),
                        file_type=p.suffix.lstrip(".") or "bin",
                        file_size=p.stat().st_size if p.exists() else 0,
                        source_task_id=task.id,
                        metadata_json=json.dumps({"is_simulation": task.is_simulation}),
                        is_original_input=False,
                        is_generated=True,
                    )
                    db.add(asset)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                if str(exc) == "cancelled" or self._cancel_flags.get(task.id):
                    task.status = "cancelled"
                    task.error_message = "cancelled"
                else:
                    task.status = "failed"
                    task.error_message = str(exc)
                task.finished_at = _utcnow()
                self._append_log(db, task, f"error: {exc}")
            finally:
                self._cancel_flags.pop(task.id, None)
        finally:
            db.close()
