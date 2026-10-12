"""Create a short synthetic WAV fixture for smoke tests (not Persian speech)."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def write_tone_wav(path: Path, seconds: float = 1.0, freq: float = 440.0) -> None:
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


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "sample_data" / "audio" / "example.wav"
    write_tone_wav(out, seconds=1.5)
    print(f"Wrote {out}")
