# Persian Speech Intelligence

AI-powered Persian speech analysis and conversational intelligence platform.

Upload Persian audio (meetings, interviews, lectures, support calls). The system transcribes speech, generates summaries, extracts structured information, analyzes transcript sentiment, and answers grounded questions over the recording.

Portfolio-ready AI engineering project: modular architecture, async processing, Kaggle benchmarks, Docker, tests, and clear docs.

## Main features

- Persian ASR with **Faster-Whisper Medium** (timestamped segments, GPU)
- Persian-aware transcript normalization
- **One combined LLM analysis call** (summary + topics + entities + sentiment) via **Qwen3-2B**
- Optional separate **Qwen3-4B** sentiment (off by default — avoids GPU model swap)
- Retrieval-augmented Q&A with **recording-level isolation** (e5-small + FAISS)
- Streamlit dashboard with RTL-friendly Persian UI
- FastAPI + PostgreSQL (or SQLite demo) + DB-backed worker
- Kaggle GPU notebooks for speed benchmarking
- Docker Compose, pytest, Ruff

## Repository layout

```
persian-speech-intelligence/
├── backend/           # FastAPI, worker, LLM, ASR, embeddings, tests
├── frontend/          # Streamlit UI
├── notebooks/         # Kaggle GPU benchmarks
├── scripts/           # sample audio generator, Tk test client
├── sample_data/       # fixtures / evaluation manifests
├── evaluation/        # ASR / retrieval / analysis eval scripts
├── docs/              # architecture, API, evaluation
├── storage/           # runtime uploads & vector indexes
├── docker-compose.yml
├── requirements.txt   # meta: -r backend + frontend
└── .env.example
```

## Architecture (runtime)

```
Upload → FastAPI → Storage + Job → Worker
                                   ├─ FFmpeg preprocess
                                   ├─ Faster-Whisper Medium (GPU)
                                   ├─ multilingual-e5-small + FAISS (CPU)
                                   └─ Qwen3-2B combined analysis / QA (GPU)
Read/Chat/Export ← FastAPI ← DB + indexes ← Streamlit
```

See [docs/architecture.md](docs/architecture.md).

## Model defaults

| بخش | مدل پیشنهادی | محل اجرا |
|---|---|---|
| Speech-to-Text | Faster-Whisper Medium | GPU |
| LLM | Qwen3-2B-Instruct-2507 (Q4) | GPU |
| Embedding | multilingual-e5-small | CPU |
| Reranker | فعلاً نیاز نیست | — |
| Sentiment Analysis | داخل همان درخواست ترکیبی (اختیاری: Qwen3-4B) | GPU |
| Vector Search | FAISS | CPU |
| Database | PostgreSQL | CPU |

Kaggle GPU reference timings (cold start, ~16s Persian TTS audio): ASR ~2s, embed search ~0.03s, LLM generate ~37s. Most wall-clock is **model load**, not inference.

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

Generate a Persian demo WAV (not a beep):

```bash
pip install -r backend/requirements-dev.txt
python scripts/create_persian_sample_audio.py
```

## Environment

Important variables (see `.env.example`):

```env
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
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
  -F "file=@./sample_data/audio/example.wav"

curl -X POST "http://localhost:8000/api/v1/recordings/<ID>/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"جلسه درباره چه موضوعی بود؟\"}"
```

If evidence is missing:

> اطلاعات کافی برای پاسخ به این سؤال در فایل صوتی وجود ندارد.

## Kaggle GPU benchmarks

Notebooks under [`notebooks/`](notebooks/) — enable **GPU T4**, then Run All:

| Notebook | Focus |
|---|---|
| `kaggle_psi_e2e.ipynb` | Full pipeline + timings |
| `kaggle_01_asr_only.ipynb` | Whisper only |
| `kaggle_02_embedding_faiss.ipynb` | e5 + FAISS |
| `kaggle_03_llm_analysis.ipynb` | Qwen 4-bit analysis |

See [`notebooks/README.md`](notebooks/README.md).

## Evaluation & tests

```bash
# Evaluation (optional labeled data)
# see docs/evaluation.md

cd backend
pytest -q
```

## Security and privacy

- Private storage directories; no public static serving of uploads
- Secrets via environment only; optional `X-API-Key`
- Delete recording removes audio, transcript, analysis, and vector index

## Limitations

- Whisper quality varies for noisy / informal Persian and code-switching
- Sentiment is **text-based**, not acoustic emotion recognition
- No reranker; no diarization / realtime streaming in MVP
- Local CPU-only setups will feel slow — use GPU or Kaggle notebooks

## License

MIT — see [LICENSE](LICENSE).
