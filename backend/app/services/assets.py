from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import AssetRecord, TaskRecord
from app.services.path_safety import UnsafePathError, resolve_under, safe_filename

ACTIVE_STATUSES = {"pending", "preparing", "running", "cancelling"}


class AssetService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_assets(self, db: Session) -> list[dict[str, Any]]:
        rows = db.query(AssetRecord).order_by(AssetRecord.created_at.desc()).all()
        return [self.serialize(r) for r in rows]

    def serialize(self, asset: AssetRecord) -> dict[str, Any]:
        return {
            "asset_id": asset.id,
            "file_path": asset.file_path,
            "file_type": asset.file_type,
            "file_size": asset.file_size,
            "source_task_id": asset.source_task_id,
            "metadata": json.loads(asset.metadata_json or "{}"),
            "is_original_input": asset.is_original_input,
            "is_generated": asset.is_generated,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        }

    async def save_upload(self, db: Session, upload: UploadFile) -> dict[str, Any]:
        filename = safe_filename(upload.filename or "upload.bin")
        asset_id = str(uuid.uuid4())
        dest_dir = self.settings.upload_dir / asset_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename

        size = 0
        with dest.open("wb") as fh:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                fh.write(chunk)

        record = AssetRecord(
            id=asset_id,
            file_path=str(dest),
            file_type=dest.suffix.lstrip(".") or "bin",
            file_size=size,
            source_task_id=None,
            metadata_json=json.dumps({"original_filename": filename}),
            is_original_input=True,
            is_generated=False,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self.serialize(record)

    def delete_asset(self, db: Session, asset_id: str) -> None:
        asset = db.get(AssetRecord, asset_id)
        if asset is None:
            raise KeyError("asset not found")

        # Block delete if used by active tasks
        active = (
            db.query(TaskRecord)
            .filter(TaskRecord.status.in_(ACTIVE_STATUSES))
            .all()
        )
        for task in active:
            inputs = json.loads(task.input_files_json or "[]")
            if asset.file_path in inputs or asset_id in inputs:
                raise ValueError("asset is in use by an active task")

        path = Path(asset.file_path)
        try:
            # Only delete files under upload/output roots
            under_upload = False
            under_output = False
            try:
                resolve_under(self.settings.upload_dir, path)
                under_upload = True
            except UnsafePathError:
                pass
            try:
                resolve_under(self.settings.output_dir, path)
                under_output = True
            except UnsafePathError:
                pass
            if under_upload or under_output:
                if path.is_file():
                    path.unlink()
                parent = path.parent
                if parent.exists() and parent != self.settings.upload_dir and parent != self.settings.output_dir:
                    try:
                        next(parent.iterdir())
                    except StopIteration:
                        parent.rmdir()
        except Exception:
            # Keep DB consistent even if filesystem cleanup partially fails
            pass

        db.delete(asset)
        db.commit()
