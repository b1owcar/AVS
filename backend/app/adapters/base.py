from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceEstimate:
    vram_mb_min: int | None = None
    vram_mb_max: int | None = None
    ram_mb_min: int | None = None
    ram_mb_max: int | None = None
    conditions: list[str] = field(default_factory=list)
    basis: str = "unverified estimate"


@dataclass
class AdapterStatus:
    model_id: str
    loaded: bool
    healthy: bool
    message: str
    cancellation_supported: bool
    implementation_status: str  # available | unimplemented | simulated


class ModelAdapter(ABC):
    model_id: str
    display_name: str
    version: str
    provider: str
    supported_tasks: list[str]
    supported_platforms: list[str]
    dependency_requirements: dict[str, Any]
    checkpoint_paths: list[str]
    model_license: str
    hardware_requirements: dict[str, Any]
    estimated_vram: dict[str, Any]
    estimated_ram: dict[str, Any]
    precision_options: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    cancellation_supported: bool = False

    def load_model(self) -> None:
        raise NotImplementedError(f"{self.model_id}: load_model not implemented")

    def unload_model(self) -> None:
        raise NotImplementedError(f"{self.model_id}: unload_model not implemented")

    def validate_environment(self) -> dict[str, Any]:
        raise NotImplementedError(f"{self.model_id}: validate_environment not implemented")

    def validate_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"{self.model_id}: validate_input not implemented")

    def estimate_resources(self, payload: dict[str, Any]) -> ResourceEstimate:
        raise NotImplementedError(f"{self.model_id}: estimate_resources not implemented")

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        raise NotImplementedError(f"{self.model_id}: execute not implemented")

    def cancel(self) -> dict[str, Any]:
        return {
            "ok": False,
            "cancellation_supported": self.cancellation_supported,
            "message": f"{self.model_id}: cancel not supported or not implemented",
        }

    def get_status(self) -> AdapterStatus:
        raise NotImplementedError(f"{self.model_id}: get_status not implemented")

    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError(f"{self.model_id}: health_check not implemented")
