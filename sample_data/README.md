# Sample data

Demonstration assets for local smoke tests and evaluation.

## Layout

```
sample_data/
  audio/                 # Persian WAV fixtures
    example.wav          # generated via scripts/create_persian_sample_audio.py
  asr/manifest.jsonl     # ASR evaluation pairs (optional)
  qa/retrieval_manifest.jsonl
  analysis/extraction_manifest.jsonl
  analysis/summary_review.jsonl
```

## Generate Persian demo audio

```bash
pip install edge-tts nest-asyncio
# FFmpeg must be on PATH (already required by the main app)
python scripts/create_persian_sample_audio.py
```

Output: `sample_data/audio/example.wav` (~15–20s Persian speech).

Voices: `fa-IR-DilaraNeural` (default) or `fa-IR-FaridNeural`.

Avoid English loanwords in TTS scripts (e.g. use «میزبان ابری» instead of «سرور»).

Legacy beep-only fixture (not useful for ASR quality):

```bash
python scripts/create_persian_sample_audio.py --tone
```

Do not commit sensitive real-world recordings. Prefer synthetic TTS or consented samples.
