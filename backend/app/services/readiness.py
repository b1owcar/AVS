from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.comfyui_adapter import ComfyUIAdapter
from app.adapters.motion_adapter import MotionTransferAdapter, SkeletonComposePreviewAdapter
from app.adapters.pose_adapter import PoseMediapipeAdapter
from app.adapters.sdxl_adapter import SdxlNativeAdapter
from app.adapters.trellis_adapter import TrellisImageTo3DAdapter, VideoTo3DKeyframeAdapter
from app.adapters.wan_comfy_adapter import WanI2VAdapter, WanT2VAdapter
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
            mode = sdxl_env.get("mode") or "subprocess"
            row.notes = f"Native Diffusers path ready (mode={mode})."
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

    # Wan T2V / I2V — ready when ComfyUI is reachable (weights verified at workflow runtime)
    for wan_cls in (WanT2VAdapter, WanI2VAdapter):
        wan = wan_cls(settings)
        wan_env = wan.validate_environment()
        wrow = db.get(ModelRecord, wan.model_id)
        if wrow is None:
            continue
        if wan_env.get("ok"):
            wrow.environment_status = "ready"
            wrow.availability = "available_conditional"
            wrow.verification_status = "installed_unverified"
            wrow.notes = (
                f"ComfyUI reachable; workflow={wan.workflow_file}. "
                "Weights must exist in ComfyUI model folders."
            )
        else:
            wrow.environment_status = "not_running"
            wrow.availability = "unavailable"
            wrow.verification_status = "unverified"
            wrow.notes = str(wan_env.get("message"))
        report[wan.model_id] = {"availability": wrow.availability, "env": wan_env}

    pose = PoseMediapipeAdapter(settings)
    pose_env = pose.validate_environment()
    prow = db.get(ModelRecord, "pose-mediapipe")
    if prow is not None:
        if pose_env.get("ok"):
            prow.environment_status = "ready"
            prow.availability = "available"
            prow.verification_status = "installed_unverified"
            prow.notes = "env-pose MediaPipe worker ready (Phase 5 stage-1)."
        else:
            prow.environment_status = "not_installed"
            prow.availability = "unavailable"
            prow.verification_status = "unverified"
            prow.notes = "; ".join(pose_env.get("issues") or [])
        report["pose-mediapipe"] = {"availability": prow.availability, "env": pose_env}

    motion = MotionTransferAdapter(settings).validate_environment()
    mrow = db.get(ModelRecord, "motion-transfer")
    if mrow is not None:
        if motion.get("ok"):
            mrow.environment_status = "ready"
            mrow.availability = "available"
            mrow.verification_status = "installed_unverified"
            mrow.notes = "env-motion + weights present."
        else:
            mrow.environment_status = "not_installed"
            mrow.availability = "unavailable"
            mrow.verification_status = "unverified"
            mrow.notes = "; ".join(motion.get("issues") or [])
        report["motion-transfer"] = {"availability": mrow.availability, "env": motion}

    compose = SkeletonComposePreviewAdapter(settings).validate_environment()
    crow = db.get(ModelRecord, "skeleton-compose-preview")
    if crow is not None:
        crow.environment_status = "ready"
        crow.availability = "available"
        crow.verification_status = "logic_only"
        crow.notes = "Preview helper only — NOT motion transfer."
        report["skeleton-compose-preview"] = {"availability": crow.availability, "env": compose}

    trellis = TrellisImageTo3DAdapter(settings).validate_environment()
    trow = db.get(ModelRecord, "trellis-image-to-3d")
    if trow is not None:
        if trellis.get("ok"):
            trow.environment_status = "ready"
            trow.availability = "available_conditional"
            trow.verification_status = "installed_unverified"
            trow.notes = "env-trellis python set; still requires trellis_runner + sufficient VRAM."
        else:
            trow.environment_status = "not_installed"
            trow.availability = "unavailable"
            trow.verification_status = "unverified"
            trow.notes = "; ".join(trellis.get("issues") or [])
        report["trellis-image-to-3d"] = {"availability": trow.availability, "env": trellis}

    v3d = VideoTo3DKeyframeAdapter(settings).validate_environment()
    vrow = db.get(ModelRecord, "video-to-3d-keyframe")
    if vrow is not None:
        if v3d.get("ok"):
            vrow.environment_status = "ready"
            vrow.availability = "available"
            vrow.verification_status = "logic_only"
            vrow.notes = "FFmpeg keyframe approx ready — not full geometry recovery."
        else:
            vrow.environment_status = "not_installed"
            vrow.availability = "unavailable"
            vrow.notes = str(v3d.get("message"))
        report["video-to-3d-keyframe"] = {"availability": vrow.availability, "env": v3d}

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
            "pose": "scripts/windows/install-pose.ps1",
            "motion": "scripts/windows/install-motion.ps1",
            "trellis_win": "scripts/windows/install-trellis.ps1",
            "trellis_linux": "scripts/linux/install-trellis.sh",
            "linux_smoke": "scripts/linux/smoke.sh",
            "start_comfyui": "scripts/windows/start_comfyui.ps1",
            "start_sdxl_worker": "scripts/windows/start_sdxl_worker.ps1",
        },
        "allow_model_download": settings.allow_model_download,
        "run_mode": settings.run_mode,
        "skip_hardware_verification": settings.skip_hardware_verification,
    }
