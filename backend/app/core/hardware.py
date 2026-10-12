from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import psutil

CompatLevel = Literal["verified", "conditional", "unverified", "unsupported"]


@dataclass
class GpuInfo:
    available: bool
    name: str | None = None
    memory_total_mb: int | None = None
    memory_free_mb: int | None = None
    driver_version: str | None = None
    cuda_available: bool | None = None
    source: str = "none"
    notes: list[str] = field(default_factory=list)
    compatibility: CompatLevel = "unverified"


@dataclass
class SystemInfo:
    os_name: str
    os_release: str
    architecture: str
    python_version: str
    cpu_count: int
    ram_total_mb: int
    ram_available_mb: int
    disk_total_gb: float
    disk_free_gb: float
    ffmpeg_available: bool
    ffmpeg_path: str | None
    gpu: GpuInfo
    run_mode: str
    degraded: bool
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def _probe_nvidia_smi() -> GpuInfo:
    if shutil.which("nvidia-smi") is None:
        return GpuInfo(
            available=False,
            source="nvidia-smi-missing",
            notes=["nvidia-smi not found. GPU probe degraded."],
            compatibility="unverified",
        )

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        )
        line = result.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        name, total, free, driver = parts[0], parts[1], parts[2], parts[3]
        return GpuInfo(
            available=True,
            name=name,
            memory_total_mb=int(float(total)),
            memory_free_mb=int(float(free)),
            driver_version=driver,
            cuda_available=None,
            source="nvidia-smi",
            notes=[
                "GPU values measured via nvidia-smi on this machine.",
                "PyTorch CUDA availability not probed (large frameworks not installed in remote-dev mode).",
            ],
            compatibility="unverified",
        )
    except Exception as exc:  # noqa: BLE001 — probe must never crash app
        return GpuInfo(
            available=False,
            source="nvidia-smi-error",
            notes=[f"nvidia-smi probe failed: {exc}"],
            compatibility="unverified",
        )


def collect_system_info(run_mode: str, data_dir_for_disk: str | None = None) -> SystemInfo:
    messages: list[str] = []
    degraded = False

    disk_path = data_dir_for_disk or "/"
    try:
        usage = psutil.disk_usage(disk_path)
        disk_total_gb = round(usage.total / (1024**3), 2)
        disk_free_gb = round(usage.free / (1024**3), 2)
    except Exception as exc:  # noqa: BLE001
        degraded = True
        disk_total_gb = 0.0
        disk_free_gb = 0.0
        messages.append(f"Disk probe failed: {exc}")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        degraded = True
        messages.append("FFmpeg not found — video preprocess will be unavailable until installed.")

    gpu = _probe_nvidia_smi()
    if not gpu.available:
        degraded = True
        messages.append("No usable NVIDIA GPU probe result — entering degraded mode for inference.")

    if run_mode == "simulation":
        messages.append(
            "Run mode is simulation. Mock adapters may run; results are Demo / Simulation Mode only."
        )

    vm = psutil.virtual_memory()
    return SystemInfo(
        os_name=platform.system(),
        os_release=platform.release(),
        architecture=platform.machine(),
        python_version=sys.version.split()[0],
        cpu_count=psutil.cpu_count(logical=True) or 0,
        ram_total_mb=int(vm.total / (1024**2)),
        ram_available_mb=int(vm.available / (1024**2)),
        disk_total_gb=disk_total_gb,
        disk_free_gb=disk_free_gb,
        ffmpeg_available=bool(ffmpeg_path),
        ffmpeg_path=ffmpeg_path,
        gpu=gpu,
        run_mode=run_mode,
        degraded=degraded,
        messages=messages,
    )
