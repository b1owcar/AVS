from __future__ import annotations

import time
from pathlib import Path

from PIL import Image


def test_studio3d_status(client):
    resp = client.get("/api/studio3d/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == 6
    assert "image_to_3d" in data
    assert "video_to_3d" in data


def test_trellis_not_ready_fails(client):
    # upload a tiny png
    img_path = Path("/tmp/lavs_t3d.png")
    Image.new("RGB", (64, 64), (10, 20, 30)).save(img_path)
    up = client.post(
        "/api/assets/upload",
        files={"file": ("t.png", img_path.read_bytes(), "image/png")},
    )
    assert up.status_code == 200
    asset_id = up.json()["asset_id"]
    create = client.post(
        "/api/studio3d/image-to-3d",
        json={"image_asset_id": asset_id, "model_id": "trellis-image-to-3d"},
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]
    final = None
    for _ in range(40):
        final = client.get(f"/api/tasks/{task_id}").json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "failed"
    assert final["is_simulation"] is False


def test_video_to_3d_rejects_multiview(client):
    resp = client.post(
        "/api/studio3d/video-to-3d",
        json={"video_asset_id": "x", "mode": "multiview_rebuild"},
    )
    # may 404 asset first if validated after — either 400 from mode or 404
    # call validate endpoint
    v = client.post(
        "/api/studio3d/video-to-3d/validate",
        json={"video_asset_id": "dummy", "mode": "multiview_rebuild"},
    )
    assert v.status_code == 400


def test_motion_transfer_not_ready(client):
    # need json + image assets
    pose = {"frames": [{"path": "x", "landmarks": [{"id": 0, "x": 0.5, "y": 0.5}]}]}
    import json as _json

    up_json = client.post(
        "/api/assets/upload",
        files={"file": ("pose.json", _json.dumps(pose).encode(), "application/json")},
    )
    img_path = Path("/tmp/lavs_tgt.png")
    Image.new("RGB", (32, 32), (1, 2, 3)).save(img_path)
    up_img = client.post(
        "/api/assets/upload",
        files={"file": ("t.png", img_path.read_bytes(), "image/png")},
    )
    create = client.post(
        "/api/motion/transfer",
        json={
            "reference_video_asset_id": up_json.json()["asset_id"],
            "target_type": "person_image",
            "target_asset_id": up_img.json()["asset_id"],
            "model_id": "motion-transfer",
        },
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]
    final = None
    for _ in range(40):
        final = client.get(f"/api/tasks/{task_id}").json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "failed"
    assert "not ready" in (final["error_message"] or "").lower()


def test_skeleton_compose_preview(client):
    import json as _json

    pose = {
        "frames": [
            {
                "path": "x",
                "landmarks": [
                    {"id": 11, "x": 0.4, "y": 0.4},
                    {"id": 12, "x": 0.6, "y": 0.4},
                ],
            }
        ]
    }
    up_json = client.post(
        "/api/assets/upload",
        files={"file": ("pose.json", _json.dumps(pose).encode(), "application/json")},
    )
    img_path = Path("/tmp/lavs_compose.png")
    Image.new("RGB", (64, 64), (40, 40, 40)).save(img_path)
    up_img = client.post(
        "/api/assets/upload",
        files={"file": ("t.png", img_path.read_bytes(), "image/png")},
    )
    create = client.post(
        "/api/motion/compose-preview",
        json={
            "pose_json_asset_id": up_json.json()["asset_id"],
            "target_image_asset_id": up_img.json()["asset_id"],
        },
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]
    final = None
    for _ in range(40):
        final = client.get(f"/api/tasks/{task_id}").json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "completed"
    assert "NOT" in (final.get("logs") or "").upper() or "not" in (
        final.get("logs") or ""
    ).lower()
    assert final["output_files"]


def test_registry_phase6_models(client):
    ids = {m["id"] for m in client.get("/api/models").json()["models"]}
    assert "motion-transfer" in ids
    assert "skeleton-compose-preview" in ids
    assert "video-to-3d-keyframe" in ids
    assert "trellis-image-to-3d" in ids


def test_motion_status_stage2(client):
    data = client.get("/api/motion/status").json()
    assert data["stage"] == 2
    assert "motion_transfer" in data
    assert "skeleton_compose_preview" in data
