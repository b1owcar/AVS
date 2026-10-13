from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.comfyui_adapter import ComfyUIAdapter
from app.adapters.sdxl_adapter import SdxlNativeAdapter
from app.core.config import Settings
from app.db.models import ModelRecord


def refresh_model_availability(db: Session, settings: Settings) -> dict[str, Any]:
    """Update registry rows from on-disk / ComfyUI readiness (no hardware verification)."""
    report: dict[str, Any] = {}

    sdxl = SdxlNativeAdapter(settings)
    sdxl_env = sdxl.validate_environment()
    row = db.get(ModelRecord, "sdxl-base-1.0")
    if row is not None:
        if sdxl_env.get("ok"):
            row.environment_status = "ready"
            row.download_status = "downloaded"
            row.availability = "available"
            row.verification_status = "installed_unverified"
            row.notes = "Native Diffusers path ready (weights + env-image present)."
        elif (settings.model_dir / "sdxl-base-1.0").exists():
            row.download_status = "downloaded"
            row.environment_status = "partial"
            row.availability = "unavailable"
            row.verification_status = "unverified"
            row.notes = "; ".join(sdxl_env.get("issues") or [])
        else:
            row.download_status = "not_downloaded"
            row.environment_status = "not_installed"
            row.availability = "unavailable"
        report["sdxl-base-1.0"] = {
            "availability": row.availability,
            "env": sdxl_env,
        }

    comfy = ComfyUIAdapter(
        settings.comfyui_url,
        settings.comfyui_timeout_seconds,
        default_checkpoint=settings.comfyui_checkpoint,
        comfy_output_dir=settings.comfyui_output_dir,
    )
    comfy_health = comfy.health_check()
    for model_id in ("sdxl-comfyui", "comfyui-bridge"):
        crow = db.get(ModelRecord, model_id)
        if crow is None:
            continue
        if comfy_health.get("ok") and (
            comfy_health.get("checkpoint_present") in (True, None)
        ):
            # None means checkpoint list unavailable; still mark connection_only available
            crow.environment_status = "ready" if comfy_health.get("checkpoint_present") else "connected"
            crow.availability = (
                "available" if comfy_health.get("checkpoint_present") else "available_conditional"
            )
            crow.verification_status = "installed_unverified"
            crow.notes = str(comfy_health.get("message"))
        elif comfy_health.get("ok"):
            crow.environment_status = "connected_missing_checkpoint"
            crow.availability = "unavailable"
            crow.verification_status = "unverified"
            crow.notes = (
                f"ComfyUI up but checkpoint '{settings.comfyui_checkpoint}' not listed. "
                f"Known: {comfy_health.get('checkpoints')}"
            )
        else:
            crow.environment_status = "not_running"
            crow.availability = "unavailable"
            crow.verification_status = "unverified"
            crow.notes = str(comfy_health.get("message"))
        report[model_id] = {
            "availability": crow.availability,
            "health": comfy_health,
        }

    mock = db.get(ModelRecord, "mock-demo")
    if mock is not None:
        mock.availability = "available_simulation"
        mock.environment_status = "ready"
        mock.verification_status = "simulated"

    db.commit()
    return report


def install_hints(settings: Settings) -> dict[str, Any]:
    root = settings.install_root or Path("D:/avs")
    return {
        "install_root_hint": str(root),
        "scripts": {
            "phase2": "scripts/windows/install-phase2.ps1",
            "comfyui": "scripts/windows/install-comfyui.ps1",
            "sdxl": "scripts/windows/install-sdxl.ps1",
        },
        "allow_model_download": settings.allow_model_download,
        "run_mode": settings.run_mode,
        "skip_hardware_verification": settings.skip_hardware_verification,
    }
