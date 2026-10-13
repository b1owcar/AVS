"""Example Stage-2 transfer hook.

Copy to data/models/motion-transfer/run_transfer.py on the office PC and
implement a real AnimateAnyone / MimicMotion / ComfyUI bridge here.

Signature expected by envs/motion/worker_transfer.py:

    def run_transfer(payload: dict) -> dict

payload keys include pose_json_path, target_image_path, output_dir, weights_dir.
Return: {ok, output_files, message, meta?} — never invent a fake MP4 success.
"""
from __future__ import annotations

from typing import Any


def run_transfer(payload: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError(
        "Replace run_transfer.example.py with a real run_transfer.py that calls "
        "your chosen motion-transfer stack. Skeleton compose preview is NOT transfer."
    )
