"""Gate 1: the SymPy checker against the generator's labels.

The generator labels each item from exact Fraction arithmetic on its states; the
checker only sees the rendered text. Gate: on 2,000 items (1,500 incorrect, 500
clean, drawn from all splits) the checker returns the injected step on 100% of
incorrect items and 0 on 100% of clean items. The same check is also run on every
item, and 50 items are drawn for hand checking (notes/phase1_hand_check.md).
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.checker import check, solution_set  # noqa: E402
from core.runlog import RunLog  # noqa: E402

SEED = 1
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "synthetic"
OUT = ROOT / "results" / "phase1" / "gate.json"
HAND = ROOT / "notes" / "phase1_hand_check.md"
SPLITS = ["train", "dev", "test_seen", "test_heldout"]


def load():
    return [json.loads(line) for s in SPLITS for line in (DATA / f"{s}.jsonl").open(encoding="utf-8")]


def verify(r) -> dict:
    res = check(r["problem"], r["steps"])
    out = {"id": r["id"], "gold": r["first_error"], "checker": res.first_error,
           "statuses": [s.status for s in res.steps]}
    out["match"] = res.first_error == r["first_error"] and res.complete
    if r["first_error"]:
        # No accidental recovery: no step from the error on has the correct solution set.
        truth = solution_set(r["answer"])
        out["recovered"] = any(solution_set(t) == truth for t in r["steps"][r["first_error"] - 1:])
        out["match"] = out["match"] and not out["recovered"]
    return out


def summarise(results):
    inc = [v for v in results if v["gold"]]
    clean = [v for v in results if not v["gold"]]
    return {
        "n": len(results),
        "incorrect": len(inc),
        "clean": len(clean),
        "incorrect_located": sum(v["match"] for v in inc) / len(inc),
        "clean_no_error": sum(v["match"] for v in clean) / len(clean),
        "recovered": sum(v.get("recovered", False) for v in inc),
        "unreadable_or_incomparable_steps": sum(s not in ("same", "changed")
                                                for v in results for s in v["statuses"]),
        "mismatches": [v for v in results if not v["match"]][:20],
    }


def hand_sheet(items, rng):
    inc = rng.sample([r for r in items if r["first_error"]], 35)
    clean = rng.sample([r for r in items if not r["first_error"]], 15)
    pick = inc + clean
    rng.shuffle(pick)
    lines = ["# Phase 1 hand check: 50 generated items", "",
             f"Drawn with `random.Random({SEED})` from all four splits (35 incorrect, 15 clean). For each item, "
             "every step was re-derived by hand from the one before it. *Verdict* says whether the hand "
             "check agrees with the gold first-error step and misconception.", ""]
    for i, r in enumerate(pick, 1):
        lines.append(f"## {i}. `{r['id']}` ({r['start_type']}), gold step **{r['first_error']}**"
                     + (f", {r['misconception']}: {r['rule']}" if r["misconception"] else ", clean"))
        lines.append("")
        lines.append(f"- 0: `{r['problem']}`")
        for k, s in enumerate(r["steps"], 1):
            mark = "  ← injected" if k == r["first_error"] else ""
            lines.append(f"- {k}: `{s}`{mark}")
        lines.append(f"- correct answer: `{r['answer']}`")
        lines.append("- **Verdict:** _to fill_")
        lines.append("")
    return "\n".join(lines)


def main():
    items = load()
    rng = random.Random(SEED)
    gate_items = (rng.sample([r for r in items if r["first_error"]], 1500)
                  + rng.sample([r for r in items if not r["first_error"]], 500))
    config = {"seed": SEED, "gate_items": 2000, "data": {s: json.loads((DATA / "manifest.json").read_text())
                                                          ["splits"][s]["sha256"] for s in SPLITS}}
    with RunLog("phase1_gate", config, SEED) as log:
        gate = [verify(r) for r in gate_items]
        for v in gate:
            log.write({"type": "check", **v})
        ids = {r["id"] for r in gate_items}
        all_results = gate + [verify(r) for r in items if r["id"] not in ids]
        results = {"gate_2000": summarise(gate), "all_items": summarise(all_results),
                   "by_split": {s: summarise([v for v in all_results if v["id"].startswith(s + "-")])
                                for s in SPLITS},
                   "status_counts": dict(Counter(s for v in all_results for s in v["statuses"]))}
        results["gate_passed"] = (results["gate_2000"]["incorrect_located"] == 1.0
                                  and results["gate_2000"]["clean_no_error"] == 1.0)
        log.write({"type": "results", **results})
        results["run_log"] = log.path.name
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    if not HAND.exists():  # never overwrite a filled-in sheet
        HAND.write_text(hand_sheet(items, random.Random(SEED)), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "by_split"}, indent=2))


if __name__ == "__main__":
    main()
