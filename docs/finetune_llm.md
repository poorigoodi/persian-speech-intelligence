# Fine-tune LLM (two LoRA adapters)

Train separate adapters for:

1. **ASR polish** — garbled Persian transcript → corrected text  
2. **Analysis** — transcript → `short_summary` / topics / entities JSON  

Base model default: `Qwen/Qwen2.5-3B-Instruct` (same family as the GPU notebooks).  
Runtime still talks to an OpenAI-compatible server (`LOCAL_LLM_BASE_URL`); after merge, register two model ids.

## Data

Layout:

```
sample_data/finetune/
  asr_polish/train.jsonl
  asr_polish/eval.jsonl
  analysis/train.jsonl
  analysis/eval.jsonl
```

Each line is chat JSON (`system` + `user` + `assistant`).  
Use production prompts from `ASR_POLISH_SYSTEM` and `COMBINED_SYSTEM_PROMPT`.  
Analysis assistant text must parse as `CombinedAnalysisPayload`.

Validate:

```bash
python scripts/validate_finetune_jsonl.py --all
```

Aim for ~200+ polish pairs and ~150+ analysis pairs (keep ~20% in `eval.jsonl`).

## Train

```bash
pip install -r training/requirements-train.txt

python training/train_lora.py --task asr_polish
python training/train_lora.py --task analysis
```

Outputs:

- `storage/models/lora_asr_polish/`
- `storage/models/lora_analysis/`

Smoke run:

```bash
python training/train_lora.py --task asr_polish --max-steps 5
```

## Merge + serve

```bash
python training/merge_lora.py \
  --adapter storage/models/lora_asr_polish \
  --output storage/models/merged_asr_polish

python training/merge_lora.py \
  --adapter storage/models/lora_analysis \
  --output storage/models/merged_analysis
```

Load both merged folders in Ollama / vLLM / LM Studio (or any OpenAI-compatible host) as e.g. `psi-asr-polish` and `psi-analysis`.

## Wire into the app

`.env`:

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
# Analysis + QA
LOCAL_LLM_MODEL=psi-analysis
LLM_MODEL=psi-analysis
# Dedicated polish adapter (optional; empty = same as LOCAL_LLM_MODEL)
ASR_POLISH_MODEL=psi-asr-polish
ASR_LLM_POLISH=true
```

`get_asr_polish_llm_provider()` uses `ASR_POLISH_MODEL`; `AnalysisPipeline` keeps `get_llm_provider()`.

## Evaluate

```bash
# Offline: score a predictions file {id, prediction}
python evaluation/evaluate_finetune.py --task asr_polish --predictions path/to/preds.jsonl
python evaluation/evaluate_finetune.py --task analysis --predictions path/to/preds.jsonl

# Or generate with adapter on GPU
python evaluation/evaluate_finetune.py --task asr_polish \
  --adapter storage/models/lora_asr_polish
python evaluation/evaluate_finetune.py --task analysis \
  --adapter storage/models/lora_analysis
```

Metrics land in `evaluation/results/finetune_*.json`.

## Notebooks

Set env before running E2E / LLM notebooks:

```bash
set MERGED_LLM_DIR=E:\persian-speech-intelligence\storage\models\merged_analysis
set MERGED_POLISH_DIR=E:\persian-speech-intelligence\storage\models\merged_asr_polish
```

Or `LLM_MODEL_ID` / `LORA_ANALYSIS_DIR` as documented in `notebooks/README.md`.

## Out of scope

Whisper audio fine-tune is separate — see [asr.md](asr.md).
