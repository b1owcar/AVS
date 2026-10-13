#!/usr/bin/env python3
"""Warm SDXL HTTP worker — keep pipeline loaded for fast repeat txt2img.

Runs inside env-image (has torch/diffusers). Not the main LAVS backend.

Usage:
  python worker_http.py --host 127.0.0.1 --port 18767 --model-path D:\\avs\\data\\models\\sdxl-base-1.0
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_STATE: dict[str, Any] = {"pipe": None, "device": None, "model_path": None, "lock": threading.Lock()}


def _load_pipeline(model_path: Path) -> None:
    import torch
    from diffusers import StableDiffusionXLPipeline

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
    _STATE["pipe"] = pipe
    _STATE["device"] = device
    _STATE["model_path"] = str(model_path)


def _txt2img(body: dict[str, Any]) -> dict[str, Any]:
    import torch

    pipe = _STATE["pipe"]
    if pipe is None:
        raise RuntimeError("pipeline not loaded")
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
    negative = str(body.get("negative_prompt", ""))
    width = int(body.get("width", 768))
    height = int(body.get("height", 768))
    steps = int(body.get("num_inference_steps", 25))
    guidance = float(body.get("guidance_scale", 7.0))
    seed = body.get("seed")
    output_path = Path(body["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    device = _STATE["device"]
    generator = None
    if seed is not None:
        generator = torch.Generator(device=device).manual_seed(int(seed))

    with _STATE["lock"]:
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()
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

    return {
        "ok": True,
        "output_files": [str(output_path)],
        "device": device,
        "vram_peak_mb": vram_peak,
        "message": f"SDXL warm txt2img on {device}",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        print(f"[sdxl-worker] {self.address_string()} {fmt % args}")

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send(
                200,
                {
                    "ok": _STATE["pipe"] is not None,
                    "device": _STATE["device"],
                    "model_path": _STATE["model_path"],
                },
            )
            return
        self._send(404, {"ok": False, "message": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"ok": False, "message": "invalid json"})
            return
        if path != "/txt2img":
            self._send(404, {"ok": False, "message": "not found"})
            return
        try:
            self._send(200, _txt2img(body))
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "message": str(exc), "error": str(exc)})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18767)
    parser.add_argument("--model-path", required=True)
    args = parser.parse_args()

    model_path = Path(args.model_path)
    if not model_path.exists():
        raise SystemExit(f"model path missing: {model_path}")

    print(f"[sdxl-worker] loading {model_path} …")
    _load_pipeline(model_path)
    print(f"[sdxl-worker] ready on http://{args.host}:{args.port} device={_STATE['device']}")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[sdxl-worker] stopping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
