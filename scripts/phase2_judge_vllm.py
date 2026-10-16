"""Run the Phase 2 feedback judge (core/judge.py) with vLLM on the E1/E2 run logs.

    python scripts/phase2_judge_vllm.py --grid dev     # freeze the judge prompt on dev
    python scripts/phase2_judge_vllm.py --grid test

Reads the newest E1/E2 run log of every (split, model) in runs/ and judges each
feedback sentence:
  faith  E1 responses that flag a step (synthetic tests and VtG)
  diag   E1 and E2 responses on incorrect synthetic items
One log per (task, split, judged model): runs/<stamp>_phase2judge_<task>_<split>_<model>.jsonl.
The judge is Qwen3.5-27B with the open-model settings of config/phase2.json, but
with a short output budget.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.judge import DIAG_INSTRUCTIONS, FAITH_INSTRUCTIONS, JUDGE_VERSION, diag_request, faith_request, parse_judge  # noqa: E402
from core.llm import load_config  # noqa: E402
from core.phase2 import load_items  # noqa: E402
from core.runlog import RunLog  # noqa: E402
from scripts.phase2_run_vllm import load  # noqa: E402
from scripts.phase2_score import load_runs  # noqa: E402

JUDGE = "qwen-27b"
MAX_TOKENS = 32
# task -> [(source exp, split)]
GRIDS = {
    "dev": {"faith": [("e1", "dev"), ("e1", "vtg_dev")], "diag": [("e1", "dev"), ("e2", "dev")]},
    "test": {"faith": [("e1", "test_seen"), ("e1", "test_heldout"), ("e1", "vtg_test")],
             "diag": [("e1", "test_seen"), ("e1", "test_heldout"), ("e2", "test_seen"), ("e2", "test_heldout")]},
}


def judge_requests(task: str, exp: str, split: str, records: dict) -> list:
    items = {it["id"]: it for it in load_items(split)}
    out = []
    for (i, cond), r in sorted(records.items()):
        it = items.get(i)
        if it is None or not r.get("feedback"):
            continue
        if task == "faith" and r["pred"]:
            out.append((r, faith_request(it, r["feedback"], exp, cond)))
        elif task == "diag" and it["first_error"]:
            out.append((r, diag_request(it, r["feedback"], exp, cond)))
    return out


def run(llm, info: dict, task: str, exp: str, split: str, model: str, src: dict) -> str:
    from vllm import SamplingParams

    pairs = judge_requests(task, exp, split, src["records"])
    msgs = [[{"role": "system", "content": rq.instructions}, {"role": "user", "content": rq.input}] for _, rq in pairs]
    params = SamplingParams(temperature=info["temperature"], max_tokens=MAX_TOKENS, seed=0)
    outs = llm.chat(msgs, params, chat_template_kwargs={"enable_thinking": info["thinking"]}, use_tqdm=True)
    config = {"phase": 2, "task": task, "source_exp": exp, "split": split, "judged_model": model,
              "judged_run": src["path"], "judge": {**info, "max_tokens": MAX_TOKENS}, "judge_version": JUDGE_VERSION,
              "instructions": FAITH_INSTRUCTIONS if task == "faith" else DIAG_INSTRUCTIONS}
    parsed = 0
    with RunLog(f"phase2judge_{task}_{exp}_{split}_{model}", config, seed=0) as log:
        for (r, rq), o in zip(pairs, outs):
            verdict = parse_judge(task, o.outputs[0].text)
            parsed += verdict is not None
            log.write({"type": "judgement", "task": task, "id": rq.item_id, "source_exp": exp,
                       "condition": rq.condition, "judged_model": model, "flagged": r["pred"],
                       "input": rq.input, "output": o.outputs[0].text, "verdict": verdict,
                       "judge_version": JUDGE_VERSION, "model_version": f"{info['id']}@{info['revision'][:12]}"})
    return f"{task} {exp}/{split}/{model}: {len(pairs)} judged, {parsed} parsed -> {log.path.name}"


def main():
    config = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True, choices=sorted(GRIDS))
    ap.add_argument("--fallback", action="store_true")
    args = ap.parse_args()

    runs = load_runs()
    todo = [(task, exp, split, m) for task, pairs in GRIDS[args.grid].items() for exp, split in pairs
            for (e, s, m) in sorted(runs) if (e, s) == (exp, split)]
    if not todo:
        sys.exit("no E1/E2 run logs in runs/ for this grid")
    llm, info = load(JUDGE, config["open_models"][JUDGE], config["open_sampling"], args.fallback)
    print(json.dumps(info))
    for task, exp, split, m in todo:
        print(run(llm, info, task, exp, split, m, runs[(exp, split, m)]), flush=True)


if __name__ == "__main__":
    main()
