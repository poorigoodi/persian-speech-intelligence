#!/usr/bin/env python3
"""Backward-compatible entrypoint — prefer create_persian_sample_audio.py."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).with_name("create_persian_sample_audio.py")),
        run_name="__main__",
    )
