#!/usr/bin/env python3
"""Motion transfer worker — env-motion only.

Supported backends (under weights_dir):
  1) run_transfer.py with run_transfer(payload) -> dict
  2) backend.json {"backend":"external_script","script":"run_transfer.py"}
  3) backend.json {"backend":"comfyui","workflow_file":"...","comfyui_url":"..."}

Without a wired backend this fails honestly. Do not invent fake video output.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any


IGNORE_NAMES = {
    "readme.txt",
    "readme.md",
    ".gitkeep",
    "backend.example.json",
    "run_transfer.example.py",
}


def _load_backend_config(weights: Path) -> dict[str, Any]:
    cfg_path = weights / "backend.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    if (weights / "run_transfer.py").exists():
        return {"backend": "external_script", "script": "run_transfer.py"}
    return {}


def _run_external_script(weights: Path, payload: dict[str, Any], script_name: str) -> dict[str, Any]:
    script = weights / script_name
    if not script.exists():
        raise FileNotFoundError(f"external_script missing: {script}")
    spec = importlib.util.spec_from_file_location("lavs_run_transfer", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "run_transfer", None)
    if not callable(fn):
        raise RuntimeError(f"{script} must define run_transfer(payload) -> dict")
    result = fn(payload)
    if not isinstance(result, dict):
        raise RuntimeError("run_transfer must return a dict")
    return result


def _run_comfyui(weights: Path, payload: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(
            "comfyui backend needs httpx in env-motion (pip install httpx)"
        ) from exc

    workflow_file = cfg.get("workflow_file")
    if not workflow_file:
        raise RuntimeError("backend.json comfyui requires workflow_file")
    wf_path = Path(str(workflow_file))
    if not wf_path.is_absolute():
        wf_path = weights / wf_path
    if not wf_path.exists():
        # also allow repo config/workflows relative to install root via env
        alt = Path(payload.get("workflow_search_dir") or ".") / str(workflow_file)
        if alt.exists():
            wf_path = alt
        else:
            raise FileNotFoundError(f"ComfyUI workflow missing: {workflow_file}")

    workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    # Optional simple placeholder substitution for operators who ship templated JSON
    text = json.dumps(workflow)
    replacements = {
        "{{TARGET_IMAGE}}": str(payload["target_image_path"]),
        "{{POSE_JSON}}": str(payload["pose_json_path"]),
        "{{OUTPUT_PREFIX}}": f"lavs_motion_{uuid.uuid4().hex[:8]}",
    }
    for key, val in replacements.items():
        text = text.replace(key, val.replace("\\", "\\\\"))
    workflow = json.loads(text)

    base = str(cfg.get("comfyui_url") or "http://127.0.0.1:8188").rstrip("/")
    timeout = float(cfg.get("timeout_seconds") or 600)
    client_id = f"lavs-motion-{uuid.uuid4().hex[:8]}"
    with httpx.Client(timeout=timeout) as client:
        probe = client.get(f"{base}/system_stats")
        if probe.status_code >= 400:
            raise RuntimeError(f"ComfyUI not reachable at {base}: HTTP {probe.status_code}")
        submitted = client.post(
            f"{base}/prompt",
            json={"prompt": workflow, "client_id": client_id},
        )
        if submitted.status_code >= 400:
            raise RuntimeError(f"ComfyUI prompt rejected: {submitted.text[:400]}")
        prompt_id = submitted.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI response missing prompt_id: {submitted.text[:400]}")

        # Poll history
        outputs: list[str] = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            hist = client.get(f"{base}/history/{prompt_id}")
            if hist.status_code == 200:
                body = hist.json() or {}
                entry = body.get(prompt_id) or {}
                if entry.get("status", {}).get("completed") or entry.get("outputs"):
                    # Collect file names; operator must map Comfy output dir separately
                    for node_out in (entry.get("outputs") or {}).values():
                        for images in node_out.values():
                            if isinstance(images, list):
                                for item in images:
                                    if isinstance(item, dict) and item.get("filename"):
                                        outputs.append(str(item["filename"]))
                    break
            time.sleep(1.0)
        else:
            raise RuntimeError(f"ComfyUI prompt {prompt_id} timed out after {timeout}s")

    if not outputs:
        raise RuntimeError(
            "ComfyUI finished but no output filenames were reported. "
            "Check custom-node workflow outputs and ComfyUI output folder."
        )
    return {
        "ok": True,
        "output_files": outputs,
        "message": "motion transfer via ComfyUI backend completed",
        "meta": {"backend": "comfyui", "prompt_id": prompt_id, "workflow": str(wf_path)},
        "is_simulation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args()
    req = Path(args.request)
    resp = Path(args.response)
    payload = json.loads(req.read_text(encoding="utf-8"))
    try:
        weights = Path(payload["weights_dir"])
        if not weights.exists():
            raise RuntimeError(f"weights_dir missing: {weights}")

        cfg = _load_backend_config(weights)
        backend = str(cfg.get("backend") or "").lower()
        if not backend:
            raise RuntimeError(
                f"No transfer backend wired under {weights}. "
                "Add run_transfer.py (see envs/motion/run_transfer.example.py) "
                "or backend.json. README.txt alone is not enough. "
                "Do not treat skeleton compose as transfer."
            )

        if backend == "external_script":
            result = _run_external_script(
                weights, payload, str(cfg.get("script") or "run_transfer.py")
            )
        elif backend == "comfyui":
            result = _run_comfyui(weights, payload, cfg)
        else:
            raise RuntimeError(
                f"Unsupported backend={backend!r}. Supported: external_script, comfyui."
            )

        if not result.get("ok", True):
            raise RuntimeError(result.get("message") or result.get("error") or "transfer failed")
        outputs = list(result.get("output_files") or [])
        if not outputs:
            raise RuntimeError("transfer backend returned no output_files")
        out = {
            "ok": True,
            "is_simulation": bool(result.get("is_simulation", False)),
            "output_files": outputs,
            "message": result.get("message", "motion transfer completed"),
            "meta": result.get("meta") or {"backend": backend},
        }
        resp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001
        out = {
            "ok": False,
            "is_simulation": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "message": f"motion transfer failed: {exc}",
        }
        resp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(out["message"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
