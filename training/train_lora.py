"""QLoRA fine-tune for PSI ASR polish or combined analysis adapters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config: {path}")
    return data


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def load_jsonl_messages(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "messages" not in row:
            raise ValueError(f"{path}:{line_no} missing messages")
        rows.append({"messages": row["messages"], "id": row.get("id", str(line_no))})
    if not rows:
        raise ValueError(f"No training rows in {path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        choices=("asr_polish", "analysis"),
        help="Select default config under training/configs/",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="YAML config path (overrides --task default)",
    )
    parser.add_argument("--base-model", type=str, default=None)
    parser.add_argument("--train-file", type=Path, default=None)
    parser.add_argument("--eval-file", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional override for a short smoke run",
    )
    args = parser.parse_args()

    root = _repo_root()
    if args.config:
        cfg_path = resolve_path(root, args.config)
    elif args.task:
        cfg_path = root / "training" / "configs" / f"{args.task}.yaml"
    else:
        parser.error("Provide --task or --config")

    cfg = load_config(cfg_path)
    task = args.task or cfg.get("task")
    if task not in {"asr_polish", "analysis"}:
        raise SystemExit(f"Unknown task: {task}")

    base_model = args.base_model or cfg["base_model"]
    train_file = resolve_path(root, args.train_file or cfg["train_file"])
    eval_file = resolve_path(root, args.eval_file or cfg["eval_file"])
    output_dir = resolve_path(root, args.output_dir or cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Heavy imports after CLI parse so `--help` works without GPU stack.
    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    train_rows = load_jsonl_messages(train_file)
    eval_rows = load_jsonl_messages(eval_file) if eval_file.exists() else []
    train_ds = Dataset.from_list(train_rows)
    eval_ds = Dataset.from_list(eval_rows) if eval_rows else None

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant = None
    if cfg.get("load_in_4bit", True):
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16
            if cfg.get("bf16", True) and torch.cuda.is_available()
            else torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

    model_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "device_map": "auto",
    }
    if quant is not None:
        model_kwargs["quantization_config"] = quant
    else:
        model_kwargs["torch_dtype"] = (
            torch.bfloat16 if torch.cuda.is_available() else torch.float32
        )

    model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
    if cfg.get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    peft_config = LoraConfig(
        r=int(cfg.get("lora_r", 16)),
        lora_alpha=int(cfg.get("lora_alpha", 32)),
        lora_dropout=float(cfg.get("lora_dropout", 0.05)),
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=list(
            cfg.get(
                "target_modules",
                [
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ],
            )
        ),
    )

    sft_kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "num_train_epochs": float(cfg.get("num_train_epochs", 3)),
        "learning_rate": float(cfg.get("learning_rate", 2e-4)),
        "per_device_train_batch_size": int(cfg.get("per_device_train_batch_size", 1)),
        "per_device_eval_batch_size": int(cfg.get("per_device_eval_batch_size", 1)),
        "gradient_accumulation_steps": int(cfg.get("gradient_accumulation_steps", 8)),
        "warmup_ratio": float(cfg.get("warmup_ratio", 0.03)),
        "logging_steps": int(cfg.get("logging_steps", 10)),
        "save_steps": int(cfg.get("save_steps", 50)),
        "bf16": bool(cfg.get("bf16", True)) and torch.cuda.is_available(),
        "fp16": (not bool(cfg.get("bf16", True))) and torch.cuda.is_available(),
        "seed": int(cfg.get("seed", 42)),
        "report_to": [],
        "packing": False,
    }
    max_seq_length = int(cfg.get("max_seq_length", 2048))
    # TRL versions disagree on where max_seq_length / dataset_text_field live.
    sft_kwargs["max_seq_length"] = max_seq_length
    sft_kwargs["dataset_text_field"] = "text"
    if eval_ds is not None:
        sft_kwargs["eval_strategy"] = cfg.get("eval_strategy", "steps")
        sft_kwargs["eval_steps"] = int(cfg.get("eval_steps", 50))
    if args.max_steps is not None:
        sft_kwargs["max_steps"] = args.max_steps

    # Materialize chat text field for SFTTrainer compatibility across TRL versions.
    def _to_text(batch: dict[str, Any]) -> dict[str, list[str]]:
        texts = []
        for messages in batch["messages"]:
            texts.append(
                tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False,
                )
            )
        return {"text": texts}

    train_ds = train_ds.map(_to_text, batched=True, remove_columns=["messages"])
    if eval_ds is not None:
        eval_ds = eval_ds.map(_to_text, batched=True, remove_columns=["messages"])

    try:
        training_args = SFTConfig(**sft_kwargs)
    except TypeError:
        # Older/newer TRL: drop keys that belong on the trainer instead.
        for key in ("max_seq_length", "dataset_text_field", "packing"):
            sft_kwargs.pop(key, None)
        training_args = SFTConfig(**sft_kwargs)

    trainer_kwargs: dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": train_ds,
        "eval_dataset": eval_ds,
        "peft_config": peft_config,
    }
    try:
        trainer = SFTTrainer(processing_class=tokenizer, **trainer_kwargs)
    except TypeError:
        trainer = SFTTrainer(tokenizer=tokenizer, **trainer_kwargs)

    print(
        f"Training task={task} base={base_model} "
        f"train_rows={len(train_rows)} eval_rows={len(eval_rows)}"
    )
    print(f"Output: {output_dir}")
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    meta = {
        "task": task,
        "base_model": base_model,
        "train_file": str(train_file),
        "eval_file": str(eval_file),
        "config": str(cfg_path),
        "lora_r": cfg.get("lora_r", 16),
        "lora_alpha": cfg.get("lora_alpha", 32),
    }
    (output_dir / "psi_finetune_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Saved LoRA adapter:", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
