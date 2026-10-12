from __future__ import annotations

from pathlib import Path

import pytest

from app.services.path_safety import UnsafePathError, resolve_under, safe_filename


def test_resolve_under_blocks_traversal(tmp_path: Path):
    root = tmp_path / "uploads"
    root.mkdir()
    ok = resolve_under(root, "a/b.txt")
    assert str(ok).startswith(str(root.resolve()))

    with pytest.raises(UnsafePathError):
        resolve_under(root, "../outside.txt")


def test_safe_filename():
    assert safe_filename("foo/bar.png") == "bar.png"
    with pytest.raises(UnsafePathError):
        safe_filename("..")
