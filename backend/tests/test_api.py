from __future__ import annotations

import time


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["run_mode"] == "simulation"


def test_system_info_degraded_ok(client):
    resp = client.get("/api/system/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "gpu" in data
    assert "disclaimer" in data
    assert data["run_mode"] == "simulation"


def test_model_registry_seeded(client):
    resp = client.get("/api/models")
    assert resp.status_code == 200
    models = resp.json()["models"]
    ids = {m["id"] for m in models}
    assert "mock-demo" in ids
    assert "sdxl-base-1.0" in ids
    mock = next(m for m in models if m["id"] == "mock-demo")
    assert mock["availability"] == "available_simulation"
    sdxl = next(m for m in models if m["id"] == "sdxl-base-1.0")
    assert sdxl["availability"] == "unavailable"
    assert sdxl["verification_status"] == "unverified"


def test_download_deferred(client):
    resp = client.post("/api/models/sdxl-base-1.0/download")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["status"] == "deferred"


def test_mock_task_completes(client):
    create = client.post(
        "/api/tasks",
        json={
            "task_type": "text_to_image",
            "model_id": "mock-demo",
            "parameters": {"prompt": "studio test", "width": 256, "height": 256},
        },
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]
    assert create.json()["is_simulation"] is True

    final = None
    for _ in range(40):
        got = client.get(f"/api/tasks/{task_id}")
        assert got.status_code == 200
        final = got.json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.2)

    assert final is not None
    assert final["status"] == "completed"
    assert final["is_simulation"] is True
    assert final["output_files"]
    assert final["progress"] == 1.0


def test_sdxl_not_ready_fails_clearly(client):
    create = client.post(
        "/api/tasks",
        json={
            "task_type": "text_to_image",
            "model_id": "sdxl-base-1.0",
            "parameters": {"prompt": "should fail"},
        },
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]

    final = None
    for _ in range(40):
        got = client.get(f"/api/tasks/{task_id}")
        final = got.json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.1)

    assert final is not None
    assert final["status"] == "failed"
    assert "not ready" in (final["error_message"] or "").lower()
    assert final["is_simulation"] is False


def test_comfy_workflow_builder():
    from app.adapters.comfyui_adapter import build_sdxl_txt2img_workflow

    wf = build_sdxl_txt2img_workflow(
        prompt="a cat",
        negative_prompt="",
        checkpoint="sd_xl_base_1.0.safetensors",
        width=768,
        height=768,
        steps=20,
        cfg=7.0,
        seed=1,
    )
    assert wf["4"]["class_type"] == "CheckpointLoaderSimple"
    assert wf["6"]["inputs"]["text"] == "a cat"


def test_cancel_pending(client):
    # Create an unimplemented task then cancel while pending if still pending
    create = client.post(
        "/api/tasks",
        json={
            "task_type": "text_to_video",
            "model_id": "wan2.1-t2v-1.3b",
            "parameters": {"prompt": "x"},
        },
    )
    task_id = create.json()["task_id"]
    # Immediately cancel — may already be failed; accept both paths
    resp = client.post(f"/api/tasks/{task_id}/cancel")
    if resp.status_code == 200:
        assert resp.json()["status"] in {"cancelled", "cancelling"}
    else:
        # Already terminal
        got = client.get(f"/api/tasks/{task_id}")
        assert got.json()["status"] in {"failed", "cancelled", "completed"}


def test_asset_upload_and_list(client):
    files = {"file": ("hello.txt", b"hello asset", "text/plain")}
    up = client.post("/api/assets/upload", files=files)
    assert up.status_code == 200
    asset_id = up.json()["asset_id"]
    listed = client.get("/api/assets")
    assert listed.status_code == 200
    ids = {a["asset_id"] for a in listed.json()["assets"]}
    assert asset_id in ids
    deleted = client.delete(f"/api/assets/{asset_id}")
    assert deleted.status_code == 200
