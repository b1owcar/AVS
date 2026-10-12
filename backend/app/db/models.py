from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelRecord(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256))
    version: Mapped[str] = mapped_column(String(64), default="unknown")
    provider: Mapped[str] = mapped_column(String(128), default="unknown")
    supported_tasks_json: Mapped[str] = mapped_column(Text, default="[]")
    supported_platforms_json: Mapped[str] = mapped_column(Text, default="[]")
    dependency_requirements_json: Mapped[str] = mapped_column(Text, default="{}")
    checkpoint_paths_json: Mapped[str] = mapped_column(Text, default="[]")
    model_license: Mapped[str] = mapped_column(String(256), default="unknown")
    hardware_requirements_json: Mapped[str] = mapped_column(Text, default="{}")
    estimated_vram_json: Mapped[str] = mapped_column(Text, default="{}")
    estimated_ram_json: Mapped[str] = mapped_column(Text, default="{}")
    precision_options_json: Mapped[str] = mapped_column(Text, default="[]")
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_size_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    environment_status: Mapped[str] = mapped_column(String(64), default="not_installed")
    download_status: Mapped[str] = mapped_column(String(64), default="not_downloaded")
    verification_status: Mapped[str] = mapped_column(String(64), default="unverified")
    availability: Mapped[str] = mapped_column(String(64), default="unavailable")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    model_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    input_files_json: Mapped[str] = mapped_column(Text, default="[]")
    output_files_json: Mapped[str] = mapped_column(Text, default="[]")
    logs: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssetRecord(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_path: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    source_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    is_original_input: Mapped[bool] = mapped_column(Boolean, default=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
