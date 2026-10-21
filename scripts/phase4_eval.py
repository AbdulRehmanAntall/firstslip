"""Evaluate Phase 4 models with vLLM: the base model or a trained LoRA adapter (GPU).

    python scripts/phase4_eval.py --label base
    python scripts/phase4_eval.py --label sft-s0 --adapter checkpoints/phase4/qwen-2b/sft-s0/final
    python scripts/phase4_eval.py --label grpo-s0-step100 --adapter .../checkpoint-100 --splits dev

Same frozen prompt (p2-v1, "none"), greedy decoding with thinking off, and the same
record format as Phase 2 (core.phase2.record). An adapter is merged into the full
base model (its own image-text class) and saved to a temporary folder that vLLM
loads exactly like the base checkpoint. Writes runs/*_phase4_<split>_<label>.jsonl
and prints first-error accuracy, clean accuracy and error F1 per split.
"""
import argparse
import gc
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.phase2 import record, requests_for, run_config  # noqa: E402
from core.phase4 import load_config  # noqa: E402
from core.runlog import RunLog  # noqa: E402


def merge(repo: str, sha: str, adapter: Path, dest: Path) -> None:
    import torch
    from peft import PeftModel
    from transformers import AutoConfig, AutoModelForCausalLM, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

    cfg = AutoConfig.from_pretrained(repo, revision=sha)
    multimodal = hasattr(cfg, "vision_config")
    cls = AutoModelForImageTextToText if multimodal else AutoModelForCausalLM
    base = cls.from_pretrained(repo, revision=sha, dtype=torch.bfloat16)
    PeftModel.from_pretrained(base, str(adapter)).merge_and_unload().save_pretrained(str(dest))
    (AutoProcessor if multimodal else AutoTokenizer).from_pretrained(repo, revision=sha).save_pretrained(str(dest))
    del base
    gc.collect()
    torch.cuda.empty_cache()


def summary(recs: list[dict]) -> str:
    wrong = [r for r in recs if r["gold"]]
    clean = [r for r in recs if not r["gold"]]
    a = sum(r["pred"] == r["gold"] for r in wrong) / max(1, len(wrong))
    c = sum(r["pred"] == 0 for r in clean) / max(1, len(clean))
    f1 = 0.0 if a + c == 0 else 2 * a * c / (a + c)
    parsed = sum(r["pred"] is not None for r in recs) / len(recs)
    return f"first-error {a:.3f} | clean {c:.3f} | F1 {f1:.3f} | parsed {parsed:.3f}"


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="base, sft-s0, grpo-s1, grpo-s0-step100, ...")
    ap.add_argument("--adapter", type=Path, default=None)
    ap.add_argument("--splits", nargs="+", default=cfg["eval"]["splits"])
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--fallback", action="store_true")
    args = ap.parse_args()
    if (args.label == "base") != (args.adapter is None):
        ap.error("use --adapter for every label except 'base'")

    import vllm
    from huggingface_hub import model_info
    from vllm import SamplingParams

    m, e = cfg["model"], cfg["eval"]
    name, repo = (m["fallback_name"], m["fallback_id"]) if args.fallback else (m["name"], m["id"])
    sha = model_info(repo).sha
    tmp = None
    path = repo
    if args.adapter:
        tmp = Path(tempfile.mkdtemp(prefix="phase4_merged_"))
        merge(repo, sha, args.adapter, tmp)
        path = str(tmp)
    kwargs = {"limit_mm_per_prompt": {"image": 0, "video": 0}} if "Qwen3.5" in repo else {}
    llm = vllm.LLM(model=path, revision=None if tmp else sha, max_model_len=e["max_model_len"],
                   gpu_memory_utilization=0.85, seed=0, **kwargs)
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True).strip()
    info = {"name": f"{name}/{args.label}", "base": name, "label": args.label, "id": repo, "revision": sha,
            "adapter": str(args.adapter) if args.adapter else None, "vllm": vllm.__version__, "gpu": gpu, **e}
    params = SamplingParams(temperature=e["temperature"], max_tokens=e["max_tokens"], seed=0)

    try:
        for split in args.splits:
            pairs = requests_for("e1", split, args.sample)
            msgs = [[{"role": "system", "content": rq.instructions}, {"role": "user", "content": rq.input}]
                    for _, rq in pairs]
            outs = llm.chat(msgs, params, chat_template_kwargs={"enable_thinking": e["thinking"]}, use_tqdm=True)
            config = {**run_config("e1", split, info, args.sample), "phase": 4}
            recs = []
            with RunLog(f"phase4_{split}_{name}_{args.label}", config, seed=0) as log:
                for (item, rq), o in zip(pairs, outs):
                    rec = record(item, rq, o.outputs[0].text, {
                        "model_version": f"{repo}@{sha[:12]}+{args.label}",
                        "input_tokens": len(o.prompt_token_ids), "output_tokens": len(o.outputs[0].token_ids),
                        "cost": 0.0, "cache_hit": False})
                    recs.append(rec)
                    log.write(rec)
            print(f"{args.label} {split}: {summary(recs)} -> {log.path.name}", flush=True)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
