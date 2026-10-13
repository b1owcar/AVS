from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, QueueDep, SettingsDep
from app.db.models import AssetRecord
from app.schemas.tasks import (
    ImageTo3DParams,
    MotionTransferParams,
    PoseExtractParams,
    TaskParameterCatalog,
    VideoGenParams,
    VideoPreprocessParams,
    VideoTo3DParams,
    ImageGenParams,
)
from app.services.path_safety import UnsafePathError
from app.services.video_preprocess import VideoPreprocessError, VideoPreprocessService

router = APIRouter(tags=["video"])


def _video_service(settings) -> VideoPreprocessService:
    return VideoPreprocessService(upload_dir=settings.upload_dir, output_dir=settings.output_dir)


def _resolve_asset_path(db: Session, asset_id: str | None, source_path: str | None) -> Path:
    if asset_id:
        row = db.get(AssetRecord, asset_id)
        if row is None:
            raise HTTPException(status_code=404, detail="asset not found")
        return Path(row.file_path)
    if source_path:
        return Path(source_path)
    raise HTTPException(status_code=400, detail="asset_id or source_path required")


def _register_outputs(db: Session, paths: list[str], source_task: str) -> list[dict]:
    registered = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        asset = AssetRecord(
            id=str(uuid.uuid4()),
            file_path=str(path),
            file_type=path.suffix.lstrip(".") or "bin",
            file_size=path.stat().st_size,
            source_task_id=source_task,
            metadata_json=json.dumps({"preprocess": True}),
            is_original_input=False,
            is_generated=True,
        )
        db.add(asset)
        registered.append({"asset_id": asset.id, "file_path": asset.file_path})
    db.commit()
    return registered


@router.get("/video/status")
def video_status(settings: SettingsDep) -> dict:
    from app.adapters.wan_comfy_adapter import WanI2VAdapter, WanT2VAdapter

    svc = _video_service(settings)
    t2v = WanT2VAdapter(settings).validate_environment()
    i2v = WanI2VAdapter(settings).validate_environment()
    return {
        "ffmpeg_available": svc.available(),
        "upload_dir": str(settings.upload_dir),
        "output_dir": str(settings.output_dir),
        "features": {
            "info": svc.available(),
            "interval_frames": svc.available(),
            "keyframes": svc.available(),
            "clip": svc.available(),
            "transcode": svc.available(),
            "preview": svc.available(),
            "text_to_video": bool(t2v.get("ok")),
            "image_to_video": bool(i2v.get("ok")),
        },
        "wan": {
            "t2v": t2v,
            "i2v": i2v,
        },
        "notes": (
            "Preprocess uses FFmpeg (no GPU). "
            "T2V/I2V run via ComfyUI Wan workflows when ComfyUI is up and weights installed."
        ),
    }


@router.get("/task-schemas", response_model=TaskParameterCatalog)
def task_schemas() -> TaskParameterCatalog:
    return TaskParameterCatalog(
        image_gen=ImageGenParams.model_json_schema(),
        video_gen=VideoGenParams.model_json_schema(),
        video_preprocess=VideoPreprocessParams.model_json_schema(),
        pose_extract=PoseExtractParams.model_json_schema(),
        motion_transfer=MotionTransferParams.model_json_schema(),
        image_to_3d=ImageTo3DParams.model_json_schema(),
        video_to_3d=VideoTo3DParams.model_json_schema(),
    )


@router.post("/video/preprocess")
def preprocess(body: VideoPreprocessParams, db: DbDep, settings: SettingsDep) -> dict:
    svc = _video_service(settings)
    if not svc.available():
        raise HTTPException(status_code=503, detail="FFmpeg not available")
    try:
        source = svc.resolve_source(_resolve_asset_path(db, body.asset_id, body.source_path))
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = uuid.uuid4().hex[:12]
    try:
        if body.mode == "info":
            info = svc.probe(source)
            return {"ok": True, "mode": "info", "job_id": job_id, "result": info}

        if body.mode == "interval":
            result = svc.extract_interval_frames(
                source,
                interval_seconds=body.interval_seconds,
                max_frames=body.max_frames,
                job_id=job_id,
            )
            result["assets"] = _register_outputs(db, result.get("frames", []), f"preprocess:{job_id}")
            return {"ok": True, "mode": "interval", "result": result}

        if body.mode == "keyframes":
            result = svc.extract_keyframes(source, max_frames=body.max_frames, job_id=job_id)
            result["assets"] = _register_outputs(db, result.get("frames", []), f"preprocess:{job_id}")
            return {"ok": True, "mode": "keyframes", "result": result}

        if body.mode == "clip":
            if body.duration_seconds is None:
                raise HTTPException(status_code=400, detail="duration_seconds required for clip")
            result = svc.clip(
                source,
                start_seconds=body.start_seconds,
                duration_seconds=body.duration_seconds,
                job_id=job_id,
            )
            result["assets"] = _register_outputs(
                db, [result["output_file"]], f"preprocess:{job_id}"
            )
            return {"ok": True, "mode": "clip", "result": result}

        if body.mode == "transcode":
            result = svc.transcode(source, output_format=body.output_format, job_id=job_id)
            result["assets"] = _register_outputs(
                db, [result["output_file"]], f"preprocess:{job_id}"
            )
            return {"ok": True, "mode": "transcode", "result": result}

        if body.mode == "preview":
            result = svc.preview_image(source, at_seconds=max(body.start_seconds, 0.1), job_id=job_id)
            result["assets"] = _register_outputs(
                db, [result["output_file"]], f"preprocess:{job_id}"
            )
            return {"ok": True, "mode": "preview", "result": result}

        raise HTTPException(status_code=400, detail=f"unsupported mode: {body.mode}")
    except VideoPreprocessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/video/generate/validate")
def validate_video_gen(body: VideoGenParams) -> dict:
    """Validate T2V/I2V params without running a model."""
    if body.task_kind == "image_to_video" and not body.reference_image_asset_id:
        raise HTTPException(
            status_code=400,
            detail="image_to_video requires reference_image_asset_id (separate from T2V)",
        )
    if body.task_kind == "text_to_video" and not body.prompt.strip():
        raise HTTPException(status_code=400, detail="text_to_video requires prompt")
    expected_model = (
        "wan2.1-i2v" if body.task_kind == "image_to_video" else "wan2.1-t2v-1.3b"
    )
    return {
        "ok": True,
        "validated": body.model_dump(),
        "expected_model_id": expected_model,
        "execution": "not_started",
        "message": "Parameters valid. Submit via POST /api/video/generate to enqueue.",
    }


@router.post("/video/generate")
def generate_video(body: VideoGenParams, db: DbDep, queue: QueueDep) -> dict:
    """Enqueue Wan T2V or I2V via ComfyUI adapters (separate schemas)."""
    if body.task_kind == "image_to_video":
        if not body.reference_image_asset_id:
            raise HTTPException(
                status_code=400,
                detail="image_to_video requires reference_image_asset_id",
            )
        model_id = "wan2.1-i2v"
        if body.model_id and body.model_id not in {"wan2.1-t2v-1.3b", "wan2.1-i2v"}:
            model_id = body.model_id
        img_row = db.get(AssetRecord, body.reference_image_asset_id)
        if img_row is None:
            raise HTTPException(status_code=404, detail="reference image asset not found")
        parameters = {
            "prompt": body.prompt,
            "negative_prompt": body.negative_prompt,
            "width": body.width,
            "height": body.height,
            "num_frames": body.num_frames,
            "fps": body.fps,
            "seed": body.seed,
            "input_image_path": img_row.file_path,
            "reference_image_path": img_row.file_path,
        }
        task = queue.create_task(
            db,
            task_type="image_to_video",
            model_id=model_id,
            parameters=parameters,
            input_files=[img_row.file_path],
        )
        return queue.serialize(task)

    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="text_to_video requires prompt")
    model_id = body.model_id or "wan2.1-t2v-1.3b"
    if model_id == "wan2.1-i2v":
        raise HTTPException(
            status_code=400,
            detail="wan2.1-i2v is image_to_video only; use task_kind=image_to_video",
        )
    parameters = {
        "prompt": body.prompt,
        "negative_prompt": body.negative_prompt,
        "width": body.width,
        "height": body.height,
        "num_frames": body.num_frames,
        "fps": body.fps,
        "seed": body.seed,
    }
    task = queue.create_task(
        db,
        task_type="text_to_video",
        model_id=model_id,
        parameters=parameters,
    )
    return queue.serialize(task)
