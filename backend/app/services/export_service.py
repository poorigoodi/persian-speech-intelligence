"""Export analysis and transcript results to downloadable formats."""

from __future__ import annotations

import json

from app.models.analysis import Analysis
from app.models.recording import Recording
from app.models.transcript import TranscriptSegment
from app.schemas.analysis import ExportResponse


class ExportService:
    def export(
        self,
        recording: Recording,
        segments: list[TranscriptSegment],
        analysis: Analysis | None,
        *,
        fmt: str,
    ) -> ExportResponse:
        fmt_normalized = fmt.lower()
        if fmt_normalized not in {"json", "txt", "markdown"}:
            raise ValueError("Unsupported export format.")

        payload = self._build_payload(recording, segments, analysis)

        if fmt_normalized == "json":
            content = json.dumps(payload, ensure_ascii=False, indent=2)
            filename = f"{recording.id}.json"
        elif fmt_normalized == "txt":
            content = self._to_txt(payload)
            filename = f"{recording.id}.txt"
        else:
            content = self._to_markdown(payload)
            filename = f"{recording.id}.md"

        return ExportResponse(
            recording_id=recording.id,
            format=fmt_normalized,  # type: ignore[arg-type]
            content=content,
            filename=filename,
        )

    def _build_payload(
        self,
        recording: Recording,
        segments: list[TranscriptSegment],
        analysis: Analysis | None,
    ) -> dict:
        return {
            "recording_id": str(recording.id),
            "original_filename": recording.original_filename,
            "duration_seconds": recording.duration_seconds,
            "language": recording.language,
            "status": recording.processing_status.value,
            "transcript": {
                "full_text": " ".join(s.original_text for s in segments),
                "full_text_normalized": " ".join(s.normalized_text for s in segments),
                "segments": [
                    {
                        "id": str(s.id),
                        "start": s.start_time,
                        "end": s.end_time,
                        "original_text": s.original_text,
                        "normalized_text": s.normalized_text,
                    }
                    for s in segments
                ],
            },
            "analysis": None
            if analysis is None
            else {
                "short_summary": analysis.short_summary,
                "detailed_summary": analysis.detailed_summary,
                "topics": analysis.topics,
                "sentiment": analysis.sentiment,
                "extracted_entities": analysis.extracted_entities,
                "action_items": analysis.action_items,
                "decisions": analysis.decisions,
            },
        }

    def _to_txt(self, payload: dict) -> str:
        lines = [
            f"Recording: {payload['original_filename']}",
            f"ID: {payload['recording_id']}",
            f"Duration: {payload.get('duration_seconds')}",
            "",
            "=== Transcript ===",
            payload["transcript"]["full_text_normalized"]
            or payload["transcript"]["full_text"],
            "",
        ]
        analysis = payload.get("analysis") or {}
        if analysis:
            lines.extend(
                [
                    "=== Short Summary ===",
                    analysis.get("short_summary") or "",
                    "",
                    "=== Topics ===",
                    json.dumps(analysis.get("topics") or [], ensure_ascii=False, indent=2),
                    "",
                    "=== Sentiment ===",
                    json.dumps(analysis.get("sentiment") or {}, ensure_ascii=False, indent=2),
                    "",
                    "=== Action Items ===",
                    json.dumps(
                        analysis.get("action_items") or [], ensure_ascii=False, indent=2
                    ),
                    "",
                    "=== Decisions ===",
                    json.dumps(analysis.get("decisions") or [], ensure_ascii=False, indent=2),
                ]
            )
        return "\n".join(lines)

    def _to_markdown(self, payload: dict) -> str:
        analysis = payload.get("analysis") or {}
        lines = [
            f"# Analysis Report — {payload['original_filename']}",
            "",
            f"- Recording ID: `{payload['recording_id']}`",
            f"- Duration: {payload.get('duration_seconds')}",
            f"- Language: {payload.get('language')}",
            "",
            "## Transcript",
            "",
            payload["transcript"]["full_text_normalized"]
            or payload["transcript"]["full_text"],
            "",
        ]
        if analysis:
            lines.extend(
                [
                    "## Short Summary",
                    "",
                    analysis.get("short_summary") or "_None_",
                    "",
                    "## Detailed Summary",
                    "",
                    "```json",
                    json.dumps(
                        analysis.get("detailed_summary") or {},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "```",
                    "",
                    "## Topics",
                    "",
                    "```json",
                    json.dumps(analysis.get("topics") or [], ensure_ascii=False, indent=2),
                    "```",
                    "",
                    "## Sentiment",
                    "",
                    "```json",
                    json.dumps(
                        analysis.get("sentiment") or {}, ensure_ascii=False, indent=2
                    ),
                    "```",
                    "",
                    "## Action Items",
                    "",
                    "```json",
                    json.dumps(
                        analysis.get("action_items") or [], ensure_ascii=False, indent=2
                    ),
                    "```",
                    "",
                    "## Decisions",
                    "",
                    "```json",
                    json.dumps(
                        analysis.get("decisions") or [], ensure_ascii=False, indent=2
                    ),
                    "```",
                ]
            )
        return "\n".join(lines)
