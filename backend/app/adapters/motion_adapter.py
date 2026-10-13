from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate
from app.adapters.pose_adapter import POSE_EDGES
from app.core.config import Settings


class MotionTransferAdapter(ModelAdapter):
    """Phase 5 stage-2 motion transfer via isolated env-motion worker.

    Without worker + weights this adapter reports not ready and tasks fail
    honestly. Skeleton overlay preview is a separate model_id.
    """

    model_id = "motion-transfer"
    display_name = "Motion Transfer (env-motion)"
    version = "0.1.0"
    provider = "lavs / stage-2"
    supported_tasks = ["motion_transfer"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {
        "env": "env-motion",
        "script": "scripts/windows/install-motion.ps1",
        "note": "Real transfer weights user-triggered; not bundled",
    }
    checkpoint_paths: list[str] = []
    model_license = "depends on chosen transfer model"
    hardware_requirements = {"gpu": "NVIDIA CUDA preferred", "compat": "conditional"}
    estimated_vram = {"min_mb": 8000, "max_mb": 16000, "basis": "PENDING TARGET HARDWARE"}
    estimated_ram = {"min_mb": 8000, "max_mb": 16000}
    precision_options = ["fp16"]
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    cancellation_supported = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def motion_python(self) -> Path | None:
        return self.settings.motion_python

    @property
    def worker_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "envs" / "motion" / "worker_transfer.py"

    @property
    def weights_dir(self) -> Path:
        return Path(self.settings.model_dir) / "motion-transfer"

    def _detect_backend(self) -> dict[str, Any]:
        """Ready only when a concrete backend is wired (not README.txt alone)."""
        root = self.weights_dir
        if not root.exists():
            return {"ok": False, "backend": None, "detail": "weights_dir missing"}
        if (root / "run_transfer.py").exists():
            return {"ok": True, "backend": "external_script", "detail": "run_transfer.py"}
        cfg_path = root / "backend.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return {"ok": False, "backend": None, "detail": f"backend.json invalid: {exc}"}
            backend = str(cfg.get("backend") or "").lower()
            if backend in {"external_script", "comfyui"}:
                return {"ok": True, "backend": backend, "detail": f"backend.json:{backend}"}
            return {
                "ok": False,
                "backend": backend or None,
                "detail": f"unsupported backend in backend.json: {backend!r}",
            }
        return {
            "ok": False,
            "backend": None,
            "detail": (
                f"No run_transfer.py / backend.json under {root}. "
                "See envs/motion/run_transfer.example.py"
            ),
        }

    def validate_environment(self) -> dict[str, Any]:
        issues: list[str] = []
        py = self.motion_python
        if py is None or not py.exists():
            issues.append(
                "LAVS_MOTION_PYTHON missing. Run scripts/windows/install-motion.ps1 "
                "(or scripts/linux/install-motion.sh) on the office PC."
            )
        if not self.worker_script.exists():
            issues.append(f"Worker missing: {self.worker_script}")
        backend = self._detect_backend()
        if not backend.get("ok"):
            issues.append(str(backend.get("detail")))
        ok = not issues
        return {
            "ok": ok,
            "motion_python": str(py) if py else None,
            "worker_script": str(self.worker_script),
            "weights_dir": str(self.weights_dir),
            "backend": backend.get("backend"),
            "issues": issues,
            "implementation_status": "available" if ok else "not_ready",
            "message": (
                f"motion transfer ready ({backend.get('backend')})"
                if ok
                else "; ".join(issues)
            ),
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        pose_json = payload.get("pose_json_path")
        target = payload.get("target_image_path") or payload.get("target_asset_path")
        if not pose_json:
            raise ValueError("motion_transfer requires pose_json_path from stage-1 extract")
        if not target:
            raise ValueError("motion_transfer requires target_image_path (person_image for stage-2)")
        if not Path(str(pose_json)).exists():
            raise FileNotFoundError(f"pose json missing: {pose_json}")
        if not Path(str(target)).exists():
            raise FileNotFoundError(f"target missing: {target}")
        target_type = str(payload.get("target_type") or "person_image")
        if target_type not in {"person_image", "person_video", "mesh_3d", "pre_rendered"}:
            raise ValueError(f"unsupported target_type: {target_type}")
        if target_type != "person_image":
            raise ValueError(
                f"target_type={target_type} not wired yet — stage-2 currently supports person_image only"
            )
        return {
            "pose_json_path": str(pose_json),
            "target_image_path": str(target),
            "target_type": target_type,
            "selected_person_id": payload.get("selected_person_id"),
            "weights_dir": str(self.weights_dir),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=8000,
            vram_mb_max=16000,
            conditions=["stage-2 transfer model"],
            basis="unverified estimate",
        )

    def get_status(self) -> AdapterStatus:
        env = self.validate_environment()
        return AdapterStatus(
            model_id=self.model_id,
            loaded=False,
            healthy=bool(env.get("ok")),
            message=str(env.get("message")),
            cancellation_supported=False,
            implementation_status=str(env.get("implementation_status")),
        )

    def health_check(self) -> dict[str, Any]:
        return self.validate_environment()

    def cancel(self) -> dict[str, Any]:
        return {
            "ok": False,
            "cancellation_supported": False,
            "message": "motion transfer cancel not supported",
        }

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        env = self.validate_environment()
        if not env.get("ok"):
            raise RuntimeError("; ".join(env.get("issues") or ["motion transfer not ready"]))
        validated = self.validate_input(payload)
        out_dir = Path(payload["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        work = out_dir / "_worker"
        work.mkdir(parents=True, exist_ok=True)
        req = work / "request.json"
        resp = work / "response.json"
        req.write_text(
            json.dumps({**validated, "output_dir": str(out_dir)}, ensure_ascii=False),
            encoding="utf-8",
        )
        if progress_cb:
            progress_cb(0.05, "launching env-motion transfer worker")
        py = self.motion_python
        assert py is not None
        proc = subprocess.Popen(
            [str(py), str(self.worker_script), "--request", str(req), "--response", str(resp)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while proc.poll() is None:
            if progress_cb:
                progress_cb(0.45, "motion transfer running")
            time.sleep(0.5)
        stdout, stderr = proc.communicate(timeout=5)
        if not resp.exists():
            raise RuntimeError(
                f"motion worker produced no response (code={proc.returncode}): {stderr or stdout}"
            )
        data = json.loads(resp.read_text(encoding="utf-8"))
        if not data.get("ok"):
            raise RuntimeError(data.get("message") or data.get("error") or "motion transfer failed")
        if progress_cb:
            progress_cb(1.0, "motion transfer completed")
        return {
            "output_files": data.get("output_files") or [],
            "is_simulation": False,
            "message": data.get("message", "motion transfer completed"),
            "meta": data.get("meta") or {},
        }


class SkeletonComposePreviewAdapter(ModelAdapter):
    """Utility: overlay pose skeleton onto a target image.

    Explicitly NOT motion transfer. Completes only as a labeled preview helper.
    """

    model_id = "skeleton-compose-preview"
    display_name = "Skeleton Compose Preview (not transfer)"
    version = "0.1.0"
    provider = "lavs"
    supported_tasks = ["skeleton_compose_preview"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {"pillow": "required"}
    checkpoint_paths: list[str] = []
    model_license = "N/A"
    hardware_requirements = {"gpu": "not required"}
    estimated_vram = {"min_mb": 0, "max_mb": 0, "basis": "cpu pillow"}
    estimated_ram = {"min_mb": 64, "max_mb": 512}
    precision_options = ["n/a"]
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    cancellation_supported = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_environment(self) -> dict[str, Any]:
        return {
            "ok": True,
            "implementation_status": "available",
            "message": "preview helper ready (NOT motion transfer)",
            "is_transfer": False,
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        pose_json = payload.get("pose_json_path")
        target = payload.get("target_image_path")
        if not pose_json or not Path(str(pose_json)).exists():
            raise ValueError("pose_json_path required")
        if not target or not Path(str(target)).exists():
            raise ValueError("target_image_path required")
        return {"pose_json_path": str(pose_json), "target_image_path": str(target)}

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(vram_mb_min=0, vram_mb_max=0, basis="cpu")

    def get_status(self) -> AdapterStatus:
        return AdapterStatus(
            model_id=self.model_id,
            loaded=True,
            healthy=True,
            message="preview helper (not transfer)",
            cancellation_supported=False,
            implementation_status="available",
        )

    def health_check(self) -> dict[str, Any]:
        return self.validate_environment()

    def cancel(self) -> dict[str, Any]:
        return {"ok": False, "cancellation_supported": False, "message": "n/a"}

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        validated = self.validate_input(payload)
        pose = json.loads(Path(validated["pose_json_path"]).read_text(encoding="utf-8"))
        frames = pose.get("frames") or []
        landmarks = []
        if frames:
            landmarks = frames[0].get("landmarks") or []
        out_dir = Path(payload["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"compose_{uuid.uuid4().hex[:10]}.png"
        img = Image.open(validated["target_image_path"]).convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        pts: dict[int, tuple[float, float]] = {}
        for lm in landmarks:
            idx = int(lm["id"])
            x, y = float(lm["x"]), float(lm["y"])
            if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                x, y = x * w, y * h
            pts[idx] = (x, y)
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(80, 200, 255))
        for a, b in POSE_EDGES:
            if a in pts and b in pts:
                draw.line([pts[a], pts[b]], fill=(255, 180, 40), width=2)
        # Banner so nobody mistakes this for transfer
        draw.rectangle((0, 0, w, 28), fill=(20, 20, 20))
        draw.text((8, 8), "SKELETON COMPOSE PREVIEW — NOT MOTION TRANSFER", fill=(255, 220, 80))
        img.save(out_path)
        if progress_cb:
            progress_cb(1.0, "compose preview done")
        return {
            "output_files": [str(out_path)],
            "is_simulation": False,
            "message": "Skeleton compose preview only — not motion transfer inference.",
            "meta": {"kind": "skeleton_compose_preview", "is_motion_transfer": False},
        }
