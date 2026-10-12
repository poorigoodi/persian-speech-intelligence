"""HTTP client for the Persian Speech Intelligence FastAPI backend."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
API_KEY = os.getenv("API_KEY", "")


class APIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class BackendClient:
    def __init__(self, base_url: str | None = None, timeout: float = 120.0) -> None:
        self.base_url = (base_url or DEFAULT_BACKEND_URL).rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if API_KEY:
            headers["X-API-Key"] = API_KEY
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}{API_PREFIX}{path}"

    def _handle(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            try:
                data = response.json()
                message = data.get("message") or data.get("detail") or response.text
            except Exception:
                message = response.text or f"HTTP {response.status_code}"
            raise APIError(str(message), status_code=response.status_code)
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    def health(self) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self._url("/health"), headers=self._headers())
            return self._handle(response)

    def ready(self) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self._url("/ready"), headers=self._headers())
            return self._handle(response)

    def stats(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(self._url("/recordings/stats"), headers=self._headers())
            return self._handle(response)

    def list_recordings(self, limit: int = 50) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url("/recordings"),
                params={"limit": limit},
                headers=self._headers(),
            )
            return self._handle(response)

    def upload(self, filename: str, file_bytes: bytes, content_type: str | None) -> dict:
        files = {
            "file": (filename, file_bytes, content_type or "application/octet-stream")
        }
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                self._url("/recordings"),
                files=files,
                headers=self._headers(),
            )
            return self._handle(response)

    def get_recording(self, recording_id: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url(f"/recordings/{recording_id}"),
                headers=self._headers(),
            )
            return self._handle(response)

    def get_status(self, recording_id: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url(f"/recordings/{recording_id}/status"),
                headers=self._headers(),
            )
            return self._handle(response)

    def get_transcript(self, recording_id: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url(f"/recordings/{recording_id}/transcript"),
                headers=self._headers(),
            )
            return self._handle(response)

    def get_analysis(self, recording_id: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url(f"/recordings/{recording_id}/analysis"),
                headers=self._headers(),
            )
            return self._handle(response)

    def chat(self, recording_id: str, question: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self._url(f"/recordings/{recording_id}/chat"),
                json={"question": question},
                headers=self._headers(),
            )
            return self._handle(response)

    def export(self, recording_id: str, fmt: str = "json") -> str:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self._url(f"/recordings/{recording_id}/export"),
                params={"format": fmt},
                headers=self._headers(),
            )
            if response.status_code >= 400:
                self._handle(response)
            return response.text

    def delete(self, recording_id: str) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                self._url(f"/recordings/{recording_id}"),
                headers=self._headers(),
            )
            return self._handle(response)
