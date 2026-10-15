"""Random and position-only baselines on the synthetic test splits (Phase 1).

Scored like VtG (first-error accuracy on incorrect items) so the numbers sit next
to scripts/vtg_baselines.py. Random: uniform guess over the solution's steps.
Position-only: the most common first-error step for each solution length, fitted
on synthetic dev and scored on test (the anti-hypothesis check in PREREGISTRATION.md).
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.runlog import RunLog  # noqa: E402
from scripts.vtg_baselines import expected_random, fit_position_prior, summarise  # noqa: E402

SEED = 0
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "synthetic"
OUT = ROOT / "results" / "phase1" / "synthetic_baselines.json"


def load(split):
    rows = [json.loads(line) for line in (DATA / f"{split}.jsonl").open(encoding="utf-8")]
    return [r for r in rows if r["first_error"]]  # first-error accuracy: incorrect items only


def main():
    dev = load("dev")
    prior, fallback = fit_position_prior(dev)
    rng = random.Random(SEED)
    config = {"fit": "synthetic dev (incorrect items)", "bootstrap": 10_000,
              "data": json.loads((DATA / "manifest.json").read_text())["config"]}
    results = {"position_prior": {str(k): v for k, v in sorted(prior.items())},
               "position_fallback": fallback, "eval": {}}
    with RunLog("phase1_synthetic_baselines", config, SEED) as log:
        for split in ("test_seen", "test_heldout"):
            rows = load(split)
            rand = [rng.randint(1, len(r["steps"])) for r in rows]
            pos = [prior.get(len(r["steps"]), fallback) for r in rows]
            for r, rp, pp in zip(rows, rand, pos):
                log.write({"type": "pred", "split": split, "id": r["id"], "gold": r["first_error"],
                           "random": rp, "position": pp})
            results["eval"][split] = {"random_expected": expected_random(rows),
                                      "random_sampled": summarise(rows, rand),
                                      "position_only": summarise(rows, pos)}
        log.write({"type": "results", **results})
        results["run_log"] = log.path.name
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
