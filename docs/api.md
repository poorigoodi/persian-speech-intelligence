# API Reference

Base URL (local): `http://localhost:8000`

API prefix: `/api/v1`

Interactive docs: `http://localhost:8000/docs`

Optional auth: set `AUTH_ENABLED=true` and send header `X-API-Key: <API_KEY>`.

## Endpoints

### Health

- `GET /api/v1/health` — liveness
- `GET /api/v1/ready` — database + storage readiness

### Recordings

- `POST /api/v1/recordings` — multipart upload (`file`)
- `GET /api/v1/recordings` — list (`limit`, `offset`, `status`)
- `GET /api/v1/recordings/stats` — dashboard counters
- `GET /api/v1/recordings/{id}` — metadata
- `GET /api/v1/recordings/{id}/status` — job progress
- `DELETE /api/v1/recordings/{id}` — delete recording + related data

### Transcript & analysis

- `GET /api/v1/recordings/{id}/transcript`
- `GET /api/v1/recordings/{id}/analysis`
- `GET /api/v1/recordings/{id}/export?format=json|txt|markdown`

### Chat

- `POST /api/v1/recordings/{id}/chat`
  ```json
  { "question": "جلسه درباره چه موضوعی بود؟" }
  ```

## Example upload (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/recordings" \
  -F "file=@sample_data/audio/example.wav"
```

## Example chat (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/recordings/<RECORDING_ID>/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"چه تصمیم‌هایی گرفته شد؟\"}"
```

## Error shape

```json
{
  "code": "not_found",
  "message": "Recording not found.",
  "details": {}
}
```

Sensitive storage paths and API keys are never returned in responses.
