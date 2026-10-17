# LLM LoRA training (ASR polish + analysis)

See [docs/finetune_llm.md](../docs/finetune_llm.md) for the full workflow.

Quick start:

```bash
pip install -r training/requirements-train.txt

# Validate data
python scripts/validate_finetune_jsonl.py --all

# Train adapters
python training/train_lora.py --task asr_polish
python training/train_lora.py --task analysis

# Merge for local OpenAI-compatible servers
python training/merge_lora.py \
  --adapter storage/models/lora_asr_polish \
  --output storage/models/merged_asr_polish

python training/merge_lora.py \
  --adapter storage/models/lora_analysis \
  --output storage/models/merged_analysis
```
