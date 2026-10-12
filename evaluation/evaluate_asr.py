"""ASR evaluation: Word Error Rate (WER) and Character Error Rate (CER).

Uses manually verified Persian reference transcripts when available.
Does not fabricate benchmark scores — results are written only after real runs.

Normalization policy (documented for reproducibility):
- Unicode NFC
- Arabic/Persian character variant unification
- Optional digit normalization via normalize_for_evaluation()
- Lowercasing and punctuation stripping for metric fairness

Example categories to include in sample_data/asr/:
- formal Persian
- informal Persian
- noisy recordings
- mixed Persian-English speech
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from app.utils.persian_normalize import normalize_for_evaluation


@dataclass
class ASRExampleResult:
    example_id: str
    category: str
    wer: float
    cer: float
    hypothesis_chars: int
    reference_chars: int


def _edit_distance(a: list[str], b: list[str]) -> int:
    """Classic Levenshtein distance."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_tokens = normalize_for_evaluation(reference).split()
    hyp_tokens = normalize_for_evaluation(hypothesis).split()
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    return _edit_distance(ref_tokens, hyp_tokens) / len(ref_tokens)


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref = list(re.sub(r"\s+", "", normalize_for_evaluation(reference)))
    hyp = list(re.sub(r"\s+", "", normalize_for_evaluation(hypothesis)))
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(ref, hyp) / len(ref)


def evaluate_manifest(manifest_path: Path) -> dict:
    """Evaluate a JSONL manifest of {id, category, reference, hypothesis}."""
    results: list[ASRExampleResult] = []
    if not manifest_path.exists():
        return {
            "status": "pending",
            "message": (
                "No labeled ASR evaluation dataset found. "
                "Add sample_data/asr/manifest.jsonl with verified Persian references, "
                "then re-run this script."
            ),
            "results": [],
        }

    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        wer = word_error_rate(row["reference"], row["hypothesis"])
        cer = character_error_rate(row["reference"], row["hypothesis"])
        results.append(
            ASRExampleResult(
                example_id=row.get("id", ""),
                category=row.get("category", "unspecified"),
                wer=wer,
                cer=cer,
                hypothesis_chars=len(row.get("hypothesis", "")),
                reference_chars=len(row.get("reference", "")),
            )
        )

    if not results:
        return {"status": "pending", "message": "Manifest is empty.", "results": []}

    avg_wer = sum(r.wer for r in results) / len(results)
    avg_cer = sum(r.cer for r in results) / len(results)
    return {
        "status": "completed",
        "count": len(results),
        "average_wer": avg_wer,
        "average_cer": avg_cer,
        "results": [asdict(r) for r in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Persian ASR WER/CER")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "sample_data" / "asr" / "manifest.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "asr_metrics.json",
    )
    args = parser.parse_args()
    report = evaluate_manifest(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
