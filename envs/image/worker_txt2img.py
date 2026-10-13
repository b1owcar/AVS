#!/usr/bin/env python3
"""SDXL text-to-image worker — runs inside env-image, not the main backend venv.

Usage:
  python worker_txt2img.py --request request.json --response response.json
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args()

    req_path = Path(args.request)
    resp_path = Path(args.response)
    payload = json.loads(req_path.read_text(encoding="utf-8"))

    try:
        import torch
        from diffusers import StableDiffusionXLPipeline

        model_path = Path(payload["model_path"])
        output_path = Path(payload["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = str(payload.get("prompt", "")).strip()
        negative = str(payload.get("negative_prompt", ""))
        width = int(payload.get("width", 768))
        height = int(payload.get("height", 768))
        steps = int(payload.get("num_inference_steps", 25))
        guidance = float(payload.get("guidance_scale", 7.0))
        seed = payload.get("seed")

        if not prompt:
            raise ValueError("prompt is required")
        if width < 64 or height < 64 or width > 2048 or height > 2048:
            raise ValueError("width/height out of range")
        if not model_path.exists():
            raise FileNotFoundError(f"model_path not found: {model_path}")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        pipe = StableDiffusionXLPipeline.from_pretrained(
            str(model_path),
            torch_dtype=dtype,
            use_safetensors=True,
            local_files_only=True,
        )
        pipe = pipe.to(device)
        if device == "cuda":
            try:
                pipe.enable_attention_slicing()
            except Exception:
                pass

        generator = None
        if seed is not None:
            generator = torch.Generator(device=device).manual_seed(int(seed))

        result = pipe(
            prompt=prompt,
            negative_prompt=negative or None,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        )
        image = result.images[0]
        image.save(output_path)

        vram_peak = None
        if device == "cuda":
            try:
                vram_peak = int(torch.cuda.max_memory_allocated() / (1024 * 1024))
            except Exception:
                vram_peak = None

        resp = {
            "ok": True,
            "is_simulation": False,
            "output_files": [str(output_path)],
            "device": device,
            "dtype": str(dtype),
            "vram_peak_mb": vram_peak,
            "message": f"SDXL txt2img completed on {device}",
        }
        resp_path.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001
        resp = {
            "ok": False,
            "is_simulation": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "message": f"SDXL worker failed: {exc}",
        }
        resp_path.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        print(resp["message"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
