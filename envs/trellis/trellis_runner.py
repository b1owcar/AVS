"""TRELLIS image-to-3D runner imported by env-trellis worker.

Requires microsoft/TRELLIS installed into this venv (see scripts/linux/install-trellis.sh).
Fails honestly if the package is missing — never writes a fake .glb.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def run_image_to_3d(
    *, image_path: str, output_dir: str, output_formats: list[str] | None = None
) -> dict[str, Any]:
    formats = [str(f).lower() for f in (output_formats or ["glb"])]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"image missing: {image_file}")

    # Upstream recommends native SPCONV for one-shot runs.
    os.environ.setdefault("SPCONV_ALGO", "native")

    try:
        from PIL import Image
        from trellis.pipelines import TrellisImageTo3DPipeline
        from trellis.utils import postprocessing_utils
    except ImportError as exc:
        raise RuntimeError(
            "microsoft/TRELLIS is not importable in env-trellis. "
            "Clone https://github.com/microsoft/TRELLIS and install per upstream README "
            "into this venv, then retry. Official: Linux + >=16GB VRAM — "
            "do not claim Windows success without local measure."
        ) from exc

    model_id = os.environ.get("LAVS_TRELLIS_MODEL", "microsoft/TRELLIS-image-large")
    pipeline = TrellisImageTo3DPipeline.from_pretrained(model_id)
    pipeline.cuda()

    image = Image.open(image_file)
    # Some installs expect RGB; keep alpha handling upstream preprocess.
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")

    outputs = pipeline.run(image, seed=int(os.environ.get("LAVS_TRELLIS_SEED", "1")))
    written: list[str] = []
    meta: dict[str, Any] = {"model": model_id, "formats": formats}

    if "glb" in formats:
        if "gaussian" not in outputs or "mesh" not in outputs:
            raise RuntimeError("TRELLIS outputs missing gaussian/mesh required for GLB export")
        glb_path = out_dir / "trellis_output.glb"
        glb = postprocessing_utils.to_glb(
            outputs["gaussian"][0],
            outputs["mesh"][0],
            simplify=0.95,
            texture_size=1024,
        )
        glb.export(str(glb_path))
        written.append(str(glb_path))

    if "ply" in formats:
        if "gaussian" not in outputs:
            raise RuntimeError("TRELLIS outputs missing gaussian required for PLY export")
        ply_path = out_dir / "trellis_output.ply"
        outputs["gaussian"][0].save_ply(str(ply_path))
        written.append(str(ply_path))

    if not written:
        raise RuntimeError(
            f"No supported output written for formats={formats}. Supported: glb, ply."
        )

    return {
        "output_files": written,
        "message": f"TRELLIS image-to-3d wrote {len(written)} file(s)",
        "meta": meta,
    }
