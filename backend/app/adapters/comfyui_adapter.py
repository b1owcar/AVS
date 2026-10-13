from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate


def build_sdxl_txt2img_workflow(
    *,
    prompt: str,
    negative_prompt: str,
    checkpoint: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    seed: int,
) -> dict[str, Any]:
    """Minimal API-format workflow for ComfyUI SDXL checkpoint txt2img."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "lavs_sdxl", "images": ["8", 0]},
        },
    }


class ComfyUIAdapter(ModelAdapter):
    """ComfyUI local API bridge — health check + SDXL txt2img workflow submit/poll."""

    model_id = "comfyui-bridge"
    display_name = "ComfyUI Bridge"
    version = "0.2.0"
    provider = "comfyui"
    supported_tasks = ["comfy_workflow", "text_to_image"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {"comfyui": "external local service"}
    checkpoint_paths: list[str] = []
    model_license = "N/A (bridge)"
    hardware_requirements = {"delegated_to": "ComfyUI"}
    estimated_vram = {"status": "delegated"}
    estimated_ram = {"status": "delegated"}
    precision_options = ["delegated"]
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    cancellation_supported = True

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        *,
        output_dir: Path | None = None,
        default_checkpoint: str = "sd_xl_base_1.0.safetensors",
        comfy_output_dir: Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.output_dir = output_dir
        self.default_checkpoint = default_checkpoint
        self.comfy_output_dir = comfy_output_dir
        self._client_id = str(uuid.uuid4())
        self._cancel = False
        self._last_prompt_id: str | None = None

    def health_check(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/system_stats")
                if resp.status_code != 200:
                    return {
                        "ok": False,
                        "reachable": False,
                        "url": self.base_url,
                        "status_code": resp.status_code,
                        "message": "ComfyUI responded with unexpected status",
                    }
                checkpoints: list[str] = []
                try:
                    obj = client.get(f"{self.base_url}/object_info/CheckpointLoaderSimple")
                    if obj.status_code == 200:
                        data = obj.json()
                        ckpts = (
                            data.get("CheckpointLoaderSimple", {})
                            .get("input", {})
                            .get("required", {})
                            .get("ckpt_name", [[]])
                        )
                        if isinstance(ckpts, list) and ckpts and isinstance(ckpts[0], list):
                            checkpoints = list(ckpts[0])
                except Exception:  # noqa: BLE001
                    checkpoints = []
                return {
                    "ok": True,
                    "reachable": True,
                    "url": self.base_url,
                    "checkpoints": checkpoints,
                    "default_checkpoint": self.default_checkpoint,
                    "checkpoint_present": self.default_checkpoint in checkpoints
                    if checkpoints
                    else None,
                    "implementation_status": "available",
                    "message": "ComfyUI reachable",
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "reachable": False,
                "url": self.base_url,
                "message": f"ComfyUI not reachable: {exc}",
                "implementation_status": "unavailable",
            }

    def get_status(self) -> AdapterStatus:
        health = self.health_check()
        return AdapterStatus(
            model_id=self.model_id,
            loaded=False,
            healthy=bool(health.get("ok")),
            message=str(health.get("message")),
            cancellation_supported=True,
            implementation_status=str(health.get("implementation_status", "unavailable")),
        )

    def validate_environment(self) -> dict[str, Any]:
        return self.health_check()

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt and "workflow" not in payload:
            raise ValueError("prompt or workflow is required")
        width = int(payload.get("width", 768))
        height = int(payload.get("height", 768))
        return {
            "prompt": prompt,
            "negative_prompt": str(payload.get("negative_prompt", "")),
            "width": width,
            "height": height,
            "num_inference_steps": int(payload.get("num_inference_steps", 25)),
            "guidance_scale": float(payload.get("guidance_scale", 7.0)),
            "seed": int(payload.get("seed", int(time.time()) % 2_147_483_647)),
            "checkpoint": str(payload.get("checkpoint") or self.default_checkpoint),
            "workflow": payload.get("workflow"),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=None,
            vram_mb_max=None,
            conditions=["delegated to ComfyUI"],
            basis="ComfyUI manages VRAM",
        )

    def cancel(self) -> dict[str, Any]:
        self._cancel = True
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if self._last_prompt_id:
                    client.post(
                        f"{self.base_url}/interrupt",
                        json={},
                    )
                    client.post(
                        f"{self.base_url}/queue",
                        json={"delete": [self._last_prompt_id]},
                    )
            return {
                "ok": True,
                "cancellation_supported": True,
                "message": "interrupt requested",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "cancellation_supported": True,
                "message": f"cancel request failed: {exc}",
            }

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        self._cancel = False
        health = self.health_check()
        if not health.get("ok"):
            raise RuntimeError(health.get("message") or "ComfyUI unavailable")

        validated = self.validate_input(payload)
        workflow = validated.get("workflow")
        if workflow is None:
            workflow = build_sdxl_txt2img_workflow(
                prompt=validated["prompt"],
                negative_prompt=validated["negative_prompt"],
                checkpoint=validated["checkpoint"],
                width=validated["width"],
                height=validated["height"],
                steps=validated["num_inference_steps"],
                cfg=validated["guidance_scale"],
                seed=validated["seed"],
            )

        if progress_cb:
            progress_cb(0.05, "submitting ComfyUI workflow")

        with httpx.Client(timeout=max(self.timeout, 60.0)) as client:
            submit = client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": self._client_id},
            )
            if submit.status_code != 200:
                raise RuntimeError(
                    f"ComfyUI /prompt failed: {submit.status_code} {submit.text[:500]}"
                )
            body = submit.json()
            prompt_id = body.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI did not return prompt_id: {body}")
            self._last_prompt_id = prompt_id

            # Poll history
            deadline = time.time() + float(payload.get("timeout_seconds", 1800))
            while time.time() < deadline:
                if self._cancel:
                    raise RuntimeError("cancelled")
                hist = client.get(f"{self.base_url}/history/{prompt_id}")
                if hist.status_code == 200:
                    data = hist.json()
                    if prompt_id in data:
                        entry = data[prompt_id]
                        status = entry.get("status", {})
                        if status.get("completed") or entry.get("outputs"):
                            if progress_cb:
                                progress_cb(0.9, "collecting ComfyUI outputs")
                            outputs = self._collect_outputs(
                                client, entry, Path(payload["output_dir"])
                            )
                            if progress_cb:
                                progress_cb(1.0, "comfyui completed")
                            return {
                                "output_files": outputs,
                                "is_simulation": False,
                                "message": "ComfyUI workflow completed",
                                "meta": {"prompt_id": prompt_id},
                            }
                        if status.get("status_str") == "error":
                            raise RuntimeError(
                                f"ComfyUI workflow error: {json.dumps(status)[:800]}"
                            )
                if progress_cb:
                    progress_cb(0.5, f"comfyui running prompt_id={prompt_id}")
                time.sleep(1.0)

        raise TimeoutError(f"ComfyUI prompt timed out: {prompt_id}")

    def _collect_outputs(
        self, client: httpx.Client, history_entry: dict[str, Any], dest_dir: Path
    ) -> list[str]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved: list[str] = []
        outputs = history_entry.get("outputs") or {}
        for _node_id, node_out in outputs.items():
            images = node_out.get("images") or []
            for img in images:
                filename = img.get("filename")
                subfolder = img.get("subfolder") or ""
                img_type = img.get("type") or "output"
                if not filename:
                    continue
                # Prefer viewing endpoint then copy locally if comfy output dir known
                params = {"filename": filename, "subfolder": subfolder, "type": img_type}
                view = client.get(f"{self.base_url}/view", params=params)
                if view.status_code == 200:
                    target = dest_dir / filename
                    target.write_bytes(view.content)
                    saved.append(str(target))
                    continue
                if self.comfy_output_dir:
                    src = self.comfy_output_dir / subfolder / filename if subfolder else self.comfy_output_dir / filename
                    if src.exists():
                        target = dest_dir / filename
                        shutil.copy2(src, target)
                        saved.append(str(target))
        if not saved:
            raise RuntimeError("ComfyUI finished but no output images were collected")
        return saved


class ComfySdxlAdapter(ComfyUIAdapter):
    """Same bridge, exposed under model_id used by Image Studio for Comfy path."""

    model_id = "sdxl-comfyui"
    display_name = "SDXL via ComfyUI"
    version = "1.0"
