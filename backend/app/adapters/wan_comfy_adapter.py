from __future__ import annotations

import copy
import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate
from app.adapters.comfyui_adapter import ComfyUIAdapter
from app.core.config import Settings


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_workflow_template(name: str) -> dict[str, Any]:
    path = _project_root() / "config" / "workflows" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_meta", None)
    return data


def apply_placeholders(workflow: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    wf = copy.deepcopy(workflow)
    for _nid, node in wf.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        for ik, iv in list(inputs.items()):
            if iv == "PROMPT_POSITIVE":
                inputs[ik] = mapping.get("PROMPT_POSITIVE", "")
            elif iv == "PROMPT_NEGATIVE":
                inputs[ik] = mapping.get("PROMPT_NEGATIVE", "")
            elif iv == "INPUT_IMAGE_NAME":
                inputs[ik] = mapping.get("INPUT_IMAGE_NAME", "")
            elif ik == "seed" and "seed" in mapping:
                inputs[ik] = int(mapping["seed"])
            elif ik == "steps" and "steps" in mapping:
                inputs[ik] = int(mapping["steps"])
            elif ik == "cfg" and "cfg" in mapping:
                inputs[ik] = float(mapping["cfg"])
            elif ik == "width" and "width" in mapping:
                inputs[ik] = int(mapping["width"])
            elif ik == "height" and "height" in mapping:
                inputs[ik] = int(mapping["height"])
            elif ik == "length" and "length" in mapping:
                inputs[ik] = int(mapping["length"])
            elif ik == "fps" and "fps" in mapping:
                inputs[ik] = int(mapping["fps"])
    return wf


class WanComfyAdapter(ComfyUIAdapter):
    """Base ComfyUI Wan runner — subclasses fix model_id and workflow."""

    workflow_file = "wan_t2v_1.3b_api.json"
    task_kind = "text_to_video"
    requires_image = False
    cancellation_supported = True

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings.comfyui_url,
            settings.comfyui_timeout_seconds,
            output_dir=settings.output_dir,
            default_checkpoint=settings.comfyui_checkpoint,
            comfy_output_dir=settings.comfyui_output_dir,
        )
        self.settings = settings
        self.supported_tasks = [self.task_kind]

    def validate_environment(self) -> dict[str, Any]:
        health = self.health_check()
        if not health.get("ok"):
            return health
        return {
            **health,
            "workflow_file": self.workflow_file,
            "task_kind": self.task_kind,
            "requires_image": self.requires_image,
            "message": f"ComfyUI reachable for {self.model_id}",
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        if self.task_kind == "text_to_video" and not prompt:
            raise ValueError("T2V requires prompt")
        if self.requires_image and not payload.get("input_image_path") and not payload.get(
            "reference_image_path"
        ):
            raise ValueError("I2V requires input_image_path / reference_image_path (separate from T2V)")
        return {
            "prompt": prompt,
            "negative_prompt": str(
                payload.get("negative_prompt")
                or "色调艳丽，过曝，静态，细节模糊，字幕，画面静止"
            ),
            "width": int(payload.get("width", 832)),
            "height": int(payload.get("height", 480)),
            "length": int(payload.get("num_frames") or payload.get("length") or 33),
            "steps": int(payload.get("num_inference_steps") or payload.get("steps") or 20),
            "cfg": float(payload.get("guidance_scale") or payload.get("cfg") or 6.0),
            "seed": int(payload.get("seed") or int(time.time()) % 2_147_483_647),
            "fps": int(payload.get("fps", 16)),
            "input_image_path": payload.get("input_image_path")
            or payload.get("reference_image_path"),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        if self.task_kind == "image_to_video":
            return ResourceEstimate(
                vram_mb_min=10000,
                vram_mb_max=20000,
                conditions=["Wan I2V 14B 480P — may OOM on 12GB; use short length/fp8 if needed"],
                basis="official I2V is 14B class",
            )
        return ResourceEstimate(
            vram_mb_min=8000,
            vram_mb_max=12000,
            conditions=["Wan T2V 1.3B"],
            basis="official lightweight claim ~8GB",
        )

    def _upload_image(self, client: httpx.Client, image_path: Path) -> str:
        with image_path.open("rb") as fh:
            files = {"image": (image_path.name, fh, "application/octet-stream")}
            data = {"overwrite": "true"}
            resp = client.post(f"{self.base_url}/upload/image", files=files, data=data)
        if resp.status_code != 200:
            raise RuntimeError(f"ComfyUI image upload failed: {resp.status_code} {resp.text[:300]}")
        body = resp.json()
        name = body.get("name") or image_path.name
        return str(name)

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        validated = self.validate_input(payload)
        env = self.validate_environment()
        if not env.get("ok"):
            raise RuntimeError(env.get("message") or "ComfyUI unavailable")

        template = load_workflow_template(self.workflow_file)
        mapping = {
            "PROMPT_POSITIVE": validated["prompt"],
            "PROMPT_NEGATIVE": validated["negative_prompt"],
            "seed": validated["seed"],
            "steps": validated["steps"],
            "cfg": validated["cfg"],
            "width": validated["width"],
            "height": validated["height"],
            "length": validated["length"],
            "fps": validated["fps"],
        }

        with httpx.Client(timeout=max(self.timeout, 120.0)) as client:
            if self.requires_image:
                img = Path(str(validated["input_image_path"]))
                if not img.exists():
                    raise FileNotFoundError(f"I2V input image missing: {img}")
                mapping["INPUT_IMAGE_NAME"] = self._upload_image(client, img)

            workflow = apply_placeholders(template, mapping)
            if progress_cb:
                progress_cb(0.08, f"submitting {self.model_id} workflow")

            # Reuse parent execute path by injecting workflow
            return super().execute(
                {**payload, **validated, "workflow": workflow, "timeout_seconds": payload.get("timeout_seconds", 3600)},
                progress_cb=progress_cb,
            )


class WanT2VAdapter(WanComfyAdapter):
    model_id = "wan2.1-t2v-1.3b"
    display_name = "Wan 2.1 T2V 1.3B (ComfyUI)"
    version = "2.1"
    provider = "Wan-AI / ComfyUI"
    workflow_file = "wan_t2v_1.3b_api.json"
    task_kind = "text_to_video"
    requires_image = False
    model_license = "Apache-2.0 (confirm)"


class WanI2VAdapter(WanComfyAdapter):
    model_id = "wan2.1-i2v"
    display_name = "Wan 2.1 I2V 480P (ComfyUI)"
    version = "2.1"
    provider = "Wan-AI / ComfyUI"
    workflow_file = "wan_i2v_480p_api.json"
    task_kind = "image_to_video"
    requires_image = True
    model_license = "see Wan-AI model card"
    # Override defaults for safer first runs on 12GB
    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = super().validate_input(payload)
        # Conservative defaults if caller did not override
        if payload.get("num_frames") is None and payload.get("length") is None:
            data["length"] = 17
        if payload.get("num_inference_steps") is None and payload.get("steps") is None:
            data["steps"] = 12
        return data
