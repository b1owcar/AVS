from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterStatus, ModelAdapter, ResourceEstimate
from app.core.config import Settings
from app.services.video_preprocess import VideoPreprocessService


class TrellisImageTo3DAdapter(ModelAdapter):
    """Phase 6 image-to-3D via isolated env-trellis. Official: Linux, >=16GB VRAM."""

    model_id = "trellis-image-to-3d"
    display_name = "Microsoft TRELLIS (Image to 3D)"
    version = "experimental"
    provider = "microsoft / env-trellis"
    supported_tasks = ["image_to_3d"]
    supported_platforms = ["linux"]  # Windows not claimed verified
    dependency_requirements = {
        "env": "env-trellis",
        "repo": "https://github.com/microsoft/TRELLIS",
        "official_vram_gb": 16,
        "isolation": "required",
    }
    checkpoint_paths: list[str] = []
    model_license = "see microsoft/TRELLIS repository"
    hardware_requirements = {
        "compat": "conditional_or_unsupported",
        "official_vram_gb": 16,
        "note": "12GB laptops may be insufficient — do not claim success without local measure",
    }
    estimated_vram = {
        "min_mb": 16000,
        "basis": "official README — PENDING TARGET HARDWARE",
    }
    estimated_ram = {"status": "unverified"}
    precision_options = ["fp16"]
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    cancellation_supported = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def trellis_python(self) -> Path | None:
        return self.settings.trellis_python

    @property
    def worker_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "envs" / "trellis" / "worker_image_to_3d.py"

    def validate_environment(self) -> dict[str, Any]:
        issues: list[str] = []
        py = self.trellis_python
        if py is None or not py.exists():
            issues.append(
                "LAVS_TRELLIS_PYTHON missing. Prefer Linux: scripts/linux/install-trellis.sh "
                "(Windows: install-trellis.ps1 is experimental / unsupported claim)."
            )
        if not self.worker_script.exists():
            issues.append(f"Worker missing: {self.worker_script}")
        ok = not issues
        return {
            "ok": ok,
            "trellis_python": str(py) if py else None,
            "worker_script": str(self.worker_script),
            "issues": issues,
            "implementation_status": "available" if ok else "not_ready",
            "message": "trellis worker ready" if ok else "; ".join(issues),
            "vram_warning": "Official TRELLIS states >=16GB VRAM",
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        image = payload.get("image_path") or payload.get("input_image_path")
        if not image:
            raise ValueError("image_to_3d requires image_path")
        if not Path(str(image)).exists():
            raise FileNotFoundError(f"image missing: {image}")
        formats = payload.get("output_formats") or ["glb"]
        if isinstance(formats, str):
            formats = [formats]
        return {
            "image_path": str(image),
            "output_formats": list(formats),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=16000,
            vram_mb_max=None,
            conditions=["official TRELLIS >=16GB"],
            basis="upstream README",
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
            "message": "trellis cancel not supported",
        }

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        env = self.validate_environment()
        if not env.get("ok"):
            raise RuntimeError("; ".join(env.get("issues") or ["trellis not ready"]))
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
            progress_cb(0.05, "launching env-trellis worker")
        py = self.trellis_python
        assert py is not None
        proc = subprocess.Popen(
            [str(py), str(self.worker_script), "--request", str(req), "--response", str(resp)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while proc.poll() is None:
            if progress_cb:
                progress_cb(0.4, "trellis running")
            time.sleep(1.0)
        stdout, stderr = proc.communicate(timeout=5)
        if not resp.exists():
            raise RuntimeError(
                f"trellis worker produced no response (code={proc.returncode}): {stderr or stdout}"
            )
        data = json.loads(resp.read_text(encoding="utf-8"))
        if not data.get("ok"):
            raise RuntimeError(data.get("message") or data.get("error") or "trellis failed")
        if progress_cb:
            progress_cb(1.0, "trellis completed")
        return {
            "output_files": data.get("output_files") or [],
            "is_simulation": False,
            "message": data.get("message", "TRELLIS image-to-3d completed"),
            "meta": data.get("meta") or {},
        }


class VideoTo3DKeyframeAdapter(ModelAdapter):
    """Phase 6 video-to-3D keyframe approximation — NOT full geometry recovery."""

    model_id = "video-to-3d-keyframe"
    display_name = "Video→3D Keyframe Approx"
    version = "0.1.0"
    provider = "lavs"
    supported_tasks = ["video_to_3d"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {"ffmpeg": "required", "optional": "trellis for first-frame mesh"}
    checkpoint_paths: list[str] = []
    model_license = "N/A (orchestration)"
    hardware_requirements = {"compat": "conditional"}
    estimated_vram = {"status": "delegated_to_optional_trellis"}
    estimated_ram = {"status": "unverified"}
    precision_options = ["n/a"]
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    cancellation_supported = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._trellis = TrellisImageTo3DAdapter(settings)

    def validate_environment(self) -> dict[str, Any]:
        svc = VideoPreprocessService(
            upload_dir=self.settings.upload_dir, output_dir=self.settings.output_dir
        )
        ffmpeg_ok = svc.available()
        trellis = self._trellis.validate_environment()
        return {
            "ok": ffmpeg_ok,
            "ffmpeg_available": ffmpeg_ok,
            "trellis_optional": trellis,
            "implementation_status": "available" if ffmpeg_ok else "not_ready",
            "message": (
                "keyframe approx ready (FFmpeg)"
                if ffmpeg_ok
                else "FFmpeg required for video-to-3d keyframe approx"
            ),
            "disclaimer": (
                "keyframe_approx must NOT be described as full geometry recovery "
                "or equivalent to multi-view reconstruction."
            ),
        }

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        video = payload.get("video_path") or payload.get("input_video_path")
        if not video or not Path(str(video)).exists():
            raise ValueError("video_to_3d requires existing video_path")
        mode = str(payload.get("mode") or "keyframe_approx")
        if mode == "multiview_rebuild":
            raise ValueError(
                "multiview_rebuild is not implemented — use keyframe_approx "
                "(does not claim full geometry recovery)"
            )
        if mode != "keyframe_approx":
            raise ValueError(f"unsupported mode: {mode}")
        return {
            "video_path": str(video),
            "mode": mode,
            "max_frames": int(payload.get("max_frames") or 8),
            "run_trellis_on_first": bool(payload.get("run_trellis_on_first", False)),
        }

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        return ResourceEstimate(
            vram_mb_min=0,
            vram_mb_max=16000,
            conditions=["ffmpeg cpu; optional trellis"],
            basis="orchestration",
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
        return {"ok": False, "cancellation_supported": False, "message": "n/a"}

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        env = self.validate_environment()
        if not env.get("ok"):
            raise RuntimeError(env.get("message") or "video-to-3d not ready")
        validated = self.validate_input(payload)
        out_dir = Path(payload["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        svc = VideoPreprocessService(
            upload_dir=self.settings.upload_dir, output_dir=self.settings.output_dir
        )
        job_id = uuid.uuid4().hex[:12]
        if progress_cb:
            progress_cb(0.1, "extracting keyframes for approx pack")
        result = svc.extract_keyframes(
            Path(validated["video_path"]),
            max_frames=validated["max_frames"],
            job_id=job_id,
        )
        frames = list(result.get("frames") or [])
        # Copy/list into task output
        frame_copies: list[str] = []
        for i, fp in enumerate(frames):
            src = Path(fp)
            if not src.exists():
                continue
            dest = out_dir / f"keyframe_{i:03d}{src.suffix}"
            dest.write_bytes(src.read_bytes())
            frame_copies.append(str(dest))

        outputs = list(frame_copies)
        trellis_outputs: list[str] = []
        trellis_note = "trellis not run"
        if validated["run_trellis_on_first"] and frame_copies:
            t_env = self._trellis.validate_environment()
            if t_env.get("ok"):
                if progress_cb:
                    progress_cb(0.5, "optional TRELLIS on first keyframe")
                t_out = out_dir / "trellis_first"
                t_out.mkdir(parents=True, exist_ok=True)
                t_result = self._trellis.execute(
                    {
                        "image_path": frame_copies[0],
                        "output_dir": str(t_out),
                        "output_formats": payload.get("output_formats") or ["glb"],
                    },
                    progress_cb=None,
                )
                trellis_outputs = list(t_result.get("output_files") or [])
                outputs.extend(trellis_outputs)
                trellis_note = "trellis ran on first keyframe only"
            else:
                trellis_note = "trellis requested but not ready: " + "; ".join(
                    t_env.get("issues") or []
                )

        manifest = {
            "mode": "keyframe_approx",
            "disclaimer": (
                "This pack is a keyframe approximation for downstream 3D experiments. "
                "It is NOT full geometry recovery and NOT multiview rebuild."
            ),
            "source_video": validated["video_path"],
            "keyframes": frame_copies,
            "trellis": {"note": trellis_note, "outputs": trellis_outputs},
            "is_simulation": False,
        }
        manifest_path = out_dir / f"video3d_manifest_{job_id}.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(str(manifest_path))
        if progress_cb:
            progress_cb(1.0, "keyframe approx pack ready")
        return {
            "output_files": outputs,
            "is_simulation": False,
            "message": (
                f"video-to-3d keyframe_approx: {len(frame_copies)} frames. "
                f"{trellis_note}. Not full geometry recovery."
            ),
            "meta": manifest,
        }
