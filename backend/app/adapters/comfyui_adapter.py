from __future__ import annotations

from typing import Any

import httpx

from app.adapters.base import AdapterStatus, ModelAdapter


class ComfyUIAdapter(ModelAdapter):
    """ComfyUI connection adapter. Does not submit real workflows until configured on target PC."""

    model_id = "comfyui-bridge"
    display_name = "ComfyUI Bridge"
    version = "0.1.0"
    provider = "comfyui"
    supported_tasks = ["comfy_workflow"]
    supported_platforms = ["windows", "linux"]
    dependency_requirements = {"comfyui": "external local service"}
    checkpoint_paths: list[str] = []
    model_license = "N/A (bridge)"
    hardware_requirements = {"delegated_to": "ComfyUI"}
    estimated_vram = {"status": "delegated"}
    estimated_ram = {"status": "delegated"}
    precision_options = ["delegated"]
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    cancellation_supported = True

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # ComfyUI exposes /system_stats when running
                resp = client.get(f"{self.base_url}/system_stats")
                if resp.status_code == 200:
                    return {
                        "ok": True,
                        "reachable": True,
                        "url": self.base_url,
                        "implementation_status": "connection_only",
                        "message": "ComfyUI reachable. Workflow execution not yet wired for production use.",
                    }
                return {
                    "ok": False,
                    "reachable": False,
                    "url": self.base_url,
                    "status_code": resp.status_code,
                    "message": "ComfyUI responded with unexpected status",
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "reachable": False,
                "url": self.base_url,
                "message": f"ComfyUI not reachable: {exc}",
                "implementation_status": "unavailable",
            }

    def get_status(self) -> AdapterStatus:
        health = self.health_check()
        return AdapterStatus(
            model_id=self.model_id,
            loaded=False,
            healthy=bool(health.get("ok")),
            message=str(health.get("message")),
            cancellation_supported=True,
            implementation_status="unimplemented"
            if not health.get("ok")
            else "connection_only",
        )

    def validate_environment(self) -> dict[str, Any]:
        return self.health_check()

    def execute(self, payload: dict[str, Any], progress_cb=None) -> dict[str, Any]:
        raise NotImplementedError(
            "ComfyUI workflow submission is scaffolded but not enabled until "
            "verified workflows are registered on the target machine."
        )
