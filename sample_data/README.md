# Sample data

Demonstration assets for local smoke tests and evaluation.

## Layout

```
sample_data/
  audio/                 # your Persian WAV/MP3/M4A recordings
    example.wav          # optional smoke tone (not speech)
    demo_script.txt      # example transcript text for evaluation
  asr/manifest.jsonl
  qa/retrieval_manifest.jsonl
  analysis/extraction_manifest.jsonl
  analysis/summary_review.jsonl
  finetune/              # LoRA chat JSONL (asr_polish + analysis)
    asr_polish/{train,eval}.jsonl
    analysis/{train,eval}.jsonl
```

See `finetune/README.md` and `docs/finetune_llm.md`.

## Audio for ASR tests

This repo does **not** include a TTS pipeline. For meaningful STT tests:

1. Record a short Persian clip with your own voice, or
2. Place consented/synthetic Persian speech under `sample_data/audio/`

Optional beep fixture (pipeline smoke only — useless for ASR quality):

```bash
python scripts/create_persian_sample_audio.py
```

Do not commit sensitive real-world recordings without consent.
