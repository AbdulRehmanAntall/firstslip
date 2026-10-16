"""Run Phase 2 experiments with the open Qwen models through vLLM (GPU, e.g. Colab A100).

    python scripts/phase2_run_vllm.py --grid dev                    # all open models
    python scripts/phase2_run_vllm.py --grid test --models qwen-27b
    python scripts/phase2_run_vllm.py --grid dev --fallback         # Qwen3 / GPTQ fallbacks

Builds the same requests as the API runner (core.phase2) and writes the same
record format, so scripts/phase2_score.py scores every model alike. Each model is
pinned to its Hugging Face commit SHA; the SHA, vLLM version and GPU are written
into every run-log header. Decoding is greedy with thinking off (config/phase2.json).
"""
import argparse
import gc
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.llm import load_config  # noqa: E402
from core.phase2 import GRIDS, record, requests_for, run_config  # noqa: E402
from core.runlog import RunLog  # noqa: E402


def load(name: str, spec: dict, sampling: dict, fallback: bool):
    import vllm
    from huggingface_hub import model_info

    repo = spec["fallback" if fallback else "model"]
    sha = model_info(repo).sha
    kwargs = {}
    if "Qwen3.5" in repo:  # image-text models: text only, so no memory goes to vision inputs
        kwargs["limit_mm_per_prompt"] = {"image": 0, "video": 0}
    llm = vllm.LLM(model=repo, revision=sha, max_model_len=sampling["max_model_len"],
                   gpu_memory_utilization=spec.get("gpu_memory_utilization", 0.85), seed=0, **kwargs)
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True).strip()
    info = {"name": name, "id": repo, "revision": sha, "fallback": fallback,
            "vllm": vllm.__version__, "gpu": gpu, **sampling}
    return llm, info


def run(llm, info: dict, exp: str, split: str, sample: int | None) -> str:
    from vllm import SamplingParams

    pairs = requests_for(exp, split, sample)
    msgs = [[{"role": "system", "content": rq.instructions}, {"role": "user", "content": rq.input}] for _, rq in pairs]
    params = SamplingParams(temperature=info["temperature"], max_tokens=info["max_tokens"], seed=0)
    outs = llm.chat(msgs, params, chat_template_kwargs={"enable_thinking": info["thinking"]}, use_tqdm=True)
    parsed = 0
    with RunLog(f"phase2_{exp}_{split}_{info['name']}", run_config(exp, split, info, sample), seed=0) as log:
        for (item, rq), o in zip(pairs, outs):
            rec = record(item, rq, o.outputs[0].text, {
                "model_version": f"{info['id']}@{info['revision'][:12]}",
                "input_tokens": len(o.prompt_token_ids), "output_tokens": len(o.outputs[0].token_ids),
                "cost": 0.0, "cache_hit": False})
            parsed += rec.get("pred", rec.get("answer")) is not None
            log.write(rec)
    return f"{exp}/{split}: {len(pairs)} requests, {parsed} parsed -> {log.path.name}"


def main():
    config = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True, choices=sorted(GRIDS))
    ap.add_argument("--models", nargs="+", default=list(config["open_models"]), choices=list(config["open_models"]))
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--fallback", action="store_true")
    args = ap.parse_args()

    import torch
    for name in args.models:
        llm, info = load(name, config["open_models"][name], config["open_sampling"], args.fallback)
        print(json.dumps(info))
        for exp, split in GRIDS[args.grid]:
            print(run(llm, info, exp, split, args.sample), flush=True)
        del llm
        gc.collect()
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
