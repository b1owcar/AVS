from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    # backend/app/core/config.py -> repo root
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAVS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Local AI Vision Studio"
    app_version: str = "0.1.0"
    run_mode: Literal["simulation", "real"] = "simulation"

    host: str = "127.0.0.1"
    port: int = 18765

    data_dir: Path = Field(default=Path("./data"))
    model_dir: Path = Field(default=Path("./data/models"))
    output_dir: Path = Field(default=Path("./data/outputs"))
    upload_dir: Path = Field(default=Path("./data/uploads"))
    log_dir: Path = Field(default=Path("./data/logs"))
    db_path: Path = Field(default=Path("./data/db/lavs.sqlite3"))

    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_timeout_seconds: float = 5.0

    gpu_memory_reserve_mb: int = 512
    max_concurrent_gpu_tasks: int = 1

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
            "http://127.0.0.1:18766",
            "http://localhost:18766",
        ]
    )

    @field_validator(
        "data_dir",
        "model_dir",
        "output_dir",
        "upload_dir",
        "log_dir",
        "db_path",
        mode="before",
    )
    @classmethod
    def _coerce_path(cls, value: object) -> Path:
        return Path(str(value))

    def resolve_paths(self) -> "Settings":
        root = _project_root()

        def resolve(p: Path) -> Path:
            return p if p.is_absolute() else (root / p).resolve()

        self.data_dir = resolve(self.data_dir)
        self.model_dir = resolve(self.model_dir)
        self.output_dir = resolve(self.output_dir)
        self.upload_dir = resolve(self.upload_dir)
        self.log_dir = resolve(self.log_dir)
        self.db_path = resolve(self.db_path)
        return self

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.model_dir,
            self.output_dir,
            self.upload_dir,
            self.log_dir,
            self.db_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def is_simulation(self) -> bool:
        return self.run_mode == "simulation"

    @property
    def remote_bind_warning(self) -> str | None:
        if self.host in {"0.0.0.0", "::", "[::]"}:
            return (
                "Server is bound beyond localhost. This exposes the local AI "
                "workstation on the network. Use only on a trusted LAN and "
                "consider authentication before remote access."
            )
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings().resolve_paths()
