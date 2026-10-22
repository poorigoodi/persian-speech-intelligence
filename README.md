# Persian Speech Intelligence

![Persian Speech Intelligence](persian-speech-intelligence.png)

AI-powered Persian speech analysis and conversational intelligence platform.

Upload Persian audio (meetings, interviews, lectures, support calls). The system transcribes speech, generates summaries, extracts structured information, analyzes transcript sentiment, and answers grounded questions over the recording.

Portfolio-ready AI engineering project: modular architecture, async processing, Docker, tests, and clear docs.

## Main features

- Persian ASR with **Farsi fine-tuned Faster-Whisper large-v3** + rule/LLM polish
- Persian-aware transcript normalization
- **One combined LLM analysis call** (summary + topics + entities + sentiment) via **Qwen3-2B**
- Optional separate **Qwen3-4B** sentiment (off by default — avoids GPU model swap)
- Retrieval-augmented Q&A with **recording-level isolation** (e5-small + FAISS)
- Streamlit dashboard with RTL-friendly Persian UI
- FastAPI + PostgreSQL (or SQLite demo) + DB-backed worker
- Docker Compose, pytest, Ruff

## Repository layout

```
persian-speech-intelligence/
├── backend/           # FastAPI, worker, LLM, ASR, embeddings, tests
├── frontend/          # Streamlit UI
├── scripts/           # utilities, Tk test client
├── sample_data/       # fixtures / evaluation manifests
├── evaluation/        # ASR / retrieval / analysis eval scripts
├── docs/              # architecture, API, ASR, evaluation
├── storage/           # runtime uploads & vector indexes
├── docker-compose.yml
├── requirements.txt   # meta: -r backend + frontend
└── .env.example
```

## Architecture (runtime)

```
Upload → FastAPI → Storage + Job → Worker
                                   ├─ FFmpeg preprocess
                                   ├─ Farsi Faster-Whisper large-v3 (GPU)
                                   ├─ multilingual-e5-small + FAISS (CPU)
                                   └─ Qwen3-2B combined analysis / QA (GPU)
Read/Chat/Export ← FastAPI ← DB + indexes ← Streamlit
```

See [docs/architecture.md](docs/architecture.md). ASR details and fine-tuning: [docs/asr.md](docs/asr.md).

## Model defaults

| بخش | مدل پیشنهادی | محل اجرا |
|---|---|---|
| Speech-to-Text | Farsi Faster-Whisper large-v3 (`oi-uae/...`) | GPU |
| LLM | Qwen3-2B-Instruct-2507 (Q4) | GPU |
| Embedding | multilingual-e5-small | CPU |
| Reranker | فعلاً نیاز نیست | — |
| Sentiment Analysis | داخل همان درخواست ترکیبی (اختیاری: Qwen3-4B) | GPU |
| Vector Search | FAISS | CPU |
| Database | PostgreSQL | CPU |

## Requirements

- Docker + Docker Compose **or** Python 3.12, FFmpeg
- PostgreSQL 16 **or** SQLite for local demo
- NVIDIA GPU + CUDA recommended for Whisper / Qwen
- Local OpenAI-compatible endpoint (Ollama / llama.cpp / vLLM / LM Studio) serving Qwen3-2B

## Quick start (Docker)

```bash
cp .env.example .env
# Start local LLM with Qwen3-2B (Q4), then:
docker compose up --build
```

- API: http://localhost:8000/docs  
- UI: http://localhost:8501  
- Postgres: localhost:5432  

## Local development

```bash
cp .env.example .env
# Optional demo DB: set DATABASE_URL=sqlite:///./storage/psi_local.db

docker compose up -d db   # skip if using SQLite

cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r ../requirements.txt
alembic upgrade head            # Postgres only
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal, from backend/)
python -m app.workers.processing_worker

# Frontend
cd ../frontend
set BACKEND_URL=http://localhost:8000
streamlit run app.py
```

For ASR quality tests, upload your own Persian recordings (this project has no TTS stack).

## Environment

Important variables (see `.env.example`):

```env
WHISPER_MODEL=oi-uae/farsi-faster-whisper-large-v3
WHISPER_DEVICE=cuda
WHISPER_CONDITION_ON_PREVIOUS_TEXT=false
ASR_LLM_POLISH=true
EMBEDDING_MODEL=intfloat/multilingual-e5-small
EMBEDDING_DEVICE=cpu
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=Qwen3-2B-Instruct-2507
LLM_TIMEOUT_SECONDS=300
LLM_MAX_TOKENS=1024
LLM_ANALYSIS_MAX_TOKENS=1536
SENTIMENT_USE_SEPARATE_MODEL=false
```

Analysis uses **one combined LLM request** by default. Set `SENTIMENT_USE_SEPARATE_MODEL=true` only when Qwen3-4B is already loaded.

## Usage

```bash
curl -X POST "http://localhost:8000/api/v1/recordings" \
  -F "file=@./sample_data/audio/your_persian.wav"

curl -X POST "http://localhost:8000/api/v1/recordings/<ID>/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"جلسه درباره چه موضوعی بود؟\"}"
```

If evidence is missing:

> اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد.

## Evaluation & tests

```bash
# Evaluation (optional labeled data) — see docs/evaluation.md

cd backend
pytest -q
```

## Security and privacy

- Private storage directories; no public static serving of uploads
- Secrets via environment only; optional `X-API-Key`
- Delete recording removes audio, transcript, analysis, and vector index

## Limitations

- Stock Whisper `medium` is weak on Persian tech talk — use the Farsi fine-tune (default) and `ASR_LLM_POLISH`
- Domain vocabulary may still need `WHISPER_HOTWORDS` / fine-tuning — see [docs/asr.md](docs/asr.md)
- Sentiment is **text-based**, not acoustic emotion recognition
- No reranker; no diarization / realtime streaming in MVP
- Local CPU-only setups will feel slow — GPU recommended

## License

MIT — see [LICENSE](LICENSE).
