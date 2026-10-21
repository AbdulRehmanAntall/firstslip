"""Phase 4 (E4) training: SFT baseline or GRPO with the checker reward (GPU, Colab A100).

    python scripts/phase4_train.py sft  --seed 0
    python scripts/phase4_train.py grpo --seed 0
    python scripts/phase4_train.py grpo --seed 0 --max-steps 5     # smoke test
    python scripts/phase4_train.py sft  --seed 0 --fallback        # Qwen3-1.7B

Both methods start from the base model, train a LoRA adapter (config/phase4.json)
on data/phase4/train.jsonl (scripts/phase4_prepare.py) and save it to
<out>/<method>-s<seed>/final. GRPO also saves an adapter every `save_steps` for
the 12 Nov go/no-go. The run log (runs/*_phase4train_*.jsonl) holds the config,
package versions, model SHA and the trainer's full log history.

SFT is pre-tokenized here so the loss covers exactly "Step: k\\nFeedback:" and no
end-of-turn token (core/phase4.py); the script checks this on the first batch.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.phase4 import TARGET_VERSION, format_reward, load_config, load_rows, sft_target, step_reward  # noqa: E402
from core.prompts import PROMPT_VERSION  # noqa: E402
from core.runlog import RunLog  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def versions() -> dict:
    import importlib.metadata as md
    out = {}
    for p in ("torch", "transformers", "trl", "peft", "vllm", "accelerate"):
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = None
    try:
        out["gpu"] = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        out["gpu"] = None
    return out


def load_model(repo: str, sha: str):
    """Load with the checkpoint's own class (Qwen3.5 is image-text), so merged weights keep its layout."""
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer

    cfg = AutoConfig.from_pretrained(repo, revision=sha)
    cls = AutoModelForImageTextToText if hasattr(cfg, "vision_config") else AutoModelForCausalLM
    model = cls.from_pretrained(repo, revision=sha, dtype=torch.bfloat16, attn_implementation="sdpa")
    tok = AutoTokenizer.from_pretrained(repo, revision=sha)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    return model, tok


def lora_config(cfg: dict):
    from peft import LoraConfig
    return LoraConfig(task_type="CAUSAL_LM", target_modules="all-linear", exclude_modules=r".*visual.*", **cfg)


def prompt_text(tok, msgs: list[dict]) -> str:
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)


def sft_dataset(tok, rows: list[dict]):
    from datasets import Dataset

    def encode(r):
        p = tok(prompt_text(tok, r["prompt"]), add_special_tokens=False)["input_ids"]
        c = tok(sft_target(r["checker_step"]), add_special_tokens=False)["input_ids"]
        return {"input_ids": p + c, "labels": [-100] * len(p) + c}

    return Dataset.from_list([encode(r) for r in rows])


def check_sft_batch(trainer, tok, rows: list[dict]) -> None:
    """The supervised tokens of the first rows must be exactly the step-only target."""
    ds = trainer.train_dataset
    for i in range(3):
        labels = [t for t in ds[i]["labels"] if t != -100]
        got, want = tok.decode(labels), sft_target(rows[i]["checker_step"])
        assert got == want, f"supervised tokens {got!r} != target {want!r}"
        assert labels[-1] not in (tok.eos_token_id, tok.pad_token_id), "target must not end the turn"
    print("SFT target check OK:", repr(want))


def train_sft(model, tok, rows, cfg, seed, out: Path, max_steps: int | None):
    from trl import SFTConfig, SFTTrainer

    s = cfg["sft"]
    args = SFTConfig(output_dir=str(out), seed=seed, data_seed=seed, learning_rate=s["learning_rate"],
                     num_train_epochs=s["num_train_epochs"], max_steps=max_steps or -1,
                     per_device_train_batch_size=s["per_device_train_batch_size"],
                     gradient_accumulation_steps=s["gradient_accumulation_steps"],
                     warmup_steps=s["warmup_steps"], lr_scheduler_type=s["lr_scheduler_type"],
                     max_length=s["max_length"], bf16=True, logging_steps=5, save_strategy="no",
                     report_to="none")
    trainer = SFTTrainer(model=model, args=args, train_dataset=sft_dataset(tok, rows), processing_class=tok,
                         peft_config=lora_config(cfg["lora"]))
    check_sft_batch(trainer, tok, rows)
    trainer.train()
    return trainer


def train_grpo(model, tok, rows, cfg, seed, out: Path, max_steps: int | None):
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer

    g = cfg["grpo"]
    args = GRPOConfig(output_dir=str(out), seed=seed, data_seed=seed, learning_rate=g["learning_rate"],
                      max_steps=max_steps or g["max_steps"], num_generations=g["num_generations"],
                      per_device_train_batch_size=g["per_device_train_batch_size"],
                      gradient_accumulation_steps=g["gradient_accumulation_steps"],
                      max_completion_length=g["max_completion_length"], temperature=g["temperature"],
                      beta=g["beta"], warmup_steps=g["warmup_steps"], lr_scheduler_type=g["lr_scheduler_type"],
                      use_vllm=True, vllm_mode="colocate", vllm_gpu_memory_utilization=g["vllm_gpu_memory_utilization"],
                      chat_template_kwargs={"enable_thinking": False}, bf16=True, logging_steps=1,
                      save_strategy="steps", save_steps=g["save_steps"], save_only_model=True, report_to="none")
    ds = Dataset.from_list([{"prompt": r["prompt"], "checker_step": r["checker_step"]} for r in rows])
    trainer = GRPOTrainer(model=model, reward_funcs=[step_reward, format_reward], args=args, train_dataset=ds,
                          processing_class=tok, peft_config=lora_config(cfg["lora"]))
    trainer.train()
    return trainer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("method", choices=("sft", "grpo"))
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--fallback", action="store_true", help="train Qwen3-1.7B instead of Qwen3.5-2B")
    ap.add_argument("--max-steps", type=int, default=None, help="cap steps (smoke test)")
    ap.add_argument("--out", type=Path, default=ROOT / "checkpoints" / "phase4")
    args = ap.parse_args()

    from huggingface_hub import model_info

    cfg = load_config()
    m = cfg["model"]
    name, repo = (m["fallback_name"], m["fallback_id"]) if args.fallback else (m["name"], m["id"])
    sha = model_info(repo).sha
    label = f"{args.method}-s{args.seed}" + (f"-smoke{args.max_steps}" if args.max_steps else "")
    out = args.out / name / label
    rows = load_rows("train")

    run_cfg = {"phase": 4, "method": args.method, "model": {"name": name, "id": repo, "revision": sha},
               "lora": cfg["lora"], args.method: cfg[args.method], "max_steps_override": args.max_steps,
               "target_version": TARGET_VERSION, "prompt_version": PROMPT_VERSION, "n_train": len(rows),
               "out": str(out), "versions": versions()}
    with RunLog(f"phase4train_{args.method}_{name}_{label}", run_cfg, seed=args.seed) as log:
        model, tok = load_model(repo, sha)
        fn = train_sft if args.method == "sft" else train_grpo
        trainer = fn(model, tok, rows, cfg, args.seed, out, args.max_steps)
        trainer.save_model(str(out / "final"))
        tok.save_pretrained(str(out / "final"))
        for entry in trainer.state.log_history:
            log.write({"type": "log", **entry})
        log.write({"type": "done", "adapter": str(out / "final"), "global_step": trainer.state.global_step})
    print("adapter ->", out / "final", "| log ->", log.path.name)


if __name__ == "__main__":
    main()
