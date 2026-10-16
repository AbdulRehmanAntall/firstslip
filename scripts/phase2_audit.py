"""Hand audits for Gate 2: the faithfulness extractor and the misconception mapping.

    python scripts/phase2_audit.py make     # writes notes/phase2_audit_{faithfulness,misconception}.csv
    python scripts/phase2_audit.py score    # agreement with the filled-in hand labels

`make` draws 100 E1 test responses for each audit (seeded, spread evenly over the
models; faithfulness also covers VtG). The extractor's or mapping's output is
hidden in the sheet. Fill in the `hand` column:
  faithfulness:   the step number the feedback talks about, or `none`
  misconception:  the misconception id the feedback describes (e.g. M14), or `none`
`score` reports agreement (Gate 2 needs >= 90% for the faithfulness extractor).
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.faithfulness import mentioned_step  # noqa: E402
from core.misconceptions import map_feedback  # noqa: E402
from core.phase2 import load_items  # noqa: E402
from core.stats import bootstrap_ci  # noqa: E402
from scripts.phase2_score import load_runs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes"
SEED = 20261102
N = 100
SHEETS = {"faithfulness": NOTES / "phase2_audit_faithfulness.csv",
          "misconception": NOTES / "phase2_audit_misconception.csv"}


def pool(splits, need_misconception: bool):
    runs = load_runs()
    by_model: dict[str, list] = {}
    for split in splits:
        items = {it["id"]: it for it in load_items(split)}
        for (exp, s, model), run in sorted(runs.items()):
            if exp != "e1" or s != split:
                continue
            for (i, _), r in sorted(run["records"].items()):
                it = items[i]
                if not r.get("feedback") or not r.get("pred"):
                    continue
                if need_misconception and not it.get("misconception"):
                    continue
                by_model.setdefault(model, []).append((model, it, r))
    rng = random.Random(SEED)
    per = N // max(1, len(by_model))
    chosen = []
    for model in sorted(by_model):
        chosen += rng.sample(by_model[model], min(per, len(by_model[model])))
    rest = [x for m in sorted(by_model) for x in by_model[m] if x not in chosen]
    chosen += rng.sample(rest, min(N - len(chosen), len(rest)))
    rng.shuffle(chosen)
    return chosen


def make():
    rows = pool(("test_seen", "test_heldout", "vtg_test"), need_misconception=False)
    with SHEETS["faithfulness"].open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["audit_id", "model", "item_id", "steps", "flagged", "feedback", "hand"])
        for k, (m, it, r) in enumerate(rows):
            steps = " | ".join(f"{j}: {s}" for j, s in enumerate(it["steps"], start=1))
            w.writerow([k, m, it["id"], steps, r["pred"], r["feedback"], ""])
    rows = pool(("test_seen", "test_heldout"), need_misconception=True)
    with SHEETS["misconception"].open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["audit_id", "model", "item_id", "problem", "steps", "feedback", "hand"])
        for k, (m, it, r) in enumerate(rows):
            steps = " | ".join(f"{j}: {s}" for j, s in enumerate(it["steps"], start=1))
            w.writerow([k, m, it["id"], it["problem"], steps, r["feedback"], ""])
    print("wrote", *SHEETS.values(), sep="\n  ")


def score():
    out = {}
    for name, path in SHEETS.items():
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        done = [r for r in rows if r["hand"].strip()]
        agree = []
        for r in done:
            hand = r["hand"].strip().lower()
            if name == "faithfulness":
                steps = [s.split(": ", 1)[1] for s in r["steps"].split(" | ")]
                auto = mentioned_step(r["feedback"], steps)
                agree.append(int(str(auto if auto is not None else "none") == hand))
            else:
                auto = map_feedback(r["feedback"])
                agree.append(int((auto or "none").lower() == hand))
        m, lo, hi = bootstrap_ci(agree) if agree else (0, 0, 0)
        out[name] = {"labelled": len(done), "of": len(rows), "agreement": m, "ci95": [lo, hi]}
    print(json.dumps(out, indent=2))
    (ROOT / "results" / "phase2").mkdir(parents=True, exist_ok=True)
    (ROOT / "results" / "phase2" / "audit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    {"make": make, "score": score}[sys.argv[1]]()
