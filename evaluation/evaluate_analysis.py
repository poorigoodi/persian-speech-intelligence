"""Summarization / extraction evaluation helpers.

Metrics:
- Factual consistency (manual checklist score)
- Coverage of important information
- Unsupported claims count
- Extraction Precision / Recall / F1 when annotations exist

Does not invent scores. Writes pending status when labels are absent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evaluate_extraction(manifest_path: Path) -> dict:
    """Rows: {predicted: [...], gold: [...]} string sets for entity/task matching."""
    if not manifest_path.exists():
        return {
            "status": "pending",
            "message": (
                "No annotated extraction set found. "
                "Add sample_data/analysis/extraction_manifest.jsonl."
            ),
        }

    precisions: list[float] = []
    recalls: list[float] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        predicted = set(row.get("predicted") or [])
        gold = set(row.get("gold") or [])
        if not predicted and not gold:
            continue
        tp = len(predicted & gold)
        precision = tp / len(predicted) if predicted else 0.0
        recall = tp / len(gold) if gold else 0.0
        precisions.append(precision)
        recalls.append(recall)

    if not precisions:
        return {"status": "pending", "message": "Manifest empty."}

    p = sum(precisions) / len(precisions)
    r = sum(recalls) / len(recalls)
    return {
        "status": "completed",
        "count": len(precisions),
        "precision": p,
        "recall": r,
        "f1": f1(p, r),
    }


def evaluate_summaries(manifest_path: Path) -> dict:
    """Rows with manual review fields: factual_consistency, coverage, unsupported_claims, readability."""
    if not manifest_path.exists():
        return {
            "status": "pending",
            "message": (
                "No manually reviewed summary set found. "
                "Add sample_data/analysis/summary_review.jsonl."
            ),
        }

    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        return {"status": "pending", "message": "Manifest empty."}

    def avg(key: str) -> float:
        values = [float(r[key]) for r in rows if key in r]
        return sum(values) / len(values) if values else 0.0

    return {
        "status": "completed",
        "count": len(rows),
        "avg_factual_consistency": avg("factual_consistency"),
        "avg_coverage": avg("coverage"),
        "avg_unsupported_claims": avg("unsupported_claims"),
        "avg_readability": avg("readability"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate analysis quality")
    root = Path(__file__).resolve().parents[1] / "sample_data" / "analysis"
    parser.add_argument("--extraction-manifest", type=Path, default=root / "extraction_manifest.jsonl")
    parser.add_argument("--summary-manifest", type=Path, default=root / "summary_review.jsonl")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "analysis_metrics.json",
    )
    args = parser.parse_args()
    report = {
        "extraction": evaluate_extraction(args.extraction_manifest),
        "summarization": evaluate_summaries(args.summary_manifest),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
