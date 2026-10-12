# Architecture

## Overview

Persian Speech Intelligence is a modular AI application that turns Persian audio into searchable transcripts and grounded analytical insights.

```
User (Streamlit)
        |
        | HTTP
        v
FastAPI (API Layer)
        |
        +-- Validation & storage
        |
        v
PostgreSQL (jobs/recordings)
        |
        v
Background Worker
        |
        +--> Audio preprocess (FFmpeg)
        +--> ASR (faster-whisper)
        +--> Normalization
        +--> Embeddings + FAISS index
        +--> LLM analysis (summary/topics/sentiment/extraction)
        |
        v
PostgreSQL + Vector indexes
        |
        v
FastAPI read/chat/export endpoints
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API | FastAPI routers, auth gate, OpenAPI, request validation |
| Business services | Audio, transcription, analysis orchestration, QA, export |
| Speech | FFmpeg validation/conversion, Whisper model manager |
| NLP / LLM | Provider abstraction, structured output parsing |
| Retrieval | Chunking, embeddings, FAISS, recording-isolated search |
| Database | SQLAlchemy models, repositories, Alembic migrations |
| Workers | DB-backed job polling, progress, retries, stale recovery |
| Frontend | Streamlit dashboard (no core AI logic) |

## Key design decisions

1. **DB-backed worker instead of Celery** — simpler local deployment, restart-safe jobs, enough for MVP concurrency.
2. **Per-recording FAISS indexes** — enforces retrieval isolation without multi-tenant vector ACL complexity.
3. **OpenAI-compatible LLM adapter** — works with hosted APIs and local servers (e.g. Ollama).
4. **Original + normalized transcripts** — preserves ASR fidelity while improving Persian text consistency.
5. **No fabricated analytics** — empty lists when decisions/actions are absent; explicit Persian refusal for unanswerable QA.

## Data flow for one recording

1. Upload validated by extension, size, duration, and FFmpeg probe.
2. Recording + pending job rows created.
3. Worker claims job (`SKIP LOCKED` on PostgreSQL).
4. Audio converted to mono 16 kHz WAV.
5. Whisper produces timestamped segments.
6. Segments stored; embeddings indexed under `recording_id`.
7. LLM analysis persisted as JSON fields.
8. Clients poll status and fetch transcript/analysis/chat/export.

## Privacy notes

- Uploaded files are stored outside public static serving paths.
- Full transcripts are not logged by default.
- External LLM providers receive transcript text required for analysis/QA only.
- Deleting a recording removes DB rows, audio file, temp files, and vector index files.
