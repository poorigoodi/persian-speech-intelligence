"""Version 1 API routers."""

from fastapi import APIRouter

from app.api.v1 import analysis, chat, health, recordings, transcripts

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
api_router.include_router(transcripts.router, prefix="/recordings", tags=["transcripts"])
api_router.include_router(analysis.router, prefix="/recordings", tags=["analysis"])
api_router.include_router(chat.router, prefix="/recordings", tags=["chat"])
