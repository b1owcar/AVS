#!/usr/bin/env python3
"""TRELLIS image-to-3D worker — env-trellis only. Never import from main backend.

Official upstream focuses on Linux and states >=16GB VRAM. Fail honestly if
TRELLIS is not importable or run fails.
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
    req = Path(args.request)
    resp = Path(args.response)
    payload = json.loads(req.read_text(encoding="utf-8"))
    try:
        image_path = Path(payload["image_path"])
        if not image_path.exists():
            raise FileNotFoundError(f"image missing: {image_path}")
        out_dir = Path(payload["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        formats = payload.get("output_formats") or ["glb"]

        try:
            # Prefer a thin local wrapper if the operator installed one.
            import trellis_runner  # type: ignore
        except ImportError:
            trellis_runner = None

        if trellis_runner is None:
            raise RuntimeError(
                "TRELLIS Python package / trellis_runner not importable in env-trellis. "
                "Clone microsoft/TRELLIS into this env and provide trellis_runner.run_image_to_3d, "
                "or extend this worker. Official: Linux, >=16GB VRAM — do not claim Win success."
            )

        result = trellis_runner.run_image_to_3d(
            image_path=str(image_path),
            output_dir=str(out_dir),
            output_formats=formats,
        )
        outputs = list(result.get("output_files") or [])
        if not outputs:
            raise RuntimeError("trellis_runner returned no output_files")
        out = {
            "ok": True,
            "is_simulation": False,
            "output_files": outputs,
            "message": result.get("message", "TRELLIS image-to-3d completed"),
            "meta": result.get("meta") or {"runner": "trellis_runner"},
        }
        resp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001
        out = {
            "ok": False,
            "is_simulation": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "message": f"TRELLIS worker failed: {exc}",
        }
        resp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(out["message"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
