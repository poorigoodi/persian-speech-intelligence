"""Safe filename utility tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.files import generate_storage_filename, resolve_under_directory, sanitize_filename


def test_sanitize_strips_path_components() -> None:
    assert ".." not in sanitize_filename("../etc/passwd.wav")
    assert Path(sanitize_filename("a/b/c.mp3")).name.endswith(".mp3")


def test_generate_storage_filename_uses_uuid_prefix() -> None:
    name = generate_storage_filename("meeting.wav")
    assert name.endswith(".wav")
    assert "_" in name


def test_path_traversal_blocked(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_under_directory(tmp_path, "../outside.txt")
