from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, QueueDep, SettingsDep
from app.db.models import AssetRecord
from app.schemas.tasks import ImageTo3DParams, VideoTo3DParams

router = APIRouter(tags=["studio3d"])


def _asset_path(db: Session, asset_id: str) -> Path:
    row = db.get(AssetRecord, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return Path(row.file_path)


@router.get("/studio3d/status")
def studio3d_status(settings: SettingsDep) -> dict:
    from app.adapters.trellis_adapter import TrellisImageTo3DAdapter, VideoTo3DKeyframeAdapter

    trellis = TrellisImageTo3DAdapter(settings).validate_environment()
    v3d = VideoTo3DKeyframeAdapter(settings).validate_environment()
    return {
        "phase": 6,
        "image_to_3d": {
            "model_id": "trellis-image-to-3d",
            "ready": bool(trellis.get("ok")),
            "env": trellis,
        },
        "video_to_3d": {
            "model_id": "video-to-3d-keyframe",
            "ready": bool(v3d.get("ok")),
            "env": v3d,
            "disclaimer": v3d.get("disclaimer"),
        },
        "notes": (
            "TRELLIS stays in env-trellis. Official Linux + >=16GB VRAM. "
            "video keyframe_approx ≠ full geometry recovery."
        ),
    }


@router.post("/studio3d/image-to-3d")
def image_to_3d(body: ImageTo3DParams, db: DbDep, queue: QueueDep) -> dict:
    path = _asset_path(db, body.image_asset_id)
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        raise HTTPException(status_code=400, detail="image_asset_id must be an image asset")
    task = queue.create_task(
        db,
        task_type="image_to_3d",
        model_id=body.model_id or "trellis-image-to-3d",
        parameters={
            "image_path": str(path),
            "output_formats": body.output_formats,
        },
        input_files=[str(path)],
    )
    return queue.serialize(task)


@router.post("/studio3d/video-to-3d")
def video_to_3d(body: VideoTo3DParams, db: DbDep, queue: QueueDep) -> dict:
    if body.mode == "multiview_rebuild":
        raise HTTPException(
            status_code=400,
            detail="multiview_rebuild not implemented — use keyframe_approx (not full geometry)",
        )
    path = _asset_path(db, body.video_asset_id)
    # Extra flags via notes field not available; accept defaults
    task = queue.create_task(
        db,
        task_type="video_to_3d",
        model_id="video-to-3d-keyframe",
        parameters={
            "video_path": str(path),
            "mode": body.mode,
            "max_frames": 8,
            "run_trellis_on_first": False,
        },
        input_files=[str(path)],
    )
    return queue.serialize(task)


@router.post("/studio3d/video-to-3d/validate")
def validate_video_to_3d(body: VideoTo3DParams) -> dict:
    if body.mode == "multiview_rebuild":
        raise HTTPException(
            status_code=400,
            detail="multiview_rebuild not implemented",
        )
    return {
        "ok": True,
        "validated": body.model_dump(),
        "message": "keyframe_approx only — not full geometry recovery.",
    }
