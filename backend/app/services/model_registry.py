from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ModelRecord


SEED_MODELS: list[dict[str, Any]] = [
    {
        "id": "mock-demo",
        "display_name": "Mock Demo Image Adapter",
        "version": "0.1.0",
        "provider": "local-mock",
        "supported_tasks": ["text_to_image", "demo"],
        "supported_platforms": ["windows", "linux"],
        "dependency_requirements": {"pillow": "required"},
        "checkpoint_paths": [],
        "model_license": "N/A",
        "hardware_requirements": {"gpu": "not required"},
        "estimated_vram": {"min_mb": 0, "max_mb": 0, "basis": "simulation"},
        "estimated_ram": {"min_mb": 64, "max_mb": 256, "basis": "simulation"},
        "precision_options": ["n/a"],
        "download_url": None,
        "download_size_hint": "0",
        "environment_status": "ready",
        "download_status": "not_required",
        "verification_status": "simulated",
        "availability": "available_simulation",
        "notes": "Demo / Simulation Mode only. Not real AI inference.",
    },
    {
        "id": "sdxl-base-1.0",
        "display_name": "Stable Diffusion XL Base 1.0",
        "version": "1.0",
        "provider": "stabilityai / huggingface-diffusers",
        "supported_tasks": ["text_to_image", "image_to_image", "inpainting"],
        "supported_platforms": ["windows", "linux"],
        "dependency_requirements": {
            "env": "env-image",
            "packages": ["torch", "diffusers", "transformers", "accelerate"],
            "official_docs": "https://huggingface.co/docs/diffusers/en/api/pipelines/stable_diffusion/stable_diffusion_xl",
        },
        "checkpoint_paths": [],
        "model_license": "CreativeML Open RAIL++-M (confirm on model card)",
        "hardware_requirements": {
            "gpu": "NVIDIA CUDA",
            "recommended_precision": "fp16",
            "batch_size": 1,
            "compat": "conditional",
        },
        "estimated_vram": {
            "min_mb": 6000,
            "max_mb": 12000,
            "conditions": ["fp16", "1024 or lower", "batch=1"],
            "basis": "community/docs heuristic — PENDING TARGET HARDWARE",
        },
        "estimated_ram": {"min_mb": 8000, "max_mb": 16000, "basis": "unverified"},
        "precision_options": ["fp16", "bf16"],
        "download_url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
        "download_size_hint": "~6–7 GB weights (approx; verify before download)",
        "environment_status": "not_installed",
        "download_status": "not_downloaded",
        "verification_status": "unverified",
        "availability": "unavailable",
        "notes": "Do not download in remote-dev mode. First real model candidate for Phase 2 on target PC.",
    },
    {
        "id": "wan2.1-t2v-1.3b",
        "display_name": "Wan 2.1 T2V 1.3B",
        "version": "2.1",
        "provider": "Wan-AI / Comfy-Org repackage",
        "supported_tasks": ["text_to_video"],
        "supported_platforms": ["windows", "linux"],
        "dependency_requirements": {
            "preferred": "ComfyUI workflow",
            "official_model": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B",
            "comfy_repack": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged",
            "docs": "https://docs.comfy.org/tutorials/video/wan/wan-video",
        },
        "checkpoint_paths": [],
        "model_license": "Apache-2.0 (per official project statements; re-confirm)",
        "hardware_requirements": {
            "gpu": "NVIDIA CUDA",
            "official_note": "Lightweight path advertised around ~8GB VRAM",
            "compat": "conditional",
        },
        "estimated_vram": {
            "min_mb": 8000,
            "max_mb": None,
            "basis": "official/community claims — PENDING TARGET HARDWARE",
        },
        "estimated_ram": {"status": "unverified"},
        "precision_options": ["fp16", "bf16"],
        "download_url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B",
        "download_size_hint": "Multi-file (diffusion + CLIP/VAE); verify before download",
        "environment_status": "not_installed",
        "download_status": "not_downloaded",
        "verification_status": "unverified",
        "availability": "unavailable",
        "notes": "Prefer ComfyUI. Do not default to Wan 14B.",
    },
    {
        "id": "wan2.1-i2v",
        "display_name": "Wan 2.1 Image-to-Video (candidate)",
        "version": "2.1",
        "provider": "Wan-AI",
        "supported_tasks": ["image_to_video"],
        "supported_platforms": ["windows", "linux"],
        "dependency_requirements": {"preferred": "ComfyUI", "note": "I2V often uses larger 14B weights"},
        "checkpoint_paths": [],
        "model_license": "see Wan-AI model card",
        "hardware_requirements": {"compat": "conditional", "risk": "higher VRAM than T2V 1.3B"},
        "estimated_vram": {"status": "unverified", "basis": "PENDING TARGET HARDWARE"},
        "estimated_ram": {"status": "unverified"},
        "precision_options": ["fp16", "fp8"],
        "download_url": "https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-480P",
        "download_size_hint": "Large (14B class) — user-triggered only",
        "environment_status": "not_installed",
        "download_status": "not_downloaded",
        "verification_status": "unverified",
        "availability": "unavailable",
        "notes": "Separate task type from T2V; incompatible parameter schemas must not be shared.",
    },
    {
        "id": "sam2.1",
        "display_name": "SAM 2.1",
        "version": "2.1",
        "provider": "facebookresearch",
        "supported_tasks": ["video_segmentation"],
        "supported_platforms": ["linux", "windows-wsl-preferred"],
        "dependency_requirements": {
            "repo": "https://github.com/facebookresearch/sam2",
            "python": ">=3.10",
            "torch": ">=2.5.1",
            "note": "Native Windows not officially preferred; WSL recommended",
        },
        "checkpoint_paths": [],
        "model_license": "Apache-2.0 (confirm)",
        "hardware_requirements": {"compat": "unverified"},
        "estimated_vram": {"status": "unverified"},
        "estimated_ram": {"status": "unverified"},
        "precision_options": ["fp16"],
        "download_url": "https://github.com/facebookresearch/sam2",
        "download_size_hint": "checkpoint-dependent",
        "environment_status": "not_installed",
        "download_status": "not_downloaded",
        "verification_status": "unverified",
        "availability": "unavailable",
        "notes": "Specialized worker env. Native Windows success must not be claimed without verification.",
    },
    {
        "id": "trellis-image-to-3d",
        "display_name": "Microsoft TRELLIS (Image to 3D)",
        "version": "upstream",
        "provider": "microsoft",
        "supported_tasks": ["image_to_3d"],
        "supported_platforms": ["linux"],
        "dependency_requirements": {
            "repo": "https://github.com/microsoft/TRELLIS",
            "official_vram": ">=16GB stated by project",
            "isolation": "env-trellis required",
        },
        "checkpoint_paths": [],
        "model_license": "see microsoft/TRELLIS repository",
        "hardware_requirements": {
            "compat": "conditional_or_unsupported",
            "official_vram_gb": 16,
            "note": "Target laptop VRAM unverified; may be insufficient",
        },
        "estimated_vram": {
            "min_mb": 16000,
            "basis": "official README — PENDING TARGET HARDWARE measurement",
        },
        "estimated_ram": {"status": "unverified"},
        "precision_options": ["fp16"],
        "download_url": "https://github.com/microsoft/TRELLIS",
        "download_size_hint": "large experimental stack",
        "environment_status": "not_installed",
        "download_status": "not_downloaded",
        "verification_status": "unverified",
        "availability": "unavailable",
        "notes": "Experimental isolated env. Video-to-3D is a separate multi-stage pipeline.",
    },
]


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def seed_models(db: Session) -> None:
    for item in SEED_MODELS:
        existing = db.get(ModelRecord, item["id"])
        payload = {
            "display_name": item["display_name"],
            "version": item["version"],
            "provider": item["provider"],
            "supported_tasks_json": _dump(item["supported_tasks"]),
            "supported_platforms_json": _dump(item["supported_platforms"]),
            "dependency_requirements_json": _dump(item["dependency_requirements"]),
            "checkpoint_paths_json": _dump(item["checkpoint_paths"]),
            "model_license": item["model_license"],
            "hardware_requirements_json": _dump(item["hardware_requirements"]),
            "estimated_vram_json": _dump(item["estimated_vram"]),
            "estimated_ram_json": _dump(item["estimated_ram"]),
            "precision_options_json": _dump(item["precision_options"]),
            "download_url": item.get("download_url"),
            "download_size_hint": item.get("download_size_hint"),
            "environment_status": item["environment_status"],
            "download_status": item["download_status"],
            "verification_status": item["verification_status"],
            "availability": item["availability"],
            "notes": item.get("notes", ""),
        }
        if existing is None:
            db.add(ModelRecord(id=item["id"], **payload))
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
    db.commit()


def serialize_model(record: ModelRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "display_name": record.display_name,
        "version": record.version,
        "provider": record.provider,
        "supported_tasks": json.loads(record.supported_tasks_json),
        "supported_platforms": json.loads(record.supported_platforms_json),
        "dependency_requirements": json.loads(record.dependency_requirements_json),
        "checkpoint_paths": json.loads(record.checkpoint_paths_json),
        "model_license": record.model_license,
        "hardware_requirements": json.loads(record.hardware_requirements_json),
        "estimated_vram": json.loads(record.estimated_vram_json),
        "estimated_ram": json.loads(record.estimated_ram_json),
        "precision_options": json.loads(record.precision_options_json),
        "download_url": record.download_url,
        "download_size_hint": record.download_size_hint,
        "environment_status": record.environment_status,
        "download_status": record.download_status,
        "verification_status": record.verification_status,
        "availability": record.availability,
        "notes": record.notes,
    }
