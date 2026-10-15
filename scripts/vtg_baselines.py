"""Random and position-only baselines on VtG (Phase 0 gate).

Random: uniform guess over the solution's steps (expected accuracy is mean 1/n).
Position-only: the most common first-error step for each solution length,
fitted on VtG dev and scored on VtG test.
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from firstslip import vtg  # noqa: E402
from firstslip.runlog import RunLog  # noqa: E402
from firstslip.stats import bootstrap_ci  # noqa: E402

SEED = 0
OUT = Path(__file__).resolve().parent.parent / "results" / "phase0" / "vtg_baselines.json"


def fit_position_prior(rows):
    by_len: dict[int, Counter] = {}
    for r in rows:
        by_len.setdefault(len(r["steps"]), Counter())[r["first_error"]] += 1
    overall = Counter(r["first_error"] for r in rows)
    # Ties go to the earlier step so the rule is deterministic.
    mode = lambda c: min(c, key=lambda k: (-c[k], k))  # noqa: E731
    return {n: mode(c) for n, c in by_len.items()}, mode(overall)


def summarise(rows, preds):
    exact = [int(p == r["first_error"]) for r, p in zip(rows, preds)]
    within = [int(abs(p - r["first_error"]) <= 1) for r, p in zip(rows, preds)]
    acc, lo, hi = bootstrap_ci(exact, seed=SEED)
    w_acc, w_lo, w_hi = bootstrap_ci(within, seed=SEED)
    return {"n": len(rows), "first_error_acc": acc, "ci95": [lo, hi],
            "within_one_acc": w_acc, "within_one_ci95": [w_lo, w_hi]}


def expected_random(rows):
    exact = sum(1 / len(r["steps"]) for r in rows) / len(rows)
    within = sum(
        sum(abs(k - r["first_error"]) <= 1 for k in range(1, len(r["steps"]) + 1)) / len(r["steps"])
        for r in rows
    ) / len(rows)
    return {"first_error_acc": exact, "within_one_acc": within}


def main():
    rows = vtg.load_rows()
    split = vtg.load_split()
    by_id = {r["id"]: r for r in rows}
    dev = [by_id[i] for i in split["dev"]]
    test = [by_id[i] for i in split["test"]]
    test_no_nota = [r for r in test if r["error_category"] != vtg.NOTA]

    prior, fallback = fit_position_prior(dev)
    rng = random.Random(SEED)
    config = {"dataset": vtg.DATASET_ID, "split_seed": split["seed"], "bootstrap": 10_000,
              "step_convention": "1-based, 0 = no error"}

    results = {"config": config, "position_prior": {str(k): v for k, v in sorted(prior.items())},
               "position_fallback": fallback, "eval": {}}
    with RunLog("phase0_vtg_baselines", config, SEED) as log:
        for subset_name, subset in [("vtg_test", test), ("vtg_test_no_nota", test_no_nota),
                                    ("vtg_all", rows)]:
            rand_preds = [rng.randint(1, len(r["steps"])) for r in subset]
            pos_preds = [prior.get(len(r["steps"]), fallback) for r in subset]
            for r, rp, pp in zip(subset, rand_preds, pos_preds):
                log.write({"type": "pred", "subset": subset_name, "id": r["id"],
                           "gold": r["first_error"], "random": rp, "position": pp})
            results["eval"][subset_name] = {
                "random_expected": expected_random(subset),
                "random_sampled": summarise(subset, rand_preds),
                "position_only": summarise(subset, pos_preds),
            }
        # Per error category on the test split.
        cats = sorted({r["error_category"] for r in test})
        results["eval"]["vtg_test_by_category"] = {
            c: {"n": sum(r["error_category"] == c for r in test),
                "position_only_acc": sum(prior.get(len(r["steps"]), fallback) == r["first_error"]
                                         for r in test if r["error_category"] == c)
                / sum(r["error_category"] == c for r in test),
                "random_expected_acc": expected_random([r for r in test if r["error_category"] == c])["first_error_acc"]}
            for c in cats
        }
        log.write({"type": "results", **results})
        results["run_log"] = log.path.name

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(json.dumps(results["eval"], indent=2))
    print("prior:", results["position_prior"], "fallback:", fallback)


if __name__ == "__main__":
    main()
