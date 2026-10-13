#!/usr/bin/env python3
"""Motion transfer worker — env-motion only.

Without real transfer weights this fails honestly. Do not invent fake video output.
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
        weights = Path(payload["weights_dir"])
        if not weights.exists() or not any(weights.iterdir()):
            raise RuntimeError(
                f"No transfer weights in {weights}. "
                "Install a chosen stage-2 model before claiming motion transfer."
            )
        # Real model hook: when weights + deps exist, call the installed pipeline here.
        # Until then fail — never write a fake mp4 and mark success.
        raise RuntimeError(
            "env-motion is installed but no concrete transfer backend is wired for the "
            "weight pack present. Place a supported package and extend worker_transfer.py; "
            "do not treat skeleton compose as transfer."
        )
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
