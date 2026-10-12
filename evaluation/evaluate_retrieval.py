"""Retrieval evaluation: Recall@K and recording isolation checks.

Benchmark results are pending until a labeled Q&A evaluation set is provided.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate_manifest(manifest_path: Path, k: int = 5) -> dict:
    """Manifest rows: {question, relevant_chunk_ids, retrieved_chunk_ids}."""
    if not manifest_path.exists():
        return {
            "status": "pending",
            "message": (
                "No labeled retrieval dataset found. "
                "Create sample_data/qa/retrieval_manifest.jsonl with gold chunk IDs."
            ),
            "recall_at_k": None,
            "k": k,
        }

    recalls: list[float] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        relevant = set(row.get("relevant_chunk_ids") or [])
        retrieved = list(row.get("retrieved_chunk_ids") or [])[:k]
        if not relevant:
            continue
        hit = len(relevant.intersection(retrieved)) / len(relevant)
        recalls.append(hit)

    if not recalls:
        return {
            "status": "pending",
            "message": "Manifest empty or missing relevant IDs.",
            "recall_at_k": None,
            "k": k,
        }

    return {
        "status": "completed",
        "k": k,
        "count": len(recalls),
        "recall_at_k": sum(recalls) / len(recalls),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate transcript retrieval")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "sample_data"
        / "qa"
        / "retrieval_manifest.jsonl",
    )
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "retrieval_metrics.json",
    )
    args = parser.parse_args()
    report = evaluate_manifest(args.manifest, k=args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
