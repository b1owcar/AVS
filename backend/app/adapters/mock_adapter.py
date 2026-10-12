from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate


class MockImageAdapter(ModelAdapter):
    """Demo / Simulation Mode adapter. Does NOT perform real AI inference."""

    model_id = "mock-demo"
    display_name = "Mock Demo Image Adapter"
    version = "0.1.0"
    provider = "local-mock"
    supported_tasks = ["text_to_image", "demo"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {"python": ">=3.10", "pillow": "required"}
    checkpoint_paths: list[str] = []
    model_license = "N/A (synthetic)"
    hardware_requirements = {"gpu": "not required for simulation"}
    estimated_vram = {"min_mb": 0, "max_mb": 0, "basis": "simulation"}
    estimated_ram = {"min_mb": 64, "max_mb": 256, "basis": "simulation"}
    precision_options = ["n/a"]
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "width": {"type": "integer", "default": 512},
            "height": {"type": "integer", "default": 512},
        },
        "required": ["prompt"],
    }
    output_schema = {"type": "object", "properties": {"output_files": {"type": "array"}}}
    cancellation_supported = True

    def __init__(self) -> None:
        self._loaded = False
        self._cancel_requested = False

    def load_model(self) -> None:
        self._loaded = True

    def unload_model(self) -> None:
        self._loaded = False

    def validate_environment(self) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": "simulation",
            "message": "Mock adapter requires only Pillow; no GPU weights.",
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("prompt is required")
        width = int(payload.get("width", 512))
        height = int(payload.get("height", 512))
        if width < 64 or height < 64 or width > 2048 or height > 2048:
            raise ValueError("width/height must be between 64 and 2048")
        return {"prompt": prompt, "width": width, "height": height}

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=0,
            vram_mb_max=0,
            ram_mb_min=64,
            ram_mb_max=256,
            conditions=["simulation only"],
            basis="mock adapter fixed estimate",
        )

    def cancel(self) -> dict[str, Any]:
        self._cancel_requested = True
        return {
            "ok": True,
            "cancellation_supported": True,
            "message": "Cancel requested for mock task",
        }

    def get_status(self) -> AdapterStatus:
        return AdapterStatus(
            model_id=self.model_id,
            loaded=self._loaded,
            healthy=True,
            message="Mock adapter ready (Demo / Simulation Mode)",
            cancellation_supported=True,
            implementation_status="simulated",
        )

    def health_check(self) -> dict[str, Any]:
        return {"ok": True, "mode": "simulation", "model_id": self.model_id}

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        self._cancel_requested = False
        validated = self.validate_input(payload)
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"mock_{int(time.time())}.png"

        steps = 5
        for i in range(steps):
            if self._cancel_requested:
                raise RuntimeError("cancelled")
            if progress_cb:
                progress_cb((i + 1) / steps, f"simulation step {i + 1}/{steps}")
            time.sleep(0.15)

        img = Image.new("RGB", (validated["width"], validated["height"]), (18, 24, 38))
        draw = ImageDraw.Draw(img)
        title = "DEMO / SIMULATION MODE"
        subtitle = "Not real AI inference"
        prompt = validated["prompt"][:80]
        draw.rectangle((24, 24, validated["width"] - 24, 120), outline=(64, 160, 255), width=2)
        draw.text((40, 40), title, fill=(120, 200, 255))
        draw.text((40, 70), subtitle, fill=(200, 200, 210))
        draw.text((40, 160), f"prompt: {prompt}", fill=(220, 220, 230))
        img.save(out_path)

        return {
            "output_files": [str(out_path)],
            "is_simulation": True,
            "message": "Mock image written. This is Demo / Simulation Mode.",
        }


class UnimplementedNativeAdapter(ModelAdapter):
    """Placeholder for real native adapters (SDXL etc.)."""

    def __init__(self, model_id: str, display_name: str, tasks: list[str]):
        self.model_id = model_id
        self.display_name = display_name
        self.version = "pending"
        self.provider = "native-pending"
        self.supported_tasks = tasks
        self.supported_platforms = ["windows", "linux"]
        self.dependency_requirements = {"note": "Install only on target machine after authorization"}
        self.checkpoint_paths = []
        self.model_license = "see model card"
        self.hardware_requirements = {"status": "unverified"}
        self.estimated_vram = {"status": "unverified"}
        self.estimated_ram = {"status": "unverified"}
        self.precision_options = ["fp16", "bf16"]
        self.input_schema = {}
        self.output_schema = {}
        self.cancellation_supported = False

    def get_status(self) -> AdapterStatus:
        return AdapterStatus(
            model_id=self.model_id,
            loaded=False,
            healthy=False,
            message="Native adapter not implemented on this machine. PENDING TARGET HARDWARE.",
            cancellation_supported=False,
            implementation_status="unimplemented",
        )

    def health_check(self) -> dict[str, Any]:
        return {
            "ok": False,
            "implementation_status": "unimplemented",
            "verification_status": "PENDING TARGET HARDWARE",
        }

    def validate_environment(self) -> dict[str, Any]:
        return {
            "ok": False,
            "implementation_status": "unimplemented",
            "message": "Real weights and CUDA stack must be installed on the target PC.",
        }

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        raise NotImplementedError(
            f"{self.model_id}: real inference not implemented. "
            "Do not treat UI presence as availability."
        )
