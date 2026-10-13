from __future__ import annotations

from fastapi import APIRouter

from app.adapters.comfyui_adapter import ComfyUIAdapter
from app.api.deps import SettingsDep
from app.core.hardware import collect_system_info
from app.schemas.api import StudioCatalog
from app.services.feature_catalog import build_feature_catalog

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
def features(settings: SettingsDep) -> StudioCatalog:
    return build_feature_catalog(settings)


@router.get("/comfyui/status")
def comfyui_status(settings: SettingsDep) -> dict:
    adapter = ComfyUIAdapter(settings.comfyui_url, settings.comfyui_timeout_seconds)
    return adapter.health_check()
