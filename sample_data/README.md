# Sample data

Place demonstration assets here.

## Suggested layout

```
sample_data/
  audio/                 # short Persian WAV/MP3 fixtures
  asr/manifest.jsonl     # ASR evaluation pairs
  qa/retrieval_manifest.jsonl
  analysis/extraction_manifest.jsonl
  analysis/summary_review.jsonl
```

Do not commit sensitive real-world recordings. Prefer synthetic or consented samples.

Synthetic short silence/tone files are useful for pipeline smoke tests but **do not** prove Persian ASR accuracy.
