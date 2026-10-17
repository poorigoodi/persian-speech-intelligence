# Persian STT (ASR)

## Current default

| Item | Value |
|------|--------|
| Model | `oi-uae/farsi-faster-whisper-large-v3` |
| Base | Fine-tune of Whisper large-v3 on Common Voice FA (CTranslate2 / faster-whisper) |
| Device | `cuda` + `float16` (fallback CPU `int8`) |
| Language | forced `fa` |
| Beam | 8 |
| `condition_on_previous_text` | `false` (reduces cascading errors on short clips) |
| Prompt / hotwords | domain Persian + tech terms (هوش مصنوعی, AI, …) |
| Post-process | rule cleanup + optional LLM polish (`ASR_LLM_POLISH=true`) |

Stock Whisper `medium` is noticeably weaker on Persian tech speech (e.g. «هوش مصنوعی» → «حوشمسنوی»). Prefer the Farsi fine-tune.

## Stronger options (no training)

Set in `.env`:

```env
# Best default for this project
WHISPER_MODEL=oi-uae/farsi-faster-whisper-large-v3

# Alternatives (HF / CT2 ids)
# WHISPER_MODEL=farbodbij/whisper-large-v3-Persian
# WHISPER_MODEL=large-v3

WHISPER_BEAM_SIZE=8
WHISPER_CONDITION_ON_PREVIOUS_TEXT=false
WHISPER_INITIAL_PROMPT=متن به زبان فارسی است. واژه‌های رایج: هوش مصنوعی، یادگیری ماشین، داده‌کاوی، شبکه عصبی، پردازش زبان طبیعی، AI.
WHISPER_HOTWORDS=هوش مصنوعی AI یادگیری ماشین داده‌کاوی
ASR_LLM_POLISH=true
```

Add domain terms you care about to `WHISPER_HOTWORDS` / `WHISPER_INITIAL_PROMPT`.

## When to fine-tune

Fine-tune if you have **hours** of labeled Persian audio in your domain (meetings, product names, accents). Otherwise the public Farsi large-v3 + prompt/hotwords/polish is usually enough.

### Recommended path

1. Collect pairs: `audio.wav` + reference transcript (Common Voice style or your own).
2. Fine-tune `openai/whisper-large-v3` (or medium) with Hugging Face `transformers` / `seq2seq` trainer on Persian data (see [whisper-large-v3-farsi-cv17](https://huggingface.co/mohammadjavadnasri/whisper-large-v3-farsi-cv17) for a reference recipe).
3. Convert to CTranslate2 for faster-whisper:

```bash
ct2-transformers-converter \
  --model path/to/your-finetune \
  --output_dir path/to/ct2-model \
  --quantization float16 \
  --copy_files tokenizer.json preprocessor_config.json
```

4. Point the app at your local CT2 folder:

```env
WHISPER_MODEL=/absolute/path/to/ct2-model
```

### Data tips for better Persian tech ASR

- Prefer clean 16 kHz mono recordings.
- Include target vocabulary in training text (هوش مصنوعی, نام محصول، …).
- Mix formal + colloquial (می‌خوام / می‌خواهم).
- Keep a held-out test set; measure WER/CER with `evaluation/evaluate_asr.py`.

## Evaluating ASR

```bash
# see docs/evaluation.md and evaluation/evaluate_asr.py
```

Place labeled pairs in `sample_data/asr/manifest.jsonl` when ready.
