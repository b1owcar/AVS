from __future__ import annotations

from fastapi import APIRouter

from app.adapters.comfyui_adapter import ComfyUIAdapter
from app.api.deps import SettingsDep
from app.core.hardware import collect_system_info
from app.schemas.api import FeatureEntry, StudioCatalog

router = APIRouter(tags=["system"])


@router.get("/health")
def health(settings: SettingsDep) -> dict:
    return {
        "ok": True,
        "app": settings.app_name,
        "version": settings.app_version,
        "run_mode": settings.run_mode,
        "remote_bind_warning": settings.remote_bind_warning,
    }


@router.get("/system/info")
def system_info(settings: SettingsDep) -> dict:
    info = collect_system_info(settings.run_mode, str(settings.data_dir))
    payload = info.to_dict()
    payload["app"] = {
        "name": settings.app_name,
        "version": settings.app_version,
        "host": settings.host,
        "port": settings.port,
        "comfyui_url": settings.comfyui_url,
        "max_concurrent_gpu_tasks": settings.max_concurrent_gpu_tasks,
        "gpu_memory_reserve_mb": settings.gpu_memory_reserve_mb,
        "remote_bind_warning": settings.remote_bind_warning,
    }
    payload["disclaimer"] = (
        "This probe reflects the CURRENT development machine, not the target RTX 5070 Ti laptop "
        "until deployment-day hardware tests are run."
    )
    return payload


@router.get("/features", response_model=StudioCatalog)
def features() -> StudioCatalog:
    return StudioCatalog(
        features=[
            FeatureEntry(
                id="dashboard",
                label="Dashboard",
                status="available",
                notes="System overview and status",
            ),
            FeatureEntry(
                id="image_studio",
                label="Image Studio",
                status="available_simulation",
                notes="Mock always available. SDXL native / ComfyUI become available after install-phase2.ps1.",
            ),
            FeatureEntry(
                id="video_studio",
                label="Video Studio",
                status="entry_only",
                notes="UI entry only. Wan / ComfyUI not verified.",
            ),
            FeatureEntry(
                id="motion_studio",
                label="Motion Studio",
                status="entry_only",
                notes="Pose / motion transfer not implemented.",
            ),
            FeatureEntry(
                id="studio_3d",
                label="3D Studio",
                status="entry_only",
                notes="TRELLIS experimental; unavailable until isolated env verified.",
            ),
            FeatureEntry(
                id="model_manager",
                label="Model Manager",
                status="available",
                notes="Registry + download metadata; no auto download.",
            ),
            FeatureEntry(
                id="task_queue",
                label="Task Queue",
                status="available",
                notes="Persisted queue with simulation/real separation.",
            ),
            FeatureEntry(
                id="asset_library",
                label="Asset Library",
                status="available",
                notes="Upload / list / delete with path safety.",
            ),
            FeatureEntry(
                id="settings",
                label="Settings",
                status="available",
                notes="Read-only view of effective config in Phase 1.",
            ),
        ]
    )


@router.get("/comfyui/status")
def comfyui_status(settings: SettingsDep) -> dict:
    adapter = ComfyUIAdapter(settings.comfyui_url, settings.comfyui_timeout_seconds)
    return adapter.health_check()
