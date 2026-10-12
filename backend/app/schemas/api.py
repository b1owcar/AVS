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
        "available_simulation",
        "entry_only",
        "unimplemented",
        "unavailable",
    ]
    notes: str


class StudioCatalog(BaseModel):
    features: list[FeatureEntry]
