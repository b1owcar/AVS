from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, QueueDep, SettingsDep
from app.db.models import AssetRecord
from app.schemas.tasks import MotionTransferParams, PoseExtractParams

router = APIRouter(tags=["motion"])


def _asset_path(db: Session, asset_id: str) -> Path:
    row = db.get(AssetRecord, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return Path(row.file_path)


@router.get("/motion/status")
def motion_status(settings: SettingsDep) -> dict:
    from app.adapters.pose_adapter import PoseMediapipeAdapter

    pose = PoseMediapipeAdapter(settings)
    env = pose.validate_environment()
    return {
        "stage": 1,
        "pose_extract": {
            "ready": bool(env.get("ok")),
            "model_id": "pose-mediapipe",
            "env": env,
        },
        "motion_transfer": {
            "ready": False,
            "notes": "Stage 2 — transfer models not wired yet. Pose extract ≠ motion transfer.",
        },
        "workflow": [
            "Import / preprocess reference video (Video Studio)",
            "Select extracted frames",
            "Optional person_id (MediaPipe Pose is single-person)",
            "Run pose_extract → pose JSON + skeleton preview",
            "Stage 2: motion transfer (not available)",
        ],
    }


@router.post("/motion/pose/validate")
def validate_pose(body: PoseExtractParams) -> dict:
    return {
        "ok": True,
        "validated": body.model_dump(),
        "execution": "not_started",
        "message": "Pose params valid. Stage 1 extract ≠ full motion transfer.",
    }


@router.post("/motion/pose/extract")
def extract_pose(
    body: PoseExtractParams,
    db: DbDep,
    queue: QueueDep,
    settings: SettingsDep,
) -> dict:
    """Enqueue Phase 5 stage-1 pose extract. Requires frame image assets (not raw video)."""
    ref = _asset_path(db, body.reference_video_asset_id)
    # Accept either a single image asset or a JSON list of frame paths stored as asset metadata
    frame_paths: list[str] = []
    suffix = ref.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        frame_paths = [str(ref)]
    elif suffix == ".json":
        data = json.loads(ref.read_text(encoding="utf-8"))
        if isinstance(data, list):
            frame_paths = [str(p) for p in data]
        elif isinstance(data, dict) and "frames" in data:
            frame_paths = [str(p) for p in data["frames"]]
        else:
            raise HTTPException(status_code=400, detail="JSON asset must list frames")
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "pose_extract expects image frame asset(s), not raw video. "
                "Use Video Studio preprocess (interval/keyframes) first, then pass a frame asset_id."
            ),
        )

    # Optional: extra frame asset ids in notes is not used; support multi via parameters later
    parameters = {
        "frame_paths": frame_paths,
        "person_id": body.person_id,
        "export_skeleton_preview": body.export_skeleton_preview,
        "coordinate_system": body.coordinate_system,
        "reference_video_asset_id": body.reference_video_asset_id,
    }
    task = queue.create_task(
        db,
        task_type="pose_extract",
        model_id=body.model_id if body.model_id else "pose-mediapipe",
        parameters=parameters,
        input_files=frame_paths,
    )
    return queue.serialize(task)


@router.post("/motion/pose/extract-frames")
def extract_pose_multi(
    body: dict,
    db: DbDep,
    queue: QueueDep,
) -> dict:
    """Enqueue pose extract for an explicit list of frame asset ids."""
    asset_ids = body.get("frame_asset_ids") or []
    if not asset_ids:
        raise HTTPException(status_code=400, detail="frame_asset_ids required")
    frame_paths: list[str] = []
    for aid in asset_ids:
        frame_paths.append(str(_asset_path(db, str(aid))))
    person_id = body.get("person_id")
    parameters = {
        "frame_paths": frame_paths,
        "person_id": person_id,
        "export_skeleton_preview": bool(body.get("export_skeleton_preview", True)),
        "coordinate_system": body.get("coordinate_system") or "image_pixel",
    }
    task = queue.create_task(
        db,
        task_type="pose_extract",
        model_id=str(body.get("model_id") or "pose-mediapipe"),
        parameters=parameters,
        input_files=frame_paths,
    )
    return queue.serialize(task)


@router.post("/motion/transfer/validate")
def validate_transfer(body: MotionTransferParams) -> dict:
    return {
        "ok": True,
        "validated": body.model_dump(),
        "execution": "not_started",
        "message": "Stage 2 motion transfer not wired — validation only.",
    }
