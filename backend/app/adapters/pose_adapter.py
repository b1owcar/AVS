from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate
from app.core.config import Settings

# MediaPipe Pose landmark connections (subset for skeleton preview)
POSE_EDGES = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (24, 26),
    (26, 28),
    (0, 11),
    (0, 12),
]


class PoseMediapipeAdapter(ModelAdapter):
    """Phase 5 stage-1: extract pose JSON + skeleton preview via env-pose worker.

    Never reports success without a real worker run.
    """

    model_id = "pose-mediapipe"
    display_name = "MediaPipe Pose Extract (env-pose)"
    version = "0.1.0"
    provider = "mediapipe"
    supported_tasks = ["pose_extract"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {"env": "env-pose", "packages": ["mediapipe", "opencv-python-headless"]}
    checkpoint_paths: list[str] = []
    model_license = "Apache-2.0 (MediaPipe)"
    hardware_requirements = {"gpu": "optional (CPU ok for stage-1)"}
    estimated_vram = {"min_mb": 0, "max_mb": 2000, "basis": "CPU-capable"}
    estimated_ram = {"min_mb": 1024, "max_mb": 4096}
    precision_options = ["fp32"]
    input_schema = {
        "type": "object",
        "properties": {
            "frame_paths": {"type": "array"},
            "person_id": {"type": "integer"},
            "export_skeleton_preview": {"type": "boolean"},
        },
        "required": ["frame_paths"],
    }
    output_schema = {"type": "object"}
    cancellation_supported = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def pose_python(self) -> Path | None:
        return self.settings.pose_python

    @property
    def worker_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "envs" / "pose" / "worker_pose.py"

    def validate_environment(self) -> dict[str, Any]:
        issues: list[str] = []
        py = self.pose_python
        if py is None or not py.exists():
            issues.append(
                "LAVS_POSE_PYTHON not set or missing. Run scripts/windows/install-pose.ps1 on D:\\avs."
            )
        if not self.worker_script.exists():
            issues.append(f"Worker script missing: {self.worker_script}")
        ok = not issues
        return {
            "ok": ok,
            "pose_python": str(py) if py else None,
            "worker_script": str(self.worker_script),
            "issues": issues,
            "implementation_status": "available" if ok else "not_ready",
            "message": "pose worker ready" if ok else "; ".join(issues),
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        frames = payload.get("frame_paths") or []
        if isinstance(frames, str):
            frames = [frames]
        frames = [str(p) for p in frames]
        if not frames:
            single = payload.get("input_image_path") or payload.get("reference_image_path")
            if single:
                frames = [str(single)]
        if not frames:
            raise ValueError("pose_extract requires frame_paths (extracted video frames or images)")
        for p in frames:
            if not Path(p).exists():
                raise FileNotFoundError(f"frame missing: {p}")
        return {
            "frame_paths": frames,
            "person_id": payload.get("person_id"),
            "export_skeleton_preview": bool(payload.get("export_skeleton_preview", True)),
            "coordinate_system": str(payload.get("coordinate_system") or "image_pixel"),
            "min_detection_confidence": float(payload.get("min_detection_confidence", 0.5)),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=0,
            vram_mb_max=2000,
            conditions=["MediaPipe Pose CPU/GPU"],
            basis="stage-1 extract",
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
            "message": "pose extract cancel not supported",
        }

    @staticmethod
    def draw_skeleton(image_path: Path, landmarks: list[dict[str, Any]], out_path: Path) -> None:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        pts: dict[int, tuple[float, float]] = {}
        for lm in landmarks:
            idx = int(lm["id"])
            x = float(lm["x"])
            y = float(lm["y"])
            # support normalized or pixel
            if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                x, y = x * w, y * h
            pts[idx] = (x, y)
            r = 3
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 220, 180))
        for a, b in POSE_EDGES:
            if a in pts and b in pts:
                draw.line([pts[a], pts[b]], fill=(255, 120, 40), width=2)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        env = self.validate_environment()
        if not env.get("ok"):
            raise RuntimeError("; ".join(env.get("issues") or ["pose worker not ready"]))

        validated = self.validate_input(payload)
        out_dir = Path(payload["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        work = out_dir / "_worker"
        work.mkdir(parents=True, exist_ok=True)
        req_path = work / "request.json"
        resp_path = work / "response.json"

        request = {
            **validated,
            "output_dir": str(out_dir),
        }
        req_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

        if progress_cb:
            progress_cb(0.05, "launching env-pose worker")

        py = self.pose_python
        assert py is not None
        proc = subprocess.Popen(
            [str(py), str(self.worker_script), "--request", str(req_path), "--response", str(resp_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while proc.poll() is None:
            if progress_cb:
                progress_cb(0.4, "pose worker running")
            time.sleep(0.4)

        stdout, stderr = proc.communicate(timeout=5)
        if not resp_path.exists():
            raise RuntimeError(
                f"pose worker produced no response (code={proc.returncode}): {stderr or stdout}"
            )
        resp = json.loads(resp_path.read_text(encoding="utf-8"))
        if not resp.get("ok"):
            raise RuntimeError(resp.get("message") or resp.get("error") or "pose extract failed")

        outputs: list[str] = list(resp.get("output_files") or [])
        pose_json_path = out_dir / f"pose_{uuid.uuid4().hex[:10]}.json"
        pose_payload = {
            "model_id": self.model_id,
            "coordinate_system": validated["coordinate_system"],
            "person_id": validated.get("person_id"),
            "frames": resp.get("frames") or [],
            "persons_detected": resp.get("persons_detected"),
            "is_simulation": False,
        }
        pose_json_path.write_text(json.dumps(pose_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(str(pose_json_path))

        if validated["export_skeleton_preview"]:
            for frame_result in resp.get("frames") or []:
                src = Path(frame_result["path"])
                landmarks = frame_result.get("landmarks") or []
                if not landmarks or not src.exists():
                    continue
                skel = out_dir / f"skeleton_{src.stem}.png"
                self.draw_skeleton(src, landmarks, skel)
                outputs.append(str(skel))

        if progress_cb:
            progress_cb(1.0, "pose extract completed")
        return {
            "output_files": outputs,
            "is_simulation": False,
            "message": resp.get("message", "pose extract completed"),
            "meta": {
                "persons_detected": resp.get("persons_detected"),
                "frame_count": len(resp.get("frames") or []),
            },
        }
