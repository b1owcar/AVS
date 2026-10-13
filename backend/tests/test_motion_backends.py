from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.motion_adapter import MotionTransferAdapter
from app.core.config import Settings


def test_motion_readme_alone_not_ready(tmp_path: Path):
    model_dir = tmp_path / "models"
    weights = model_dir / "motion-transfer"
    weights.mkdir(parents=True)
    (weights / "README.txt").write_text("docs only\n", encoding="utf-8")
    py = tmp_path / "fake_python"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    py.chmod(0o755)

    settings = Settings(
        model_dir=model_dir,
        motion_python=py,
        data_dir=tmp_path / "data",
    )
    env = MotionTransferAdapter(settings).validate_environment()
    assert env["ok"] is False
    assert env["backend"] is None
    assert any("run_transfer" in i or "backend.json" in i for i in env["issues"])


def test_motion_run_transfer_marks_ready(tmp_path: Path):
    model_dir = tmp_path / "models"
    weights = model_dir / "motion-transfer"
    weights.mkdir(parents=True)
    (weights / "run_transfer.py").write_text(
        "def run_transfer(payload):\n    return {'ok': True, 'output_files': ['x']}\n",
        encoding="utf-8",
    )
    py = tmp_path / "fake_python"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    py.chmod(0o755)
    settings = Settings(model_dir=model_dir, motion_python=py, data_dir=tmp_path / "data")
    env = MotionTransferAdapter(settings).validate_environment()
    assert env["ok"] is True
    assert env["backend"] == "external_script"


def test_worker_external_script_succeeds(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    worker = root / "envs" / "motion" / "worker_transfer.py"
    weights = tmp_path / "weights"
    weights.mkdir()
    (weights / "run_transfer.py").write_text(
        "from pathlib import Path\n"
        "def run_transfer(payload):\n"
        "    out = Path(payload['output_dir']) / 'marker.txt'\n"
        "    out.write_text('ok', encoding='utf-8')\n"
        "    return {'ok': True, 'output_files': [str(out)], 'message': 'test backend'}\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    req = tmp_path / "req.json"
    resp = tmp_path / "resp.json"
    pose = tmp_path / "pose.json"
    target = tmp_path / "t.png"
    pose.write_text("{}", encoding="utf-8")
    target.write_bytes(b"\x89PNG\r\n\x1a\n")
    req.write_text(
        json.dumps(
            {
                "pose_json_path": str(pose),
                "target_image_path": str(target),
                "output_dir": str(out_dir),
                "weights_dir": str(weights),
            }
        ),
        encoding="utf-8",
    )
    code = subprocess.call(
        [sys.executable, str(worker), "--request", str(req), "--response", str(resp)],
    )
    assert code == 0
    data = json.loads(resp.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["output_files"]
    assert Path(data["output_files"][0]).exists()


def test_trellis_runner_shipped():
    root = Path(__file__).resolve().parents[2]
    runner = root / "envs" / "trellis" / "trellis_runner.py"
    assert runner.exists()
    text = runner.read_text(encoding="utf-8")
    assert "TrellisImageTo3DPipeline" in text
    assert "run_image_to_3d" in text
