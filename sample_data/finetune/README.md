# Fine-tune datasets (LoRA)

Chat-format JSONL for two adapters on the same Qwen base:

| Task | Path | Goal |
|------|------|------|
| ASR polish | `asr_polish/{train,eval}.jsonl` | Garbled transcript → corrected text |
| Analysis | `analysis/{train,eval}.jsonl` | Transcript → summary / topics JSON |

## Row format

Each line is one object:

```json
{"id": "p1", "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

- **system** — use the same prompts as production (`ASR_POLISH_SYSTEM` / `COMBINED_SYSTEM_PROMPT`).
- **assistant** (analysis) — valid JSON matching `CombinedAnalysisPayload`.

Validate:

```bash
cd backend
set PYTHONPATH=.
python ../scripts/validate_finetune_jsonl.py --task asr_polish --path ../sample_data/finetune/asr_polish/train.jsonl
python ../scripts/validate_finetune_jsonl.py --task analysis --path ../sample_data/finetune/analysis/train.jsonl
```

Example rows in this folder are tiny smoke fixtures; replace with your labeled pairs before training.
