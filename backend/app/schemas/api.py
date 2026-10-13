from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    task_type: str = Field(..., examples=["text_to_image"])
    model_id: str = Field(..., examples=["mock-demo"])
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_files: list[str] = Field(default_factory=list)


class FeatureEntry(BaseModel):
    id: str
    label: str
    status: Literal[
        "available",
        "available_conditional",
        "available_simulation",
        "entry_only",
        "unimplemented",
        "unavailable",
    ]
    notes: str


class FeatureSummary(BaseModel):
    run_mode: str
    ready_count: int
    blocked_count: int
    comfyui: Literal["reachable", "offline"]
    comfyui_message: str = ""
    sdxl_native: Literal["ready", "not_ready"] = "not_ready"
    ffmpeg: Literal["available", "missing"] = "missing"
    next_steps: list[str] = Field(default_factory=list)


class StudioCatalog(BaseModel):
    features: list[FeatureEntry]
    summary: FeatureSummary | None = None
