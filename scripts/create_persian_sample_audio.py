#!/usr/bin/env python3
"""Generate a short Persian speech WAV for local / Kaggle smoke tests.

Uses edge-tts (real Persian voice). Converts MP3→WAV via FFmpeg (no pydub).
Avoid English loanwords that TTS misreads.

Usage (from repo root):
  pip install edge-tts nest-asyncio
  python scripts/create_persian_sample_audio.py
"""

from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import shutil
import subprocess
from pathlib import Path

DEMO_SCRIPT = (
    "در جلسه امروز درباره بودجه پروژه و زمان‌بندی صحبت شد. "
    "علی مسئول تهیه گزارش تا پایان هفته شد. "
    "تصمیم گرفته شد نسخه آزمایشی تا ماه آینده آماده شود. "
    "سؤال باز این است که هزینه میزبان ابری چقدر خواهد بود."
)

DEFAULT_VOICE = "fa-IR-DilaraNeural"
DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "sample_data" / "audio" / "example.wav"
)


def run_async(coro):
    """Safe for both CLI and Jupyter (running event loop)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


async def _tts_to_mp3(text: str, mp3_path: Path, voice: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice=voice).save(str(mp3_path))


def _ffmpeg_mp3_to_wav(mp3_path: Path, wav_path: Path, sample_rate: int = 16000) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg, then re-run this script."
        )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(mp3_path),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            str(wav_path),
        ],
        check=True,
        capture_output=True,
    )


def synthesize_wav(
    out_path: Path,
    text: str = DEMO_SCRIPT,
    voice: str = DEFAULT_VOICE,
    sample_rate: int = 16000,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mp3_path = out_path.with_suffix(".mp3")
    run_async(_tts_to_mp3(text, mp3_path, voice))
    _ffmpeg_mp3_to_wav(mp3_path, out_path, sample_rate=sample_rate)
    mp3_path.unlink(missing_ok=True)
    return out_path


def write_tone_wav(path: Path, seconds: float = 1.5, freq: float = 440.0) -> Path:
    """Legacy beep fixture (not speech) — only for non-ASR smoke tests."""
    import math
    import struct
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    rate = 16000
    n = int(rate * seconds)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            value = int(16000 * math.sin(2 * math.pi * freq * (i / rate)))
            frames.extend(struct.pack("<h", value))
        wf.writeframes(frames)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Persian sample audio")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--text", default=DEMO_SCRIPT)
    parser.add_argument(
        "--tone",
        action="store_true",
        help="Write a beep WAV instead of Persian TTS (legacy smoke only)",
    )
    args = parser.parse_args()

    if args.tone:
        path = write_tone_wav(args.output)
        print(f"Wrote tone fixture (not speech): {path}")
        return

    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        pass

    path = synthesize_wav(args.output, text=args.text, voice=args.voice)
    print(f"Wrote Persian TTS sample: {path}")
    print(f"Voice: {args.voice}")
    print(f"Script: {args.text}")


if __name__ == "__main__":
    main()
