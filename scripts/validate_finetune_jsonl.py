"""Validate fine-tune JSONL against production prompt/schema contracts."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.analysis import (  # noqa: E402
    DetailedSummary,
    ExtractedEntities,
    SentimentResult,
    TopicItem,
)
from app.utils.asr_correct import ASR_POLISH_SYSTEM  # noqa: E402


class CombinedAnalysisPayload(BaseModel):
    """Mirrors app.services.analysis_pipeline.CombinedAnalysisPayload."""

    short_summary: str = ""
    detailed_summary: DetailedSummary = Field(default_factory=DetailedSummary)
    topics: list[TopicItem] = Field(default_factory=list)
    sentiment: SentimentResult | None = None
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)


def _load_string_const(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise RuntimeError(f"{name} not found in {path}")


COMBINED_SYSTEM_PROMPT = _load_string_const(
    BACKEND / "app" / "services" / "analysis_pipeline.py",
    "COMBINED_SYSTEM_PROMPT",
)


def _assistant_content(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return (msg.get("content") or "").strip()
    raise ValueError("missing assistant message")


def _system_content(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "system":
            return (msg.get("content") or "").strip()
    raise ValueError("missing system message")


def validate_row(task: str, row: dict, *, line_no: int) -> list[str]:
    errors: list[str] = []
    if "id" not in row or not str(row["id"]).strip():
        errors.append(f"L{line_no}: missing id")
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 3:
        errors.append(f"L{line_no}: messages must be a list of >= 3 chat turns")
        return errors

    roles = [m.get("role") for m in messages if isinstance(m, dict)]
    if "system" not in roles or "user" not in roles or "assistant" not in roles:
        errors.append(f"L{line_no}: need system, user, and assistant roles")

    try:
        system = _system_content(messages)
        assistant = _assistant_content(messages)
    except ValueError as exc:
        errors.append(f"L{line_no}: {exc}")
        return errors

    if task == "asr_polish":
        if system != ASR_POLISH_SYSTEM.strip():
            errors.append(
                f"L{line_no}: system prompt != ASR_POLISH_SYSTEM "
                "(copy from app.utils.asr_correct)"
            )
        if not assistant:
            errors.append(f"L{line_no}: empty assistant (corrected transcript)")
    elif task == "analysis":
        if system != COMBINED_SYSTEM_PROMPT.strip():
            errors.append(
                f"L{line_no}: system prompt != COMBINED_SYSTEM_PROMPT "
                "(copy from app.services.analysis_pipeline)"
            )
        try:
            payload = json.loads(assistant)
        except json.JSONDecodeError as exc:
            errors.append(f"L{line_no}: assistant is not valid JSON ({exc})")
            return errors
        try:
            CombinedAnalysisPayload.model_validate(payload)
        except Exception as exc:
            errors.append(f"L{line_no}: CombinedAnalysisPayload invalid: {exc}")
    else:
        errors.append(f"unknown task: {task}")

    return errors


def validate_file(task: str, path: Path) -> int:
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        return 1

    errors: list[str] = []
    count = 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"L{line_no}: JSON decode error: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"L{line_no}: row must be an object")
            continue
        errors.extend(validate_row(task, row, line_no=line_no))

    if errors:
        print(f"FAIL {path} ({count} rows):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(f"OK {path}: {count} rows")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("asr_polish", "analysis"), required=False)
    parser.add_argument("--path", type=Path, required=False)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate the default sample_data/finetune tree.",
    )
    args = parser.parse_args()

    if args.all:
        root = ROOT / "sample_data" / "finetune"
        code = 0
        for task, rel in (
            ("asr_polish", "asr_polish/train.jsonl"),
            ("asr_polish", "asr_polish/eval.jsonl"),
            ("analysis", "analysis/train.jsonl"),
            ("analysis", "analysis/eval.jsonl"),
        ):
            code |= validate_file(task, root / rel)
        return code

    if not args.task or not args.path:
        parser.error("--task and --path are required unless --all is set")
    return validate_file(args.task, args.path)


if __name__ == "__main__":
    raise SystemExit(main())
