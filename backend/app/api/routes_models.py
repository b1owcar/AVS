from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbDep
from app.db.models import ModelRecord
from app.services.model_registry import serialize_model

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models(db: DbDep) -> dict:
    rows = db.query(ModelRecord).order_by(ModelRecord.display_name.asc()).all()
    return {"models": [serialize_model(r) for r in rows]}


@router.get("/{model_id}")
def get_model(model_id: str, db: DbDep) -> dict:
    row = db.get(ModelRecord, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")
    return serialize_model(row)


@router.post("/{model_id}/download")
def request_download(model_id: str, db: DbDep) -> dict:
    """Download is intentionally deferred. Remote-dev mode never fetches weights."""
    row = db.get(ModelRecord, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")
    if model_id == "mock-demo":
        return {
            "ok": True,
            "model_id": model_id,
            "status": "not_required",
            "message": "Mock model has no weights to download.",
        }
    return {
        "ok": False,
        "model_id": model_id,
        "status": "deferred",
        "download_url": row.download_url,
        "download_size_hint": row.download_size_hint,
        "message": (
            "Weight download is blocked in remote development mode. "
            "Trigger downloads only on the target PC after reviewing license, disk space, and deps."
        ),
        "verification_status": "PENDING TARGET HARDWARE",
    }
