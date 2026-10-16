"""Items, experiments and the response-record format shared by every Phase 2 runner.

The API runner (scripts/phase2_run.py) and the Colab vLLM notebook both build
requests with `requests_for` and write one `record(...)` per response, so the
scorer (scripts/phase2_score.py) reads every model's run log the same way.
"""
import json
import random
from pathlib import Path

from core import vtg
from core.prompts import INSTRUCTIONS, LOCATION_SEED, PROMPT_VERSION, SOLVE_INSTRUCTIONS, build_request, parse_response, parse_solve

ROOT = Path(__file__).resolve().parent.parent
SYNTH = ROOT / "data" / "synthetic"
SYNTH_SPLITS = ("dev", "test_seen", "test_heldout")
VTG_SPLITS = ("vtg_dev", "vtg_test")
SAMPLE_SEED = 20261028

# experiment -> (conditions, allowed splits, incorrect items only)
EXPERIMENTS = {
    "e1": (("none",), SYNTH_SPLITS + VTG_SPLITS, False),
    "e2": (("true",), SYNTH_SPLITS, True),
    "e3": (("off1", "rand"), SYNTH_SPLITS, True),
    "solve": (("solve",), ("dev", "test_seen"), False),
}


def load_synthetic(split: str) -> list[dict]:
    rows = [json.loads(line) for line in (SYNTH / f"{split}.jsonl").open(encoding="utf-8")]
    for r in rows:
        r["source"] = "synthetic"
    return rows


def load_vtg(split: str) -> list[dict]:
    rows = vtg.load_rows()
    ids = vtg.load_split()[split.removeprefix("vtg_")]
    # Lenient labels: every teacher label given to the same solution (same problem and steps).
    labels: dict[tuple, set] = {}
    for r in rows:
        labels.setdefault((r["problem"], tuple(r["steps"])), set()).add(r["first_error"])
    by_id = {r["id"]: r for r in rows}
    out = []
    for i in ids:
        r = dict(by_id[i])
        r.update(id=f"vtg-{i:04d}", source="vtg", split=split,
                 all_labels=sorted(labels[(r["problem"], tuple(r["steps"]))]))
        out.append(r)
    return out


def load_items(split: str) -> list[dict]:
    return load_vtg(split) if split in VTG_SPLITS else load_synthetic(split)


def sample(items: list[dict], n: int | None) -> list[dict]:
    """Fixed subsample keeping the clean/incorrect ratio; nested (a smaller n is a subset of a larger one)."""
    if not n or n >= len(items):
        return items
    rng = random.Random(SAMPLE_SEED)
    order = sorted(items, key=lambda r: r["id"])
    rng.shuffle(order)
    clean = [r for r in order if r["first_error"] == 0]
    wrong = [r for r in order if r["first_error"] != 0]
    n_clean = round(n * len(clean) / len(items))
    keep = {r["id"] for r in clean[:n_clean] + wrong[:n - n_clean]}
    return [r for r in items if r["id"] in keep]


def requests_for(exp: str, split: str, n: int | None = None):
    conditions, splits, incorrect_only = EXPERIMENTS[exp]
    if split not in splits:
        raise ValueError(f"{exp} does not run on {split}")
    items = load_items(split)
    if incorrect_only:
        items = [r for r in items if r["first_error"] != 0]
    items = sample(items, n)
    return [(item, build_request(item, c)) for item in items for c in conditions]


def run_config(exp: str, split: str, model: dict, n: int | None) -> dict:
    return {"phase": 2, "exp": exp, "split": split, "sample": n, "model": model,
            "prompt_version": PROMPT_VERSION, "location_seed": LOCATION_SEED, "sample_seed": SAMPLE_SEED,
            "instructions": SOLVE_INSTRUCTIONS if exp == "solve" else INSTRUCTIONS}


def record(item: dict, req, text: str, meta: dict) -> dict:
    """One response record. `meta` carries model version, token usage, cost and cache flag."""
    rec = {"type": "response", "id": item["id"], "split": item["split"], "condition": req.condition,
           "supplied": req.supplied, "gold": item["first_error"], "n_steps": len(item["steps"]),
           "input": req.input, "output": text, **meta}
    if req.condition == "solve":
        rec["answer"] = parse_solve(text)
        rec["gold_answer"] = item.get("answer")
    else:
        p = parse_response(text)
        rec["pred"], rec["feedback"] = p.step, p.feedback
    return rec
