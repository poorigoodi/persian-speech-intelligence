# Persian Speech Intelligence

AI-powered Persian speech analysis and conversational intelligence platform.

Upload Persian audio (meetings, interviews, lectures, support calls). The system transcribes speech, generates summaries, extracts structured information, analyzes transcript sentiment, and answers grounded questions over the recording.

This repository is designed as a **portfolio-ready AI engineering project**: modular architecture, asynchronous processing, evaluation scripts, Docker deployment, tests, and clear documentation.

## Main features

- Persian ASR with **faster-whisper** (timestamped segments)
- Persian-aware transcript normalization
- Short + detailed LLM summarization
- Topic detection, action items, decisions, entity extraction
- Transcript-based sentiment analysis (not acoustic emotion recognition)
- Retrieval-augmented Q&A with **recording-level isolation**
- Streamlit dashboard with RTL-friendly Persian UI
- FastAPI + PostgreSQL + DB-backed worker
- Docker Compose one-command local stack
- Automated tests and evaluation harnesses

## Architecture

```
Upload → FastAPI → Storage + Job row → Worker
                                       ├─ FFmpeg preprocess
                                       ├─ Whisper ASR
                                       ├─ Embeddings + FAISS
                                       └─ LLM analysis
Read/Chat/Export ← FastAPI ← PostgreSQL + vector indexes ← Streamlit
```

See [docs/architecture.md](docs/architecture.md) for details.

## Technology stack

| Area | Technology |
|------|------------|
| API | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| DB | PostgreSQL, SQLAlchemy 2, Alembic |
| ASR | faster-whisper, FFmpeg |
| NLP/LLM | OpenAI-compatible + local adapters |
| Retrieval | sentence-transformers, FAISS |
| Frontend | Streamlit |
| Ops | Docker Compose, GitHub Actions, pytest, Ruff |

## Model defaults

| Component | Default | Notes |
|-----------|---------|-------|
| Whisper | `small` | Configurable; CPU `int8` by default |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | Multilingual / Persian-capable |
| LLM | `gpt-4o-mini` via OpenAI-compatible API | Or local Ollama-compatible server |

## Requirements

- Docker + Docker Compose **or**
- Python 3.12, PostgreSQL 16, FFmpeg
- LLM API key **or** a local OpenAI-compatible endpoint for analysis/QA

ASR can run on CPU. GPU (`WHISPER_DEVICE=cuda`) is optional.

## Quick start (Docker)

```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY (or switch LLM_PROVIDER=local)

docker compose up --build
```

Services:

- API: http://localhost:8000/docs
- UI: http://localhost:8501
- Postgres: localhost:5432

First Whisper/embedding downloads may take several minutes.

## Local development setup

```bash
cp .env.example .env

# Database
docker compose up -d db

# Backend
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
python -m app.workers.processing_worker

# Frontend (separate terminal)
cd ../frontend
pip install -r requirements.txt
set BACKEND_URL=http://localhost:8000
streamlit run app.py
```

## Environment configuration

Copy `.env.example` → `.env`. Important variables:

```env
DATABASE_URL=postgresql+psycopg://psi:psi_secret@localhost:5432/persian_speech
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-your-api-key-here
```

For local LLMs:

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3.2
```

## Usage examples

### Upload (Persian meeting audio)

```bash
curl -X POST "http://localhost:8000/api/v1/recordings" \
  -F "file=@./sample_data/audio/example.wav"
```

### Ask a grounded question

```bash
curl -X POST "http://localhost:8000/api/v1/recordings/<ID>/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"جلسه درباره چه موضوعی بود؟\"}"
```

Example Persian questions:

- جلسه درباره چه موضوعی بود؟
- چه تصمیم‌هایی گرفته شد؟
- چه کسی مسئول انجام کار شد؟
- مهلت انجام پروژه چه زمانی است؟

If evidence is missing, the API returns:

> اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد.

## API documentation

- OpenAPI UI: `/docs`
- Written reference: [docs/api.md](docs/api.md)

## Evaluation

Scripts live in `evaluation/`:

- `evaluate_asr.py` — WER / CER
- `evaluate_retrieval.py` — Recall@K
- `evaluate_analysis.py` — extraction F1 + summary review averages

Labeled datasets are optional. Without them, scripts report `status: pending` and do **not** invent scores.

See [docs/evaluation.md](docs/evaluation.md).

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

CI runs lint + unit tests without paid API calls (LLM responses are mocked / unused in unit tests).

## Security and privacy

- Audio stored under configurable private storage directories
- No unrestricted static file serving of uploads
- Secrets via environment variables only
- Optional `X-API-Key` gate (`AUTH_ENABLED=true`)
- Recording deletion removes audio, transcript, analysis, and vector index
- Transcript text sent to external LLM providers only for configured analysis/QA steps — document this for production deployments

## Limitations

- Whisper quality varies for noisy / highly informal Persian and heavy code-switching
- LLM analysis can miss nuances or over-generalize; empty lists are preferred over invented decisions
- Sentiment is **text-based**, not acoustic emotion recognition
- Default stack is single-node; not a multi-tenant SaaS
- Speaker diarization and realtime streaming are out of MVP scope

## Screenshots

> Placeholder: add UI screenshots under `docs/images/` (dashboard, transcript viewer, Ask AI) after running the app locally.

## Future improvements

- Speaker diarization
- Streaming transcription
- Stronger Persian embedding models
- Optional Celery/Redis for higher throughput
- Multi-user auth and audit logs
- Expanded labeled evaluation corpora

## License

MIT — see [LICENSE](LICENSE).
