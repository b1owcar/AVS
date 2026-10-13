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
    from app.adapters.motion_adapter import MotionTransferAdapter, SkeletonComposePreviewAdapter
    from app.adapters.pose_adapter import PoseMediapipeAdapter

    pose = PoseMediapipeAdapter(settings).validate_environment()
    transfer = MotionTransferAdapter(settings).validate_environment()
    compose = SkeletonComposePreviewAdapter(settings).validate_environment()
    return {
        "stage": 2,
        "pose_extract": {
            "ready": bool(pose.get("ok")),
            "model_id": "pose-mediapipe",
            "env": pose,
        },
        "motion_transfer": {
            "ready": bool(transfer.get("ok")),
            "model_id": "motion-transfer",
            "env": transfer,
            "notes": "Stage 2 real transfer — pose extract ≠ motion transfer.",
        },
        "skeleton_compose_preview": {
            "ready": bool(compose.get("ok")),
            "model_id": "skeleton-compose-preview",
            "notes": "Utility overlay only — NOT motion transfer inference.",
        },
        "workflow": [
            "Import / preprocess reference video (Video Studio)",
            "Select extracted frames",
            "Optional person_id (MediaPipe Pose is single-person)",
            "Run pose_extract → pose JSON + skeleton preview",
            "Stage 2: motion-transfer (needs env-motion + weights) or skeleton-compose-preview helper",
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
) -> dict:
    """Enqueue Phase 5 stage-1 pose extract. Requires frame image assets (not raw video)."""
    ref = _asset_path(db, body.reference_video_asset_id)
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
        "message": (
            "Params valid. Real transfer needs env-motion + weights. "
            "skeleton-compose-preview is a separate helper and is not transfer."
        ),
    }


@router.post("/motion/transfer")
def run_transfer(body: MotionTransferParams, db: DbDep, queue: QueueDep) -> dict:
    if body.target_type != "person_image":
        raise HTTPException(
            status_code=400,
            detail="stage-2 currently supports target_type=person_image only",
        )
    # Pose JSON asset: expect a generated .json from pose extract
    pose_path = _asset_path(db, body.reference_video_asset_id)
    if pose_path.suffix.lower() != ".json":
        raise HTTPException(
            status_code=400,
            detail=(
                "reference_video_asset_id for transfer must be the pose JSON asset "
                "from stage-1 (file_type=json), not the raw video."
            ),
        )
    target_path = _asset_path(db, body.target_asset_id)
    model_id = body.model_id or "motion-transfer"
    task = queue.create_task(
        db,
        task_type="motion_transfer",
        model_id=model_id,
        parameters={
            "pose_json_path": str(pose_path),
            "target_image_path": str(target_path),
            "target_type": body.target_type,
            "selected_person_id": body.selected_person_id,
        },
        input_files=[str(pose_path), str(target_path)],
    )
    return queue.serialize(task)


@router.post("/motion/compose-preview")
def compose_preview(body: dict, db: DbDep, queue: QueueDep) -> dict:
    """Skeleton overlay helper — explicitly NOT motion transfer."""
    pose_id = body.get("pose_json_asset_id")
    target_id = body.get("target_image_asset_id")
    if not pose_id or not target_id:
        raise HTTPException(
            status_code=400,
            detail="pose_json_asset_id and target_image_asset_id required",
        )
    pose_path = _asset_path(db, str(pose_id))
    target_path = _asset_path(db, str(target_id))
    task = queue.create_task(
        db,
        task_type="skeleton_compose_preview",
        model_id="skeleton-compose-preview",
        parameters={
            "pose_json_path": str(pose_path),
            "target_image_path": str(target_path),
        },
        input_files=[str(pose_path), str(target_path)],
    )
    return queue.serialize(task)
