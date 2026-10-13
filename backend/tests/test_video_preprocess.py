from __future__ import annotations

import subprocess
from pathlib import Path


def _make_test_video(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x240:d=2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr


def test_video_status(client):
    resp = client.get("/api/video/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ffmpeg_available"] is True
    assert data["features"]["info"] is True
    assert data["features"]["text_to_video"] is False


def test_task_schemas(client):
    resp = client.get("/api/task-schemas")
    assert resp.status_code == 200
    data = resp.json()
    assert "video_gen" in data
    assert "pose_extract" in data
    assert "image_to_3d" in data


def test_preprocess_info_and_frames(client, tmp_path, monkeypatch):
    # Use client fixture's data dirs via upload
    video_bytes_path = tmp_path / "sample.mp4"
    _make_test_video(video_bytes_path)

    with video_bytes_path.open("rb") as fh:
        up = client.post(
            "/api/assets/upload",
            files={"file": ("sample.mp4", fh, "video/mp4")},
        )
    assert up.status_code == 200
    asset_id = up.json()["asset_id"]

    info = client.post(
        "/api/video/preprocess",
        json={"asset_id": asset_id, "mode": "info"},
    )
    assert info.status_code == 200
    assert info.json()["result"]["duration_seconds"] > 0

    frames = client.post(
        "/api/video/preprocess",
        json={
            "asset_id": asset_id,
            "mode": "interval",
            "interval_seconds": 0.5,
            "max_frames": 5,
        },
    )
    assert frames.status_code == 200
    assert frames.json()["result"]["frame_count"] >= 1
    assert frames.json()["result"]["source_preserved"] is True


def test_t2v_validate_separate_from_i2v(client):
    bad = client.post(
        "/api/video/generate/validate",
        json={"task_kind": "image_to_video", "prompt": "x"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/video/generate/validate",
        json={"task_kind": "text_to_video", "prompt": "a cat walks"},
    )
    assert ok.status_code == 200
    assert ok.json()["execution"] == "not_started"
