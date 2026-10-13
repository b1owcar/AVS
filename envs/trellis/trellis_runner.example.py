"""Example stub — copy to trellis_runner.py inside env-trellis after installing TRELLIS.

Rename/adapt to call the real microsoft/TRELLIS pipeline. LAVS imports `trellis_runner`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def run_image_to_3d(
    *, image_path: str, output_dir: str, output_formats: list[str]
) -> dict[str, Any]:
    # TODO: call real TRELLIS here after upstream install.
    raise NotImplementedError(
        "Replace trellis_runner.example.py with a real trellis_runner.py "
        "that invokes microsoft/TRELLIS and writes .glb/.ply under output_dir."
    )
