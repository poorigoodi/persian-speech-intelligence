"""Evaluate LoRA fine-tune holdouts for ASR polish (WER/CER) and analysis (JSON/F1).

Modes:
1) Score precomputed predictions JSONL (--predictions)
2) Generate with base+adapter (--base-model --adapter) then score

Does not invent scores when eval data is missing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT / "evaluation") not in sys.path:
    sys.path.insert(0, str(ROOT / "evaluation"))

from evaluate_asr import character_error_rate, word_error_rate  # noqa: E402
from evaluate_analysis import f1  # noqa: E402


def _assistant(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return (msg.get("content") or "").strip()
    return ""


def _prompt_messages(messages: list[dict]) -> list[dict]:
    """Drop gold assistant turn for generation."""
    out: list[dict] = []
    for msg in messages:
        if msg.get("role") == "assistant":
            break
        out.append({"role": msg["role"], "content": msg["content"]})
    return out


def load_eval_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows.append(row)
    return rows


def load_predictions(path: Path) -> dict[str, str]:
    """JSONL rows: {id, prediction} or {id, hypothesis}."""
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rid = str(row.get("id", ""))
        pred = row.get("prediction")
        if pred is None:
            pred = row.get("hypothesis")
        if rid and pred is not None:
            out[rid] = str(pred)
    return out


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return None
    snippet = text[start:]
    for end in range(len(snippet), 0, -1):
        try:
            data = json.loads(snippet[:end])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def _topic_names(payload: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for topic in payload.get("topics") or []:
        if isinstance(topic, str):
            names.add(topic.strip())
        elif isinstance(topic, dict) and topic.get("name"):
            names.add(str(topic["name"]).strip())
    return {n for n in names if n}


def _keyword_set(payload: dict[str, Any]) -> set[str]:
    ents = payload.get("extracted_entities") or {}
    if isinstance(ents, list):
        return {str(x.get("entity", x)).strip() for x in ents if x}
    keywords = ents.get("keywords") or []
    return {str(k).strip() for k in keywords if str(k).strip()}


def _set_f1(predicted: set[str], gold: set[str]) -> tuple[float, float, float]:
    if not predicted and not gold:
        return 1.0, 1.0, 1.0
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return precision, recall, f1(precision, recall)


def generate_with_adapter(
    rows: list[dict[str, Any]],
    *,
    base_model: str,
    adapter: Path,
    max_new_tokens: int,
) -> dict[str, str]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    model = PeftModel.from_pretrained(model, str(adapter))
    model.eval()

    preds: dict[str, str] = {}
    for row in rows:
        rid = str(row.get("id", ""))
        messages = _prompt_messages(row.get("messages") or [])
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
        text = tokenizer.decode(
            out[0][inputs["input_ids"].shape[-1] :],
            skip_special_tokens=True,
        ).strip()
        preds[rid] = text
    return preds


def evaluate_asr_polish(
    eval_rows: list[dict[str, Any]],
    predictions: dict[str, str],
) -> dict[str, Any]:
    wers: list[float] = []
    cers: list[float] = []
    missing = 0
    for row in eval_rows:
        rid = str(row.get("id", ""))
        gold = _assistant(row.get("messages") or [])
        hyp = predictions.get(rid)
        if hyp is None:
            missing += 1
            continue
        wers.append(word_error_rate(gold, hyp))
        cers.append(character_error_rate(gold, hyp))

    if not wers:
        return {
            "status": "pending",
            "message": "No overlapping predictions for ASR polish eval.",
            "missing": missing,
        }
    return {
        "status": "completed",
        "task": "asr_polish",
        "count": len(wers),
        "missing_predictions": missing,
        "wer_mean": sum(wers) / len(wers),
        "cer_mean": sum(cers) / len(cers),
    }


def evaluate_analysis(
    eval_rows: list[dict[str, Any]],
    predictions: dict[str, str],
) -> dict[str, Any]:
    parse_ok = 0
    topic_scores: list[tuple[float, float, float]] = []
    keyword_scores: list[tuple[float, float, float]] = []
    missing = 0
    for row in eval_rows:
        rid = str(row.get("id", ""))
        gold_raw = _assistant(row.get("messages") or [])
        hyp_raw = predictions.get(rid)
        if hyp_raw is None:
            missing += 1
            continue
        gold = _extract_json_blob(gold_raw) or {}
        pred = _extract_json_blob(hyp_raw)
        if pred is None:
            continue
        parse_ok += 1
        topic_scores.append(_set_f1(_topic_names(pred), _topic_names(gold)))
        keyword_scores.append(_set_f1(_keyword_set(pred), _keyword_set(gold)))

    n = len(eval_rows) - missing
    if n <= 0:
        return {
            "status": "pending",
            "message": "No overlapping predictions for analysis eval.",
            "missing": missing,
        }

    def _avg(idx: int, scores: list[tuple[float, float, float]]) -> float:
        if not scores:
            return 0.0
        return sum(s[idx] for s in scores) / len(scores)

    return {
        "status": "completed",
        "task": "analysis",
        "count": n,
        "missing_predictions": missing,
        "json_parse_rate": parse_ok / n,
        "topics": {
            "precision": _avg(0, topic_scores),
            "recall": _avg(1, topic_scores),
            "f1": _avg(2, topic_scores),
        },
        "keywords": {
            "precision": _avg(0, keyword_scores),
            "recall": _avg(1, keyword_scores),
            "f1": _avg(2, keyword_scores),
        },
        "note": (
            "Also review short_summary coverage manually on a 20-example holdout "
            "(see sample_data/analysis/summary_review.jsonl)."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("asr_polish", "analysis"), required=True)
    parser.add_argument(
        "--eval-jsonl",
        type=Path,
        help="Holdout chat JSONL (default under sample_data/finetune/)",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        help="JSONL of {id, prediction} to score without loading a model",
    )
    parser.add_argument("--base-model", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--adapter", type=Path, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write metrics JSON (default evaluation/results/finetune_<task>.json)",
    )
    args = parser.parse_args()

    default_eval = (
        ROOT
        / "sample_data"
        / "finetune"
        / ("asr_polish" if args.task == "asr_polish" else "analysis")
        / "eval.jsonl"
    )
    eval_path = args.eval_jsonl or default_eval
    if not eval_path.exists():
        payload = {
            "status": "pending",
            "message": f"Eval file not found: {eval_path}",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    rows = load_eval_jsonl(eval_path)
    if args.predictions:
        predictions = load_predictions(args.predictions)
    elif args.adapter:
        predictions = generate_with_adapter(
            rows,
            base_model=args.base_model,
            adapter=args.adapter.resolve(),
            max_new_tokens=args.max_new_tokens,
        )
    else:
        payload = {
            "status": "pending",
            "message": "Provide --predictions or --adapter to score the holdout.",
            "eval_jsonl": str(eval_path),
            "count": len(rows),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.task == "asr_polish":
        result = evaluate_asr_polish(rows, predictions)
    else:
        result = evaluate_analysis(rows, predictions)

    out = args.out or (ROOT / "evaluation" / "results" / f"finetune_{args.task}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
