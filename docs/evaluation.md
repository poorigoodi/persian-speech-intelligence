# Evaluation Methodology

This project includes evaluation **scripts and contracts**. Measured scores are written only after running against labeled data. Placeholder claims are intentionally avoided.

## ASR

Script: `evaluation/evaluate_asr.py`

Metrics:

- Word Error Rate (WER)
- Character Error Rate (CER)

Normalization for metrics uses `normalize_for_evaluation()`:

- NFC Unicode
- Arabic/Persian glyph unification
- Digit normalization
- Punctuation stripping / whitespace collapse

Prepare `sample_data/asr/manifest.jsonl`:

```json
{"id":"formal-1","category":"formal","reference":"...","hypothesis":"..."}
```

Suggested categories:

- formal Persian
- informal Persian
- noisy audio
- mixed Persian-English

## Retrieval / QA

Script: `evaluation/evaluate_retrieval.py`

Metrics:

- Recall@K
- Manual answer correctness / evidence support / refusal quality (documented review)

Prepare `sample_data/qa/retrieval_manifest.jsonl`.

Unanswerable questions must map to the Persian refusal:

`اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد.`

## Analysis

Script: `evaluation/evaluate_analysis.py`

- Extraction Precision / Recall / F1
- Manual summary review averages (consistency, coverage, unsupported claims, readability)

## LLM fine-tune (LoRA)

Script: `evaluation/evaluate_finetune.py`

- ASR polish holdout: WER / CER vs gold assistant text in `sample_data/finetune/asr_polish/eval.jsonl`
- Analysis holdout: JSON parse rate + topic/keyword F1 vs gold in `sample_data/finetune/analysis/eval.jsonl`

See [finetune_llm.md](finetune_llm.md).

## Performance

Track separately during demos:

- preprocess time
- ASR inference time
- LLM latency
- RSS / optional GPU memory

## Running

```bash
cd backend
pip install -r requirements.txt
set PYTHONPATH=.
python ../evaluation/evaluate_asr.py
python ../evaluation/evaluate_retrieval.py
python ../evaluation/evaluate_analysis.py
python ../evaluation/evaluate_finetune.py --task asr_polish
python ../evaluation/evaluate_finetune.py --task analysis
```

Outputs are written under `evaluation/results/`.
