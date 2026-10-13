from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ImageGenParams(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = Field(default=768, ge=64, le=2048)
    height: int = Field(default=768, ge=64, le=2048)
    num_inference_steps: int = Field(default=25, ge=1, le=80)
    guidance_scale: float = Field(default=7.0, ge=0.0, le=30.0)
    seed: int | None = None
    init_image_asset_id: str | None = None
    strength: float | None = Field(default=None, ge=0.0, le=1.0)
    mask_asset_id: str | None = None


class VideoGenParams(BaseModel):
    """Text-to-video / image-to-video — separate schemas, not interchangeable."""

    task_kind: Literal["text_to_video", "image_to_video"]
    prompt: str = ""
    negative_prompt: str = ""
    model_id: str = "wan2.1-t2v-1.3b"
    # Conservative defaults for first local tests
    width: int = Field(default=480, ge=64, le=1280)
    height: int = Field(default=480, ge=64, le=1280)
    num_frames: int = Field(default=33, ge=1, le=121)
    fps: int = Field(default=16, ge=1, le=60)
    seed: int | None = None
    reference_image_asset_id: str | None = None
    notes: str = "Real Wan models not loaded until ComfyUI workflow verified on office PC."


class VideoPreprocessParams(BaseModel):
    asset_id: str | None = None
    source_path: str | None = None
    mode: Literal["info", "keyframes", "interval", "clip", "transcode", "preview"] = "info"
    interval_seconds: float = Field(default=1.0, gt=0)
    start_seconds: float = Field(default=0.0, ge=0)
    duration_seconds: float | None = Field(default=None, gt=0)
    max_frames: int = Field(default=60, ge=1, le=500)
    output_format: str = "mp4"


class PoseExtractParams(BaseModel):
    reference_video_asset_id: str
    person_id: int | None = None
    model_id: str = "dwpose"
    export_skeleton_preview: bool = True
    coordinate_system: Literal["image_pixel", "normalized"] = "image_pixel"
    notes: str = "Pose extract ≠ full motion transfer. Stage 1 framework only."


class MotionTransferParams(BaseModel):
    reference_video_asset_id: str
    target_type: Literal["person_image", "person_video", "mesh_3d", "pre_rendered"]
    target_asset_id: str
    selected_person_id: int | None = None
    model_id: str | None = None
    notes: str = "Stage 2 — real transfer models not wired yet."


class ImageTo3DParams(BaseModel):
    image_asset_id: str
    model_id: str = "trellis-image-to-3d"
    output_formats: list[str] = Field(default_factory=lambda: ["glb"])
    notes: str = "TRELLIS requires isolated env; experimental."


class VideoTo3DParams(BaseModel):
    video_asset_id: str
    mode: Literal["keyframe_approx", "multiview_rebuild"] = "keyframe_approx"
    notes: str = (
        "Video-to-3D is not the same as image-to-3D. "
        "keyframe_approx must not claim full geometry recovery."
    )


class TaskParameterCatalog(BaseModel):
    image_gen: dict[str, Any]
    video_gen: dict[str, Any]
    video_preprocess: dict[str, Any]
    pose_extract: dict[str, Any]
    motion_transfer: dict[str, Any]
    image_to_3d: dict[str, Any]
    video_to_3d: dict[str, Any]
