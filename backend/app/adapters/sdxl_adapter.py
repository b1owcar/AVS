from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate
from app.core.config import Settings


class SdxlNativeAdapter(ModelAdapter):
    """Native SDXL via isolated env-image Python subprocess."""

    model_id = "sdxl-base-1.0"
    display_name = "Stable Diffusion XL Base 1.0"
    version = "1.0"
    provider = "stabilityai / huggingface-diffusers"
    supported_tasks = ["text_to_image"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {
        "env": "env-image",
        "packages": ["torch", "diffusers", "transformers", "accelerate"],
    }
    checkpoint_paths: list[str] = []
    model_license = "CreativeML Open RAIL++-M (confirm on model card)"
    hardware_requirements = {"gpu": "NVIDIA CUDA preferred", "batch_size": 1}
    estimated_vram = {
        "min_mb": 6000,
        "max_mb": 12000,
        "conditions": ["fp16", "batch=1"],
        "basis": "community heuristic",
    }
    estimated_ram = {"min_mb": 8000, "max_mb": 16000}
    precision_options = ["fp16", "fp32"]
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "width": {"type": "integer", "default": 768},
            "height": {"type": "integer", "default": 768},
            "num_inference_steps": {"type": "integer", "default": 25},
            "guidance_scale": {"type": "number", "default": 7.0},
            "seed": {"type": "integer"},
        },
        "required": ["prompt"],
    }
    output_schema = {"type": "object"}
    cancellation_supported = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cancel = False

    @property
    def model_path(self) -> Path:
        return Path(self.settings.model_dir) / "sdxl-base-1.0"

    @property
    def image_python(self) -> Path | None:
        raw = self.settings.image_python
        if not raw:
            return None
        return Path(raw)

    @property
    def worker_script(self) -> Path:
        # repo_root/envs/image/worker_txt2img.py
        return Path(__file__).resolve().parents[3] / "envs" / "image" / "worker_txt2img.py"

    def validate_environment(self) -> dict[str, Any]:
        py = self.image_python
        issues: list[str] = []
        if py is None or not py.exists():
            issues.append(
                "LAVS_IMAGE_PYTHON not set or missing. Run scripts/windows/install-sdxl.ps1"
            )
        if not self.model_path.exists():
            issues.append(
                f"Weights missing at {self.model_path}. Run install-sdxl.ps1 -DownloadWeights"
            )
        if not self.worker_script.exists():
            issues.append(f"Worker script missing: {self.worker_script}")
        ok = not issues
        return {
            "ok": ok,
            "model_path": str(self.model_path),
            "image_python": str(py) if py else None,
            "worker_script": str(self.worker_script),
            "issues": issues,
            "implementation_status": "available" if ok else "not_ready",
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("prompt is required")
        width = int(payload.get("width", 768))
        height = int(payload.get("height", 768))
        if min(width, height) < 64 or max(width, height) > 2048:
            raise ValueError("width/height must be 64..2048")
        return {
            "prompt": prompt,
            "negative_prompt": str(payload.get("negative_prompt", "")),
            "width": width,
            "height": height,
            "num_inference_steps": int(payload.get("num_inference_steps", 25)),
            "guidance_scale": float(payload.get("guidance_scale", 7.0)),
            "seed": payload.get("seed"),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=6000,
            vram_mb_max=12000,
            ram_mb_min=8000,
            ram_mb_max=16000,
            conditions=["fp16 on CUDA", "batch=1"],
            basis="SDXL Diffusers heuristic",
        )

    def get_status(self) -> AdapterStatus:
        env = self.validate_environment()
        return AdapterStatus(
            model_id=self.model_id,
            loaded=False,
            healthy=bool(env.get("ok")),
            message="; ".join(env.get("issues") or ["SDXL native adapter ready"]),
            cancellation_supported=False,
            implementation_status=str(env.get("implementation_status")),
        )

    def health_check(self) -> dict[str, Any]:
        return self.validate_environment()

    def cancel(self) -> dict[str, Any]:
        return {
            "ok": False,
            "cancellation_supported": False,
            "message": "SDXL worker cancel not supported in Phase 2",
        }

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        env = self.validate_environment()
        if not env.get("ok"):
            raise RuntimeError("; ".join(env.get("issues") or ["SDXL not ready"]))

        validated = self.validate_input(payload)
        out_dir = Path(payload["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"sdxl_{uuid.uuid4().hex[:10]}.png"

        work = out_dir / "_worker"
        work.mkdir(parents=True, exist_ok=True)
        req_path = work / "request.json"
        resp_path = work / "response.json"

        request = {
            **validated,
            "model_path": str(self.model_path),
            "output_path": str(out_path),
        }
        req_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

        if progress_cb:
            progress_cb(0.05, "launching env-image SDXL worker")

        py = self.image_python
        assert py is not None
        proc = subprocess.Popen(
            [str(py), str(self.worker_script), "--request", str(req_path), "--response", str(resp_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Poll until done; report coarse progress
        while proc.poll() is None:
            if progress_cb:
                progress_cb(0.4, "sdxl worker running")
            time.sleep(1.0)

        stdout, stderr = proc.communicate(timeout=5)
        if not resp_path.exists():
            raise RuntimeError(
                f"SDXL worker produced no response (code={proc.returncode}): {stderr or stdout}"
            )
        resp = json.loads(resp_path.read_text(encoding="utf-8"))
        if not resp.get("ok"):
            raise RuntimeError(resp.get("message") or resp.get("error") or "SDXL failed")
        if progress_cb:
            progress_cb(1.0, "sdxl completed")
        return {
            "output_files": resp.get("output_files", [str(out_path)]),
            "is_simulation": False,
            "message": resp.get("message", "SDXL completed"),
            "meta": {
                "device": resp.get("device"),
                "vram_peak_mb": resp.get("vram_peak_mb"),
            },
        }
