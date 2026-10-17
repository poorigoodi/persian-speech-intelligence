# Architecture

## Overview

Persian Speech Intelligence turns Persian audio into searchable transcripts and grounded analytical insights.

```
User (Streamlit / Tk test client)
        |
        | HTTP
        v
FastAPI (API Layer)
        |
        +-- Validation & storage
        |
        v
PostgreSQL or SQLite (jobs/recordings)
        |
        v
Background Worker
        |
        +--> Audio preprocess (FFmpeg)
        +--> ASR (Farsi Faster-Whisper large-v3, GPU) + rule/LLM polish
        +--> Normalization
        +--> Embeddings (multilingual-e5-small, CPU) + FAISS (CPU)
        +--> Combined LLM analysis — Qwen3-2B JSON (summary/topics/entities/sentiment)
        +--> Optional 2nd call — Qwen3-4B sentiment (SENTIMENT_USE_SEPARATE_MODEL)
        |
        v
DB + per-recording vector indexes
        |
        v
FastAPI read/chat/export endpoints
```

## Model placement

| بخش | مدل | محل اجرا |
|---|---|---|
| Speech-to-Text | Farsi Faster-Whisper large-v3 | GPU |
| LLM (analysis / QA) | Qwen3-2B-Instruct-2507 (Q4) or fine-tuned LoRA merge | GPU |
| LLM (ASR polish) | same server; optional `ASR_POLISH_MODEL` LoRA | GPU |
| Embedding | multilingual-e5-small | CPU |
| Reranker | — | not used |
| Sentiment | included in combined call; optional Qwen3-4B | GPU |
| Vector Search | FAISS | CPU |
| Database | PostgreSQL (prod) / SQLite (local demo) | CPU |

## Layers

| Layer | Responsibility |
|-------|----------------|
| API | FastAPI routers, auth gate, OpenAPI, request validation |
| Business services | Audio, transcription, analysis orchestration, QA, export |
| Speech | FFmpeg validation/conversion, Whisper model manager |
| NLP / LLM | Provider abstraction, combined JSON analysis, structured parsing |
| Retrieval | Chunking, embeddings, FAISS, recording-isolated search |
| Database | SQLAlchemy models, repositories, Alembic migrations |
| Workers | DB-backed job polling, progress steps, retries, stale recovery |
| Frontend | Streamlit dashboard (no core AI logic) |

## Key design decisions

1. **DB-backed worker instead of Celery** — simpler local deployment, restart-safe jobs.
2. **Per-recording FAISS indexes** — retrieval isolation without multi-tenant vector ACL complexity.
3. **OpenAI-compatible LLM adapter** — Ollama / llama.cpp / vLLM / LM Studio.
4. **One combined analysis LLM call** — summary + topics + entities + sentiment in a single JSON request to avoid timeout on slow local GPUs. Optional second call for Qwen3-4B sentiment (`SENTIMENT_USE_SEPARATE_MODEL=true`). Optional separate LoRA model ids for polish vs analysis (`ASR_POLISH_MODEL` / `LOCAL_LLM_MODEL`) — see [finetune_llm.md](finetune_llm.md).
5. **Original + normalized transcripts** — preserves ASR fidelity while improving Persian text consistency.
6. **No fabricated analytics** — empty lists when decisions/actions are absent; explicit Persian refusal for unanswerable QA.
7. **No reranker** — embedding + FAISS top-k only for MVP.
8. **Paced LLM I/O** — connect timeout fails fast; long read timeout; optional pause between calls; transcript clipped for analysis.

## Data flow for one recording

1. Upload validated by extension, size, duration, and FFmpeg probe.
2. Recording + pending job rows created.
3. Worker claims job (`SKIP LOCKED` on PostgreSQL; SQLite uses a simpler claim).
4. Audio converted to mono 16 kHz WAV.
5. Whisper produces timestamped segments.
6. Segments stored; embeddings indexed under `recording_id`.
7. Combined LLM analysis persisted as JSON fields (progress: `analyze_prepare` → `analyze_combined` → …).
8. Clients poll status and fetch transcript/analysis/chat/export.

## Repository layout

```
persian-speech-intelligence/
  backend/           # FastAPI app, worker, tests
  frontend/          # Streamlit UI
  scripts/           # utilities + Tk test client
  sample_data/       # fixtures / manifests
  evaluation/        # ASR / retrieval / analysis eval
  docs/              # architecture, API, evaluation
  storage/           # runtime uploads / indexes (gitignored contents)
```

## Privacy notes

- Uploaded files are stored outside public static serving paths.
- Full transcripts are not logged by default.
- LLM endpoints receive transcript text required for analysis/QA only.
- Deleting a recording removes DB rows, audio file, temp files, and vector index files.
