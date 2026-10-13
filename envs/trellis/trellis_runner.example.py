"""Legacy example stub.

Prefer the shipped `trellis_runner.py`, which calls microsoft/TRELLIS when installed.
Keep this file only if you need a custom runner API.
"""
from __future__ import annotations

from typing import Any


def run_image_to_3d(
    *, image_path: str, output_dir: str, output_formats: list[str]
) -> dict[str, Any]:
    raise NotImplementedError(
        "Use envs/trellis/trellis_runner.py (shipped). Install microsoft/TRELLIS "
        "into env-trellis so TrellisImageTo3DPipeline imports succeed."
    )
