from __future__ import annotations

from typing import Any

from app.adapters.comfyui_adapter import ComfyUIAdapter
from app.adapters.motion_adapter import MotionTransferAdapter, SkeletonComposePreviewAdapter
from app.adapters.pose_adapter import PoseMediapipeAdapter
from app.adapters.sdxl_adapter import SdxlNativeAdapter
from app.adapters.trellis_adapter import TrellisImageTo3DAdapter, VideoTo3DKeyframeAdapter
from app.adapters.wan_comfy_adapter import WanI2VAdapter, WanT2VAdapter
from app.core.config import Settings
from app.schemas.api import FeatureEntry, FeatureSummary, StudioCatalog


def _issue_text(env: dict[str, Any], fallback: str) -> str:
    issues = env.get("issues")
    if isinstance(issues, list) and issues:
        return "; ".join(str(x) for x in issues)
    msg = env.get("message")
    if msg:
        return str(msg)
    return fallback


def build_feature_catalog(settings: Settings) -> StudioCatalog:
    """Live feature gates from adapters — not a static Phase-1 checklist."""
    comfy = ComfyUIAdapter(
        settings.comfyui_url,
        settings.comfyui_timeout_seconds,
        default_checkpoint=settings.comfyui_checkpoint,
        comfy_output_dir=settings.comfyui_output_dir,
    ).health_check()
    comfy_ok = bool(comfy.get("ok"))

    sdxl = SdxlNativeAdapter(settings).validate_environment()
    sdxl_ok = bool(sdxl.get("ok"))
    t2v = WanT2VAdapter(settings).validate_environment()
    i2v = WanI2VAdapter(settings).validate_environment()
    wan_ok = bool(t2v.get("ok") or i2v.get("ok"))

    pose = PoseMediapipeAdapter(settings).validate_environment()
    transfer = MotionTransferAdapter(settings).validate_environment()
    compose = SkeletonComposePreviewAdapter(settings).validate_environment()
    pose_ok = bool(pose.get("ok"))
    transfer_ok = bool(transfer.get("ok"))

    trellis = TrellisImageTo3DAdapter(settings).validate_environment()
    v3d = VideoTo3DKeyframeAdapter(settings).validate_environment()
    trellis_ok = bool(trellis.get("ok"))
    v3d_ok = bool(v3d.get("ok"))

    # FFmpeg via simple shutil which video service uses — avoid heavy import cycles
    import shutil

    ffmpeg_ok = shutil.which("ffmpeg") is not None

    features: list[FeatureEntry] = [
        FeatureEntry(
            id="dashboard",
            label="Dashboard",
            status="available",
            notes="Live probe of this machine.",
        ),
    ]

    # Image Studio
    if sdxl_ok and comfy_ok:
        features.append(
            FeatureEntry(
                id="image_studio",
                label="Image Studio",
                status="available",
                notes=f"SDXL native ({sdxl.get('mode') or 'ready'}) + ComfyUI online.",
            )
        )
    elif sdxl_ok:
        features.append(
            FeatureEntry(
                id="image_studio",
                label="Image Studio",
                status="available",
                notes=f"SDXL native ready ({sdxl.get('mode') or 'subprocess'}). ComfyUI offline.",
            )
        )
    elif comfy_ok:
        features.append(
            FeatureEntry(
                id="image_studio",
                label="Image Studio",
                status="available_conditional",
                notes="ComfyUI online — use sdxl-comfyui / bridge models. Native SDXL worker not ready.",
            )
        )
    elif settings.run_mode == "simulation":
        features.append(
            FeatureEntry(
                id="image_studio",
                label="Image Studio",
                status="available_simulation",
                notes="Demo mock only. Install SDXL or start ComfyUI for real inference.",
            )
        )
    else:
        features.append(
            FeatureEntry(
                id="image_studio",
                label="Image Studio",
                status="unavailable",
                notes=_issue_text(sdxl, "SDXL and ComfyUI not ready. Run install-sdxl.ps1 / start-all.ps1."),
            )
        )

    # Video Studio
    wan_bits = []
    if t2v.get("ok"):
        wan_bits.append("T2V")
    if i2v.get("ok"):
        wan_bits.append("I2V")
    if ffmpeg_ok and wan_ok:
        features.append(
            FeatureEntry(
                id="video_studio",
                label="Video Studio",
                status="available_conditional",
                notes=f"FFmpeg OK; Wan {'/'.join(wan_bits)} via ComfyUI (weights checked at run time).",
            )
        )
    elif ffmpeg_ok:
        features.append(
            FeatureEntry(
                id="video_studio",
                label="Video Studio",
                status="available",
                notes="FFmpeg preprocess ready. Wan T2V/I2V need ComfyUI + Wan weights.",
            )
        )
    elif wan_ok:
        features.append(
            FeatureEntry(
                id="video_studio",
                label="Video Studio",
                status="available_conditional",
                notes="ComfyUI Wan path up; install FFmpeg for preprocess tools.",
            )
        )
    else:
        features.append(
            FeatureEntry(
                id="video_studio",
                label="Video Studio",
                status="unavailable",
                notes="Need FFmpeg and/or ComfyUI for video features.",
            )
        )

    # Motion Studio
    if pose_ok and transfer_ok:
        features.append(
            FeatureEntry(
                id="motion_studio",
                label="Motion Studio",
                status="available",
                notes="Pose extract + motion transfer workers ready.",
            )
        )
    elif pose_ok:
        features.append(
            FeatureEntry(
                id="motion_studio",
                label="Motion Studio",
                status="available",
                notes="Pose extract ready. Motion transfer still needs env-motion/weights.",
            )
        )
    elif bool(compose.get("ok")):
        features.append(
            FeatureEntry(
                id="motion_studio",
                label="Motion Studio",
                status="available_conditional",
                notes="Skeleton compose helper only — install pose worker for extract.",
            )
        )
    else:
        features.append(
            FeatureEntry(
                id="motion_studio",
                label="Motion Studio",
                status="unavailable",
                notes=_issue_text(pose, "Run scripts/windows/install-pose.ps1."),
            )
        )

    # 3D Studio
    if trellis_ok and v3d_ok:
        features.append(
            FeatureEntry(
                id="studio_3d",
                label="3D Studio",
                status="available_conditional",
                notes="TRELLIS env + FFmpeg keyframe approx ready (VRAM still required at run).",
            )
        )
    elif trellis_ok:
        features.append(
            FeatureEntry(
                id="studio_3d",
                label="3D Studio",
                status="available_conditional",
                notes="TRELLIS env ready; video→3D keyframe needs FFmpeg.",
            )
        )
    elif v3d_ok:
        features.append(
            FeatureEntry(
                id="studio_3d",
                label="3D Studio",
                status="available",
                notes="Keyframe approx ready. TRELLIS image→3D not installed.",
            )
        )
    else:
        features.append(
            FeatureEntry(
                id="studio_3d",
                label="3D Studio",
                status="unavailable",
                notes=_issue_text(trellis, "Run install-trellis.ps1 (or Linux install) + ensure FFmpeg."),
            )
        )

    features.extend(
        [
            FeatureEntry(
                id="model_manager",
                label="Model Manager",
                status="available",
                notes="Registry + install hints for this PC.",
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
                notes="Effective config for this process.",
            ),
        ]
    )

    ready_statuses = {"available", "available_conditional", "available_simulation"}
    ready = sum(1 for f in features if f.status in ready_statuses)
    blocked = sum(1 for f in features if f.status in {"unavailable", "unimplemented", "entry_only"})

    next_steps: list[str] = []
    if not comfy_ok:
        next_steps.append(
            "Start ComfyUI with scripts\\windows\\start-all.ps1 (browser refresh will not start it)."
        )
    if not sdxl_ok and settings.run_mode != "simulation":
        next_steps.append("For native SDXL: scripts\\windows\\install-sdxl.ps1 then start_sdxl_worker.ps1.")
    if not pose_ok:
        next_steps.append("For pose: scripts\\windows\\install-pose.ps1.")
    if not transfer_ok and pose_ok:
        next_steps.append("For motion transfer: scripts\\windows\\install-motion.ps1.")
    if not trellis_ok:
        next_steps.append("For TRELLIS: scripts\\windows\\install-trellis.ps1 (or Linux install script).")
    if not ffmpeg_ok:
        next_steps.append("Install FFmpeg and ensure it is on PATH.")
    if settings.run_mode == "simulation" and not (sdxl_ok or comfy_ok):
        next_steps.append(
            "Run mode is simulation — mock image tasks work; set LAVS_RUN_MODE=real after office install."
        )

    summary = FeatureSummary(
        run_mode=settings.run_mode,
        ready_count=ready,
        blocked_count=blocked,
        comfyui="reachable" if comfy_ok else "offline",
        comfyui_message=str(comfy.get("message") or ("online" if comfy_ok else "offline")),
        sdxl_native="ready" if sdxl_ok else "not_ready",
        ffmpeg="available" if ffmpeg_ok else "missing",
        next_steps=next_steps[:5],
    )
    return StudioCatalog(features=features, summary=summary)
