"""Score the Phase 4 (E4) evaluation logs: Base vs. SFT vs. GRPO (or RFT), three seeds each.

    python scripts/phase4_score.py

Reads the newest runs/*_phase4_<split>_* log for each (split, label). Main-table
labels are "base" and "<method>-s<seed>"; checkpoint labels such as
"grpo-s0-step100" (go/no-go) are listed separately. Writes
results/phase4/tables.{json,md} and the position check, f_position.png.

Per seed: the Phase 2 metrics (first-error, clean, error F1, within-one).
Per condition: mean and sd over seeds. Pre-registered tests (PREREGISTRATION.md §1):
  H3     gain over base on test-seen error F1 > between-seed sd ("improves"), and
         held-out gain >= half the seen gain ("holds its gain").
  Anti   held-out first-error accuracy must beat the position-only baseline
         (37.5%, Amendment 1); the predicted-step distribution is plotted against gold.
  H4     VtG-test first-error gain over base > sd, and smaller than the test-seen gain.
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.phase2 import load_items  # noqa: E402
from phase2_score import localization  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OUT = ROOT / "results" / "phase4"
MAIN = re.compile(r"^(base|(sft|grpo|rft)-s\d+)$")
METRICS = ("first_error_acc", "clean_acc", "error_f1", "within_one_acc")
SPLITS = ("dev", "test_seen", "test_heldout", "vtg_test")


def load_runs(runs: Path | None = None) -> dict:
    """{(split, label): {(id, condition): record}} from the newest log of each pair."""
    runs = runs or RUNS
    newest: dict[tuple, Path] = {}
    for path in sorted(runs.glob("*_phase4_*.jsonl")):
        with path.open(encoding="utf-8") as f:
            c = json.loads(f.readline())["config"]
        newest[(c["split"], c["model"]["label"])] = path
    out = {}
    for key, path in newest.items():
        recs = {}
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("type") == "response":
                recs[(r["id"], r["condition"])] = r
        out[key] = recs
    return out


def value(m: dict, key: str) -> float | None:
    v = m.get(key)
    return v["mean"] if isinstance(v, dict) else v


def condition(label: str) -> str:
    return label.split("-")[0]


def aggregate(per_label: dict) -> dict:
    """{condition: {metric: {mean, sd, seeds}}} from {label: metrics}."""
    by_cond = defaultdict(list)
    for label, m in per_label.items():
        by_cond[condition(label)].append(m)
    out = {}
    for cond, ms in by_cond.items():
        out[cond] = {}
        for k in METRICS:
            xs = [value(m, k) for m in ms if value(m, k) is not None]
            if xs:
                out[cond][k] = {"mean": statistics.mean(xs), "sd": statistics.stdev(xs) if len(xs) > 1 else 0.0,
                                "seeds": xs}
    return out


def h3(agg: dict, cond: str) -> dict | None:
    seen, held = agg.get("test_seen", {}), agg.get("test_heldout", {})
    if cond not in seen or "base" not in seen or cond not in held or "base" not in held:
        return None
    g_seen = seen[cond]["error_f1"]["mean"] - seen["base"]["error_f1"]["mean"]
    g_held = held[cond]["error_f1"]["mean"] - held["base"]["error_f1"]["mean"]
    return {"seen_gain": g_seen, "seen_sd": seen[cond]["error_f1"]["sd"],
            "improves": g_seen > seen[cond]["error_f1"]["sd"],
            "heldout_gain": g_held, "heldout_sd": held[cond]["error_f1"]["sd"],
            "holds_gain": g_seen > 0 and g_held >= 0.5 * g_seen}


def h4(agg: dict, cond: str) -> dict | None:
    vtg, seen = agg.get("vtg_test", {}), agg.get("test_seen", {})
    if cond not in vtg or "base" not in vtg or cond not in seen or "base" not in seen:
        return None
    g = vtg[cond]["first_error_acc"]["mean"] - vtg["base"]["first_error_acc"]["mean"]
    g_seen = seen[cond]["first_error_acc"]["mean"] - seen["base"]["first_error_acc"]["mean"]
    sd = vtg[cond]["first_error_acc"]["sd"]
    return {"vtg_gain": g, "vtg_sd": sd, "seen_gain": g_seen, "supported": g > sd and g < g_seen}


def position_check(agg: dict, baseline: float) -> dict:
    held = agg.get("test_heldout", {})
    return {cond: {"mean": v["first_error_acc"]["mean"], "seeds": v["first_error_acc"]["seeds"],
                   "position_only": baseline, "beats_mean": v["first_error_acc"]["mean"] > baseline,
                   "beats_every_seed": all(x > baseline for x in v["first_error_acc"]["seeds"])}
            for cond, v in held.items()}


def step_distribution(runs: dict, split: str, items: dict) -> dict:
    """Share of predictions per step on incorrect items: gold and each condition (seeds pooled)."""
    dist = {"gold": Counter(it["first_error"] for it in items.values() if it["first_error"])}
    for (s, label), recs in runs.items():
        if s != split or not MAIN.match(label):
            continue
        c = dist.setdefault(condition(label), Counter())
        c.update(r["pred"] if r["pred"] is not None else -1 for (i, _), r in recs.items() if items[i]["first_error"])
    return {k: {step: n / sum(c.values()) for step, n in sorted(c.items())} for k, c in dist.items()}


COLORS = {"gold": "#8a8a85", "base": "#2a78d6", "sft": "#eb6834", "grpo": "#1baf7a", "rft": "#eda100"}
NAMES = {"gold": "True first error", "base": "Base", "sft": "SFT", "grpo": "GRPO", "rft": "RFT"}


def plot(dists: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(dists), figsize=(5.2 * len(dists), 3.4), sharey=True)
    axes = axes if len(dists) > 1 else [axes]
    for ax, (split, dist) in zip(axes, dists.items()):
        series = [k for k in COLORS if k in dist]
        steps = sorted({s for d in dist.values() for s in d})
        w = 0.8 / len(series)
        for j, k in enumerate(series):
            xs = [i + (j - (len(series) - 1) / 2) * w for i in range(len(steps))]
            ax.bar(xs, [dist[k].get(s, 0) for s in steps], width=w * 0.9, color=COLORS[k], label=NAMES[k])
        ax.set_xticks(range(len(steps)), ["unparsed" if s == -1 else str(s) for s in steps])
        ax.set_title(split.replace("_", "-") + " (incorrect items)", fontsize=10, loc="left")
        ax.set_xlabel("Predicted step (0 = no error)", fontsize=9)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="y", color="#e4e3df", linewidth=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Share of predictions", fontsize=9)
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def pct(x):
    return "-" if x is None else f"{100 * x:.1f}"


def to_markdown(res: dict) -> str:
    lines = ["# Phase 4 (E4): Base vs. SFT vs. GRPO", "",
             "Mean ± sd over seeds (Base is greedy and has one run). Percentages.", ""]
    for split, agg in res["aggregate"].items():
        lines += [f"## {split}", "", "| Condition | Seeds | First-error | Clean | Error F1 | Within-one |",
                  "|---|---|---|---|---|---|"]
        for cond, m in agg.items():
            cells = [f"{pct(m[k]['mean'])} ± {pct(m[k]['sd'])}" if k in m else "-" for k in METRICS]
            lines.append(f"| {NAMES.get(cond, cond)} | {len(m['first_error_acc']['seeds'])} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Pre-registered tests", "", "```json", json.dumps(res["tests"], indent=1), "```", ""]
    if res["checkpoints"]:
        lines += ["## Checkpoints (go/no-go)", "", "| Label | Split | First-error | Clean | Error F1 |", "|---|---|---|---|---|"]
        for (label, split), m in sorted(res["checkpoints"].items()):
            lines.append(f"| {label} | {split} | {pct(value(m, 'first_error_acc'))} | {pct(value(m, 'clean_acc'))} | "
                         f"{pct(m.get('error_f1'))} |")
    return "\n".join(lines) + "\n"


def main():
    runs = load_runs()
    if not runs:
        sys.exit("no runs/*_phase4_*.jsonl logs")
    items = {s: {it["id"]: it for it in load_items(s)} for s in SPLITS if any(k[0] == s for k in runs)}
    per_split, checkpoints = defaultdict(dict), {}
    for (split, label), recs in runs.items():
        m = localization(recs, items[split])
        if MAIN.match(label):
            per_split[split][label] = m
        else:
            checkpoints[(label, split)] = m
    agg = {s: aggregate(per_split[s]) for s in SPLITS if s in per_split}
    base_pos = json.loads((ROOT / "results/phase1/synthetic_baselines.json").read_text())
    pos = base_pos["eval"]["test_heldout"]["position_only"]["first_error_acc"]
    trained = sorted({condition(lb) for s in per_split.values() for lb in s} - {"base"})
    tests = {"H3": {c: h3(agg, c) for c in trained}, "H4": {c: h4(agg, c) for c in trained},
             "anti_position": position_check(agg, pos)}
    OUT.mkdir(parents=True, exist_ok=True)
    dists = {s: step_distribution(runs, s, items[s]) for s in ("test_seen", "test_heldout") if s in items}
    if dists:
        plot(dists, OUT / "f_position.png")
    res = {"per_seed": per_split, "aggregate": agg, "tests": tests, "position_distribution": dists,
           "checkpoints": checkpoints}
    (OUT / "tables.json").write_text(json.dumps(
        {**res, "checkpoints": {f"{k[0]}|{k[1]}": v for k, v in checkpoints.items()}}, indent=1, default=str))
    (OUT / "tables.md").write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res))


if __name__ == "__main__":
    main()
