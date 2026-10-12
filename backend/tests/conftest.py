from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Isolate test DB / data before importing app settings cache
TEST_ROOT = Path(__file__).resolve().parent / "_tmp_data"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data = tmp_path / "data"
    monkeypatch.setenv("LAVS_RUN_MODE", "simulation")
    monkeypatch.setenv("LAVS_DATA_DIR", str(data))
    monkeypatch.setenv("LAVS_MODEL_DIR", str(data / "models"))
    monkeypatch.setenv("LAVS_OUTPUT_DIR", str(data / "outputs"))
    monkeypatch.setenv("LAVS_UPLOAD_DIR", str(data / "uploads"))
    monkeypatch.setenv("LAVS_LOG_DIR", str(data / "logs"))
    monkeypatch.setenv("LAVS_DB_PATH", str(data / "db" / "test.sqlite3"))
    monkeypatch.setenv("LAVS_HOST", "127.0.0.1")
    monkeypatch.setenv("LAVS_PORT", "18765")

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    application = create_app()
    with TestClient(application) as test_client:
        yield test_client

    get_settings.cache_clear()
