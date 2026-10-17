"""Merge a LoRA adapter into the base model for OpenAI-compatible serving."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-model",
        type=str,
        default=None,
        help="HF id or path (default: read from adapter psi_finetune_meta.json)",
    )
    parser.add_argument(
        "--adapter",
        type=Path,
        required=True,
        help="Directory with LoRA adapter weights",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory for merged full model",
    )
    parser.add_argument(
        "--dtype",
        choices=("bf16", "fp16", "fp32"),
        default="bf16",
    )
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter = args.adapter.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    base_model = args.base_model
    meta_path = adapter / "psi_finetune_meta.json"
    if base_model is None and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        base_model = meta.get("base_model")
    if not base_model:
        raise SystemExit("Provide --base-model or ensure psi_finetune_meta.json exists")

    dtype_map = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }
    torch_dtype = dtype_map[args.dtype]

    print(f"Loading base: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch_dtype,
        device_map="cpu",
        trust_remote_code=True,
    )
    print(f"Loading adapter: {adapter}")
    model = PeftModel.from_pretrained(model, str(adapter))
    print("Merging…")
    model = model.merge_and_unload()

    print(f"Saving merged model: {output}")
    model.save_pretrained(str(output), safe_serialization=True)
    tokenizer.save_pretrained(str(output))
    (output / "psi_merge_meta.json").write_text(
        json.dumps(
            {
                "base_model": base_model,
                "adapter": str(adapter),
                "dtype": args.dtype,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
