from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from app.services.path_safety import UnsafePathError, resolve_under, safe_filename


class VideoPreprocessError(RuntimeError):
    pass


class VideoPreprocessService:
    """FFmpeg-based video info / frame extract / clip / transcode.

    Never overwrites the source file. Outputs go under output_dir.
    """

    def __init__(self, *, upload_dir: Path, output_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.ffmpeg = shutil.which("ffmpeg")
        self.ffprobe = shutil.which("ffprobe")

    def available(self) -> bool:
        return bool(self.ffmpeg and self.ffprobe)

    def _require_tools(self) -> None:
        if not self.available():
            raise VideoPreprocessError("FFmpeg/ffprobe not found on PATH")

    def resolve_source(self, path: str | Path) -> Path:
        raw = Path(path)
        # Allow under upload or output roots only
        for root in (self.upload_dir, self.output_dir):
            try:
                return resolve_under(root, raw if raw.is_absolute() else path)
            except UnsafePathError:
                continue
        if raw.is_absolute() and raw.exists():
            # Absolute paths outside roots are rejected for safety
            raise UnsafePathError("Source path must be under upload or output directories")
        # Relative path tried as under upload
        return resolve_under(self.upload_dir, path)

    def probe(self, source: Path) -> dict[str, Any]:
        self._require_tools()
        assert self.ffprobe
        cmd = [
            self.ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(source),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VideoPreprocessError(f"ffprobe failed: {proc.stderr[:500]}")
        data = json.loads(proc.stdout or "{}")
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        fmt = data.get("format") or {}
        duration = float(fmt.get("duration") or 0)
        fps = None
        if video_stream and video_stream.get("r_frame_rate"):
            num, _, den = video_stream["r_frame_rate"].partition("/")
            try:
                fps = float(num) / float(den or 1)
            except ValueError:
                fps = None
        return {
            "path": str(source),
            "duration_seconds": duration,
            "size_bytes": int(fmt.get("size") or source.stat().st_size),
            "format_name": fmt.get("format_name"),
            "width": int(video_stream["width"]) if video_stream and video_stream.get("width") else None,
            "height": int(video_stream["height"]) if video_stream and video_stream.get("height") else None,
            "fps": fps,
            "codec": video_stream.get("codec_name") if video_stream else None,
            "raw": data,
        }

    def extract_interval_frames(
        self,
        source: Path,
        *,
        interval_seconds: float = 1.0,
        max_frames: int = 60,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_tools()
        assert self.ffmpeg
        job = job_id or uuid.uuid4().hex[:12]
        out_dir = self.output_dir / "preprocess" / job / "frames"
        out_dir.mkdir(parents=True, exist_ok=True)
        pattern = out_dir / "frame_%05d.png"
        # fps filter: 1/interval
        fps_expr = 1.0 / interval_seconds
        cmd = [
            self.ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vf",
            f"fps={fps_expr}",
            "-frames:v",
            str(max_frames),
            str(pattern),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VideoPreprocessError(f"ffmpeg extract failed: {proc.stderr[-800:]}")
        frames = sorted(out_dir.glob("frame_*.png"))
        return {
            "job_id": job,
            "output_dir": str(out_dir),
            "frame_count": len(frames),
            "frames": [str(p) for p in frames],
            "source_preserved": True,
        }

    def extract_keyframes(
        self,
        source: Path,
        *,
        max_frames: int = 60,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_tools()
        assert self.ffmpeg
        job = job_id or uuid.uuid4().hex[:12]
        out_dir = self.output_dir / "preprocess" / job / "keyframes"
        out_dir.mkdir(parents=True, exist_ok=True)
        pattern = out_dir / "key_%05d.png"
        cmd = [
            self.ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vf",
            "select=eq(pict_type\\,I)",
            "-vsync",
            "vfr",
            "-frames:v",
            str(max_frames),
            str(pattern),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VideoPreprocessError(f"ffmpeg keyframes failed: {proc.stderr[-800:]}")
        frames = sorted(out_dir.glob("key_*.png"))
        return {
            "job_id": job,
            "output_dir": str(out_dir),
            "frame_count": len(frames),
            "frames": [str(p) for p in frames],
            "source_preserved": True,
        }

    def clip(
        self,
        source: Path,
        *,
        start_seconds: float,
        duration_seconds: float,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_tools()
        assert self.ffmpeg
        job = job_id or uuid.uuid4().hex[:12]
        out_dir = self.output_dir / "preprocess" / job
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"clip_{safe_filename(source.stem)}.mp4"
        cmd = [
            self.ffmpeg,
            "-y",
            "-ss",
            str(start_seconds),
            "-i",
            str(source),
            "-t",
            str(duration_seconds),
            "-c",
            "copy",
            str(out_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            # fallback re-encode
            cmd = [
                self.ffmpeg,
                "-y",
                "-ss",
                str(start_seconds),
                "-i",
                str(source),
                "-t",
                str(duration_seconds),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(out_file),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise VideoPreprocessError(f"ffmpeg clip failed: {proc.stderr[-800:]}")
        return {
            "job_id": job,
            "output_file": str(out_file),
            "source_preserved": True,
        }

    def transcode(
        self,
        source: Path,
        *,
        output_format: str = "mp4",
        job_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_tools()
        assert self.ffmpeg
        job = job_id or uuid.uuid4().hex[:12]
        out_dir = self.output_dir / "preprocess" / job
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = output_format.lstrip(".")
        out_file = out_dir / f"transcode_{safe_filename(source.stem)}.{ext}"
        cmd = [
            self.ffmpeg,
            "-y",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(out_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VideoPreprocessError(f"ffmpeg transcode failed: {proc.stderr[-800:]}")
        return {
            "job_id": job,
            "output_file": str(out_file),
            "source_preserved": True,
        }

    def preview_image(self, source: Path, *, at_seconds: float = 0.5, job_id: str | None = None) -> dict[str, Any]:
        self._require_tools()
        assert self.ffmpeg
        job = job_id or uuid.uuid4().hex[:12]
        out_dir = self.output_dir / "preprocess" / job
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "preview.jpg"
        cmd = [
            self.ffmpeg,
            "-y",
            "-ss",
            str(at_seconds),
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(out_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VideoPreprocessError(f"ffmpeg preview failed: {proc.stderr[-800:]}")
        return {
            "job_id": job,
            "output_file": str(out_file),
            "source_preserved": True,
        }
