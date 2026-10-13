from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorkerSpec:
    worker_id: str
    display_name: str
    python_executable: Path | None
    entrypoint: Path | None
    env_name: str
    supported_tasks: list[str]
    isolation_notes: str


class SpecializedModelWorker(ABC):
    """Contract for models that must run in a separate Python env / subprocess.

    Used for SAM2, TRELLIS, etc. Main backend must not import their heavy deps.
    """

    spec: WorkerSpec

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class SubprocessJsonWorker(SpecializedModelWorker):
    """Generic JSON request/response worker launcher."""

    def __init__(self, spec: WorkerSpec) -> None:
        self.spec = spec

    def health_check(self) -> dict[str, Any]:
        py = self.spec.python_executable
        entry = self.spec.entrypoint
        ok = bool(py and py.exists() and entry and entry.exists())
        return {
            "ok": ok,
            "worker_id": self.spec.worker_id,
            "env_name": self.spec.env_name,
            "python": str(py) if py else None,
            "entrypoint": str(entry) if entry else None,
            "implementation_status": "available" if ok else "not_installed",
            "message": "ready" if ok else "Install isolated env before use",
            "isolation_notes": self.spec.isolation_notes,
        }

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        health = self.health_check()
        if not health.get("ok"):
            raise RuntimeError(health.get("message") or "worker not ready")
        assert self.spec.python_executable and self.spec.entrypoint
        work_dir = Path(payload.get("work_dir") or ".")
        work_dir.mkdir(parents=True, exist_ok=True)
        req = work_dir / "request.json"
        resp = work_dir / "response.json"
        req.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [
                str(self.spec.python_executable),
                str(self.spec.entrypoint),
                "--request",
                str(req),
                "--response",
                str(resp),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if not resp.exists():
            raise RuntimeError(
                f"worker produced no response (code={proc.returncode}): {proc.stderr[-800:]}"
            )
        data = json.loads(resp.read_text(encoding="utf-8"))
        if not data.get("ok", True) and data.get("error"):
            raise RuntimeError(str(data.get("error")))
        return data


class PlaceholderTrellisWorker(SubprocessJsonWorker):
    def __init__(self, python: Path | None = None, entry: Path | None = None) -> None:
        super().__init__(
            WorkerSpec(
                worker_id="trellis-image-to-3d",
                display_name="TRELLIS Image-to-3D Worker",
                python_executable=python,
                entrypoint=entry,
                env_name="env-trellis",
                supported_tasks=["image_to_3d"],
                isolation_notes="Must stay isolated; official Linux focus, >=16GB VRAM stated upstream.",
            )
        )


class PlaceholderSam2Worker(SubprocessJsonWorker):
    def __init__(self, python: Path | None = None, entry: Path | None = None) -> None:
        super().__init__(
            WorkerSpec(
                worker_id="sam2.1",
                display_name="SAM 2.1 Worker",
                python_executable=python,
                entrypoint=entry,
                env_name="env-sam2",
                supported_tasks=["video_segmentation"],
                isolation_notes="Prefer Linux/WSL; custom CUDA extension optional.",
            )
        )
