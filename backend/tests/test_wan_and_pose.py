from __future__ import annotations

import json
from pathlib import Path


def test_wan_workflows_load_and_placeholders():
    from app.adapters.wan_comfy_adapter import apply_placeholders, load_workflow_template

    t2v = load_workflow_template("wan_t2v_1.3b_api.json")
    assert "3" in t2v
    filled = apply_placeholders(
        t2v,
        {
            "PROMPT_POSITIVE": "hello",
            "PROMPT_NEGATIVE": "bad",
            "seed": 42,
            "steps": 10,
            "cfg": 5.5,
            "width": 480,
            "height": 480,
            "length": 17,
            "fps": 16,
        },
    )
    # Find a CLIP encode with our prompt
    texts = []
    for node in filled.values():
        if isinstance(node, dict):
            inputs = node.get("inputs") or {}
            if "text" in inputs:
                texts.append(inputs["text"])
    assert "hello" in texts
    assert "bad" in texts


def test_wan_i2v_conservative_defaults():
    from app.adapters.wan_comfy_adapter import WanI2VAdapter
    from app.core.config import Settings

    adapter = WanI2VAdapter(Settings(run_mode="simulation"))
    # Requires image path — use a temp that we create
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        path = fh.name
        fh.write(b"x")
    try:
        data = adapter.validate_input(
            {"prompt": "move", "input_image_path": path}
        )
        assert data["length"] == 17
        assert data["steps"] == 12
    finally:
        Path(path).unlink(missing_ok=True)


def test_wan_i2v_requires_image():
    from app.adapters.wan_comfy_adapter import WanI2VAdapter
    from app.core.config import Settings

    adapter = WanI2VAdapter(Settings(run_mode="simulation"))
    try:
        adapter.validate_input({"prompt": "x"})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "I2V" in str(exc)


def test_pose_not_ready_without_env(client):
    create = client.post(
        "/api/tasks",
        json={
            "task_type": "pose_extract",
            "model_id": "pose-mediapipe",
            "parameters": {"frame_paths": ["/tmp/nope.png"]},
        },
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]
    import time

    final = None
    for _ in range(40):
        final = client.get(f"/api/tasks/{task_id}").json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "failed"
    assert "not ready" in (final["error_message"] or "").lower()
    assert final["is_simulation"] is False


def test_video_generate_validate_i2v_requires_ref(client):
    resp = client.post(
        "/api/video/generate/validate",
        json={"task_kind": "image_to_video", "prompt": "x"},
    )
    assert resp.status_code == 400


def test_video_generate_t2v_enqueues(client):
    resp = client.post(
        "/api/video/generate",
        json={
            "task_kind": "text_to_video",
            "prompt": "foggy hills",
            "model_id": "wan2.1-t2v-1.3b",
            "width": 480,
            "height": 480,
            "num_frames": 17,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_type"] == "text_to_video"
    assert data["model_id"] == "wan2.1-t2v-1.3b"
    # Without ComfyUI, should fail (not simulate success)
    import time

    final = None
    for _ in range(40):
        final = client.get(f"/api/tasks/{data['task_id']}").json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "failed"
    assert final["is_simulation"] is False


def test_motion_status(client):
    resp = client.get("/api/motion/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stage"] >= 1
    assert "pose_extract" in data


def test_registry_has_pose_and_i2v(client):
    models = client.get("/api/models").json()["models"]
    ids = {m["id"] for m in models}
    assert "wan2.1-i2v" in ids
    assert "pose-mediapipe" in ids
    assert "wan2.1-t2v-1.3b" in ids


def test_wan_workflow_files_exist():
    root = Path(__file__).resolve().parents[2]
    assert (root / "config" / "workflows" / "wan_t2v_1.3b_api.json").exists()
    assert (root / "config" / "workflows" / "wan_i2v_480p_api.json").exists()
    meta = json.loads(
        (root / "config" / "workflows" / "wan_i2v_480p_api.json").read_text(encoding="utf-8")
    )
    assert "_meta" in meta
