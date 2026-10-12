from __future__ import annotations

from pathlib import Path


class UnsafePathError(ValueError):
    pass


def resolve_under(root: Path, user_path: str | Path) -> Path:
    """Resolve user_path and ensure it stays under root (no path traversal)."""
    root_resolved = root.resolve()
    candidate = Path(user_path)
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise UnsafePathError(
            f"Path escapes allowed root: {resolved} not under {root_resolved}"
        ) from exc
    return resolved


def safe_filename(name: str) -> str:
    cleaned = name.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.strip().replace("..", "")
    if not cleaned or cleaned in {".", ".."}:
        raise UnsafePathError("Invalid filename")
    return cleaned
