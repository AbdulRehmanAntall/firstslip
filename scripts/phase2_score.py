"""Score Phase 2 run logs into the E1–E3 tables (and the H1 solve comparison).

Reads the newest run log for each (exp, split, model) in runs/ (API runs and the
Colab vLLM runs share one record format) and writes results/phase2/tables.json
and results/phase2/tables.md.

Metrics (PREREGISTRATION.md §5): first-error accuracy on incorrect items, clean
accuracy, error F1 (harmonic mean), within-one accuracy, misconception accuracy
(label and family), faithfulness, and the E3 deference rate. All intervals are
95% bootstrap CIs (10,000 resamples). Model comparisons use McNemar's exact test
with Holm correction within each experiment; differences use a paired bootstrap
on the items both conditions answered.

    python scripts/phase2_score.py            # test splits
    python scripts/phase2_score.py --dev      # dev splits (prompt freezing only)
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.checker import Unreadable, solution_set  # noqa: E402
from core.faithfulness import faithfulness_label  # noqa: E402
from core.judge import faith_label  # noqa: E402
from core.misconceptions import family, map_feedback  # noqa: E402
from core.phase2 import load_items  # noqa: E402
from core.stats import bootstrap_ci, holm, mcnemar, paired_bootstrap_diff  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OUT = ROOT / "results" / "phase2"
BASELINES = {"test_seen": ROOT / "results" / "phase1" / "synthetic_baselines.json",
             "test_heldout": ROOT / "results" / "phase1" / "synthetic_baselines.json",
             "vtg_test": ROOT / "results" / "phase0" / "vtg_baselines.json"}


def load_runs() -> dict:
    """{(exp, split, model): {(id, condition): record}} from the newest log of each triple."""
    newest: dict[tuple, Path] = {}
    for path in sorted(RUNS.glob("*_phase2_*.jsonl")):  # names start with a UTC stamp, so sorted = by time
        with path.open(encoding="utf-8") as f:
            head = json.loads(f.readline())
        c = head["config"]
        newest[(c["exp"], c["split"], c["model"]["name"])] = path
    out = {}
    for key, path in newest.items():
        recs = {}
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("type") == "response":
                recs[(r["id"], r["condition"])] = r
        out[key] = {"path": path.name, "records": recs}
    return out


def load_judgements() -> dict:
    """{(task, exp, split, model): {(id, condition): judgement}} from the newest judge log of each."""
    newest: dict[tuple, Path] = {}
    for path in sorted(RUNS.glob("*_phase2judge_*.jsonl")):
        with path.open(encoding="utf-8") as f:
            c = json.loads(f.readline())["config"]
        newest[(c["task"], c["source_exp"], c["split"], c["judged_model"])] = path
    out = {}
    for key, path in newest.items():
        recs = {}
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("type") == "judgement":
                recs[(r["id"], r["condition"])] = r
        out[key] = {"path": path.name, "records": recs}
    return out


def ci(xs):
    if not xs:
        return None
    m, lo, hi = bootstrap_ci(xs)
    return {"n": len(xs), "mean": m, "ci95": [lo, hi]}


def f1(a, b):
    return 0.0 if a + b == 0 else 2 * a * b / (a + b)


def same_answer(pred: str | None, gold: str | None) -> bool:
    if not pred or not gold:
        return False
    try:
        return solution_set(pred if "=" in pred else f"x = {pred}") == solution_set(gold)
    except Unreadable:
        return False


def localization(recs: dict, items: dict, condition: str = "none") -> dict:
    """E1-style metrics on one (split, model, condition)."""
    rows = [(items[i], r) for (i, c), r in recs.items() if c == condition and i in items]
    wrong = [(it, r) for it, r in rows if it["first_error"]]
    clean = [(it, r) for it, r in rows if not it["first_error"]]
    exact = [int(r["pred"] == it["first_error"]) for it, r in wrong]
    within = [int(r["pred"] is not None and abs(r["pred"] - it["first_error"]) <= 1) for it, r in wrong]
    out = {"n": len(rows), "parse_rate": ci([int(r["pred"] is not None) for _, r in rows]),
           "first_error_acc": ci(exact), "within_one_acc": ci(within)}
    if clean:
        clean_acc = [int(r["pred"] == 0) for _, r in clean]
        out["clean_acc"] = ci(clean_acc)
        out["error_f1"] = f1(sum(exact) / max(len(exact), 1), sum(clean_acc) / len(clean_acc))
    if wrong and "all_labels" in wrong[0][0]:
        out["lenient_acc"] = ci([int(r["pred"] in it["all_labels"]) for it, r in wrong])
        no_nota = [(it, r) for it, r in wrong if it["error_category"] != "None of the above"]
        out["first_error_acc_no_nota"] = ci([int(r["pred"] == it["first_error"]) for it, r in no_nota])
    if wrong and wrong[0][0].get("misconception"):
        labels = [map_feedback(r["feedback"]) for _, r in wrong]
        out["misconception_acc"] = ci([int(lab == it["misconception"]) for (it, _), lab in zip(wrong, labels)])
        out["family_acc"] = ci([int(family(lab) == it["family"]) for (it, _), lab in zip(wrong, labels)])
        out["unmapped_rate"] = sum(lab is None for lab in labels) / len(labels)
    faith = [faithfulness_label(r["pred"], r["feedback"], it["steps"]) for it, r in rows]
    faith = [f for f in faith if f]
    if faith:
        out["faithful"] = ci([int(f == "faithful") for f in faith])
        out["unfaithful"] = ci([int(f == "unfaithful") for f in faith])
        out["unspecified_rate"] = sum(f == "unspecified" for f in faith) / len(faith)
    out["by_n_steps"] = {n: sum(r["pred"] == it["first_error"] for it, r in wrong if len(it["steps"]) == n)
                         / max(1, sum(len(it["steps"]) == n for it, _ in wrong))
                         for n in sorted({len(it["steps"]) for it, _ in wrong})}
    return out


def paired(recs_a, recs_b, cond_a, cond_b, items, metric):
    """Paired outcomes on the items both answered."""
    ids = sorted(i for (i, c) in recs_a if c == cond_a and (i, cond_b) in recs_b and i in items)
    a = [metric(items[i], recs_a[(i, cond_a)]) for i in ids]
    b = [metric(items[i], recs_b[(i, cond_b)]) for i in ids]
    return a, b


def compare(a, b) -> dict:
    d, lo, hi = paired_bootstrap_diff(a, b) if a else (0.0, 0.0, 0.0)
    return {"n": len(a), "diff": d, "ci95": [lo, hi], **mcnemar(a, b)}


def apply_holm(tests: list[dict]) -> None:
    for t, p in zip(tests, holm([t["p"] for t in tests])):
        t["p_holm"] = p


def exact_hit(it, r):
    return int(r["pred"] == it["first_error"])


def misc_hit(it, r):
    return int(map_feedback(r["feedback"]) == it["misconception"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    args = ap.parse_args()
    syn = ("dev",) if args.dev else ("test_seen", "test_heldout")
    vtg_split = "vtg_dev" if args.dev else "vtg_test"

    runs = load_runs()
    models = sorted({m for (_, _, m) in runs})
    items = {s: {it["id"]: it for it in load_items(s)} for s in syn + (vtg_split,)}
    res = {"runs": {"/".join(k): v["path"] for k, v in runs.items()}, "e1": {}, "e1_tests": [],
           "h1": {}, "e2": {}, "e2_tests": [], "e3": {}}

    # E1: localization, every model x split, plus pairwise McNemar between models.
    for split in syn + (vtg_split,):
        res["e1"][split] = {m: localization(runs[("e1", split, m)]["records"], items[split])
                            for m in models if ("e1", split, m) in runs}
        if split in BASELINES and BASELINES[split].exists():
            res["e1"][split]["_baselines"] = json.loads(BASELINES[split].read_text())["eval"].get(split)
        present = [m for m in models if ("e1", split, m) in runs]
        for i, ma in enumerate(present):
            for mb in present[i + 1:]:
                a, b = paired(runs[("e1", split, ma)]["records"], runs[("e1", split, mb)]["records"],
                              "none", "none", {k: v for k, v in items[split].items() if v["first_error"]}, exact_hit)
                res["e1_tests"].append({"split": split, "a": ma, "b": mb, "metric": "first_error_acc", **compare(a, b)})
    apply_holm(res["e1_tests"])

    # H1: localization (incorrect items) vs solving the same equation.
    solve_split = "dev" if args.dev else "test_seen"
    for m in models:
        if ("solve", solve_split, m) in runs and ("e1", solve_split, m) in runs:
            s_recs, e_recs = runs[("solve", solve_split, m)]["records"], runs[("e1", solve_split, m)]["records"]
            wrong = {k: v for k, v in items[solve_split].items() if v["first_error"]}
            ids = sorted(i for i in wrong if (i, "none") in e_recs and (i, "solve") in s_recs)
            loc = [exact_hit(wrong[i], e_recs[(i, "none")]) for i in ids]
            sol = [int(same_answer(s_recs[(i, "solve")]["answer"], wrong[i]["answer"])) for i in ids]
            res["h1"][m] = {"localization_acc": ci(loc), "solve_acc": ci(sol), "loc_minus_solve": compare(loc, sol)}

    # E2: misconception accuracy with vs without the checker's location (E1 = no location).
    for split in syn:
        res["e2"][split] = {}
        wrong = {k: v for k, v in items[split].items() if v["first_error"]}
        for m in models:
            if ("e2", split, m) not in runs:
                continue
            given = runs[("e2", split, m)]["records"]
            res["e2"][split][m] = {"given": localization(given, wrong, "true")}
            if ("e1", split, m) in runs:
                none = runs[("e1", split, m)]["records"]
                a, b = paired(given, none, "true", "none", wrong, misc_hit)
                t = {"split": split, "model": m, "metric": "misconception_acc (given - none)", **compare(a, b)}
                res["e2_tests"].append(t)
                fa, fb = paired(given, none, "true", "none", wrong,
                                lambda it, r: int(family(map_feedback(r["feedback"])) == it["family"]))
                res["e2"][split][m]["family_given_minus_none"] = compare(fa, fb)
    apply_holm(res["e2_tests"])

    # E3: deference to a wrong supplied location; "true" comes from E2.
    for split in syn:
        res["e3"][split] = {}
        wrong = {k: v for k, v in items[split].items() if v["first_error"]}
        for m in models:
            if ("e3", split, m) not in runs:
                continue
            recs = runs[("e3", split, m)]["records"]
            row = {}
            for cond in ("off1", "rand"):
                rs = [(wrong[i], r) for (i, c), r in recs.items() if c == cond and i in wrong]
                row[cond] = {"deference": ci([int(r["pred"] == r["supplied"]) for _, r in rs]),
                             "first_error_acc": ci([int(r["pred"] == it["first_error"]) for it, r in rs]),
                             "other_step": ci([int(r["pred"] not in (r["supplied"], it["first_error"])) for it, r in rs])}
            if ("e2", split, m) in runs:
                g = runs[("e2", split, m)]["records"]
                row["true"] = {"first_error_acc": ci([exact_hit(wrong[i], r) for (i, c), r in g.items() if i in wrong])}
            res["e3"][split][m] = row

    # Judge-based feedback metrics (Amendment 5): faithfulness on E1, diagnosis on E1 and E2.
    judged = load_judgements()
    res["judge"] = {"runs": {"/".join(k): v["path"] for k, v in judged.items()}, "faith": {}, "diag": {}, "h2_tests": []}
    for split in syn + (vtg_split,):
        for m in models:
            j = judged.get(("faith", "e1", split, m))
            if not j:
                continue
            recs = list(j["records"].values())
            labs = [x for x in (faith_label(r["flagged"], r["verdict"]) for r in recs) if x]
            res["judge"]["faith"].setdefault(split, {})[m] = {
                "n": len(labs), "parse_rate": sum(r["verdict"] is not None for r in recs) / max(1, len(recs)),
                "faithful": ci([int(x == "faithful") for x in labs]), "unfaithful": ci([int(x == "unfaithful") for x in labs]),
                "unspecified_rate": sum(x == "unspecified" for x in labs) / max(1, len(labs))}
    for split in syn:
        for m in models:
            none, given = judged.get(("diag", "e1", split, m)), judged.get(("diag", "e2", split, m))
            row = {}
            for name, j, cond in (("none", none, "none"), ("given", given, "true")):
                if j:
                    row[name] = ci([int(r["verdict"] is True) for (_, c), r in j["records"].items() if c == cond])
            if none and given:
                ids = sorted(i for (i, c) in given["records"] if c == "true" and (i, "none") in none["records"])
                a = [int(given["records"][(i, "true")]["verdict"] is True) for i in ids]
                b = [int(none["records"][(i, "none")]["verdict"] is True) for i in ids]
                res["judge"]["h2_tests"].append({"split": split, "model": m, "metric": "diagnosis_acc (given - none)", **compare(a, b)})
            if row:
                res["judge"]["diag"].setdefault(split, {})[m] = row
    apply_holm(res["judge"]["h2_tests"])

    OUT.mkdir(parents=True, exist_ok=True)
    stem = "tables_dev" if args.dev else "tables"
    (OUT / f"{stem}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    (OUT / f"{stem}.md").write_text(to_markdown(res), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(to_markdown(res))


def pct(c, key="mean"):
    if not c:
        return "—"
    return f"{100 * c[key]:.1f} ({100 * c['ci95'][0]:.1f}–{100 * c['ci95'][1]:.1f})"


def to_markdown(res) -> str:
    L = ["# Phase 2 tables", "", "95% bootstrap CIs in brackets. n = items scored.", ""]
    L += ["## E1 — prompted localization", ""]
    for split, by_model in res["e1"].items():
        L += [f"### {split}", "", "| Model | n | First-error acc. | Clean acc. | Error F1 | Within-one | Misconception (label) | Family | Unfaithful | Parse |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for m, r in by_model.items():
            if m == "_baselines":
                continue
            f1_cell = f"{100 * r['error_f1']:.1f}" if "error_f1" in r else "—"
            L.append(f"| {m} | {r['n']} | {pct(r['first_error_acc'])} | {pct(r.get('clean_acc'))} | {f1_cell} | "
                     f"{pct(r['within_one_acc'])} | {pct(r.get('misconception_acc'))} | {pct(r.get('family_acc'))} | "
                     f"{pct(r.get('unfaithful'))} | {pct(r['parse_rate'])} |")
        if "_baselines" in by_model and by_model["_baselines"]:
            b = by_model["_baselines"]
            L.append(f"| *random (expected)* | | {100 * b['random_expected']['first_error_acc']:.1f} | | | | | | | |")
            L.append(f"| *position-only* | | {100 * b['position_only']['first_error_acc']:.1f} | | | | | | | |")
        vt = [(m, r) for m, r in by_model.items() if m != "_baselines" and "lenient_acc" in r]
        if vt:
            L += ["", "| Model | Without NOTA | Lenient (any teacher label) |", "|---|---|---|"]
            L += [f"| {m} | {pct(r['first_error_acc_no_nota'])} | {pct(r['lenient_acc'])} |" for m, r in vt]
        L.append("")
    if res["e1_tests"]:
        L += ["Model vs model (first-error acc., McNemar, Holm within E1):", "", "| Split | A | B | n | A − B | p (Holm) |", "|---|---|---|---|---|---|"]
        L += [f"| {t['split']} | {t['a']} | {t['b']} | {t['n']} | {100 * t['diff']:+.1f} ({100 * t['ci95'][0]:+.1f}–{100 * t['ci95'][1]:+.1f}) | {t['p_holm']:.3g} |" for t in res["e1_tests"]]
        L.append("")
    if res["h1"]:
        L += ["## H1 — localization vs solving (same equations, incorrect items)", "", "| Model | Localization | Solving | Loc − solve | p |", "|---|---|---|---|---|"]
        for m, h in res["h1"].items():
            d = h["loc_minus_solve"]
            L.append(f"| {m} | {pct(h['localization_acc'])} | {pct(h['solve_acc'])} | {100 * d['diff']:+.1f} ({100 * d['ci95'][0]:+.1f}–{100 * d['ci95'][1]:+.1f}) | {d['p']:.3g} |")
        L.append("")
    if res["e2_tests"]:
        L += ["## E2 — checker location given vs not given (misconception acc.)", "", "| Split | Model | n | Given − none | p (Holm) | Given: first-error acc. |", "|---|---|---|---|---|---|"]
        for t in res["e2_tests"]:
            g = res["e2"][t["split"]][t["model"]]["given"]
            L.append(f"| {t['split']} | {t['model']} | {t['n']} | {100 * t['diff']:+.1f} ({100 * t['ci95'][0]:+.1f}–{100 * t['ci95'][1]:+.1f}) | {t['p_holm']:.3g} | {pct(g['first_error_acc'])} |")
        L.append("")
    if any(res["e3"].values()):
        L += ["## E3 — corrupted tool", "", "| Split | Model | Acc. (true loc.) | Deference (one-off) | Deference (random wrong) | Acc. (one-off) | Acc. (random wrong) |", "|---|---|---|---|---|---|---|"]
        for split, by_model in res["e3"].items():
            for m, r in by_model.items():
                L.append(f"| {split} | {m} | {pct(r.get('true', {}).get('first_error_acc'))} | {pct(r['off1']['deference'])} | {pct(r['rand']['deference'])} | "
                         f"{pct(r['off1']['first_error_acc'])} | {pct(r['rand']['first_error_acc'])} |")
        L.append("")
    jd = res.get("judge", {})
    if jd.get("faith"):
        L += ["## Judge — faithfulness (E1, Amendment 5)", "", "| Split | Model | n | Faithful | Unfaithful | Unspecified | Parse |", "|---|---|---|---|---|---|---|"]
        for split, by_model in jd["faith"].items():
            for m, r in by_model.items():
                L.append(f"| {split} | {m} | {r['n']} | {pct(r['faithful'])} | {pct(r['unfaithful'])} | {100 * r['unspecified_rate']:.1f} | {100 * r['parse_rate']:.1f} |")
        L.append("")
    if jd.get("diag"):
        L += ["## Judge — correct diagnosis (E1 no location vs E2 location given, Amendment 5)", "", "| Split | Model | None | Given | Given − none | p (Holm) |", "|---|---|---|---|---|---|"]
        tests = {(t["split"], t["model"]): t for t in jd["h2_tests"]}
        for split, by_model in jd["diag"].items():
            for m, r in by_model.items():
                t = tests.get((split, m))
                d = f"{100 * t['diff']:+.1f} ({100 * t['ci95'][0]:+.1f}–{100 * t['ci95'][1]:+.1f}) | {t['p_holm']:.3g}" if t else "— | —"
                L.append(f"| {split} | {m} | {pct(r.get('none'))} | {pct(r.get('given'))} | {d} |")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
