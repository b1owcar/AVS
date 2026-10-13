from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.deps import DbDep, SettingsDep
from app.db.models import ModelRecord
from app.services.model_registry import serialize_model
from app.services.readiness import install_hints, refresh_model_availability

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models(db: DbDep, settings: SettingsDep) -> dict:
    refresh_model_availability(db, settings)
    rows = db.query(ModelRecord).order_by(ModelRecord.display_name.asc()).all()
    return {"models": [serialize_model(r) for r in rows], "install": install_hints(settings)}


@router.get("/{model_id}")
def get_model(model_id: str, db: DbDep, settings: SettingsDep) -> dict:
    refresh_model_availability(db, settings)
    row = db.get(ModelRecord, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")
    return serialize_model(row)


@router.post("/refresh")
def refresh(db: DbDep, settings: SettingsDep) -> dict:
    report = refresh_model_availability(db, settings)
    return {"ok": True, "report": report}


@router.post("/{model_id}/download")
def request_download(model_id: str, db: DbDep, settings: SettingsDep, request: Request) -> dict:
    """User-triggered download guidance. Actual large downloads run via PowerShell on D:\\avs."""
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

    if not settings.allow_model_download:
        return {
            "ok": False,
            "model_id": model_id,
            "status": "deferred",
            "download_url": row.download_url,
            "download_size_hint": row.download_size_hint,
            "message": (
                "Set LAVS_ALLOW_MODEL_DOWNLOAD=1 in D:\\avs\\.env after reviewing the license, "
                "then run scripts\\windows\\install-sdxl.ps1 -DownloadWeights "
                "(or install-phase2.ps1). The API does not stream multi-GB weights itself."
            ),
            "install": install_hints(settings),
        }

    # Office mode: point operator to the local installer (safer than streaming in-process)
    script = "scripts\\windows\\install-sdxl.ps1 -DownloadWeights"
    if model_id.startswith("sdxl-comfy") or model_id == "comfyui-bridge":
        script = "scripts\\windows\\install-comfyui.ps1 -DownloadSdxlCheckpoint"
    return {
        "ok": True,
        "model_id": model_id,
        "status": "run_local_installer",
        "download_url": row.download_url,
        "download_size_hint": row.download_size_hint,
        "message": (
            f"Downloads are enabled. On the office PC run from D:\\avs: "
            f"powershell -ExecutionPolicy Bypass -File {script}"
        ),
        "command": script,
        "install": install_hints(settings),
    }
