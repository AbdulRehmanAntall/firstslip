"""Generate the synthetic splits (Phase 1): train, dev, test_seen, test_heldout.

Balanced positions: a pilot run finds which (solution length, first-error step)
cells each split's misconceptions can reach. Generation then repeatedly picks the
cell furthest below its quota, picks the least-used misconception that can land
in it, and samples a start equation that reaches that cell with that misconception. Seen splits use fixed
length shares with a uniform position within each length; the held-out split,
whose four misconceptions reach few cells, is uniform over its reachable cells.
Clean items follow the incorrect items' length distribution. Every equation is
used once across all splits (deduplicated by its unevaluated SymPy form).
"""
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sympy as sp  # noqa: E402
from sympy.parsing.sympy_parser import parse_expr  # noqa: E402

from core import generator as g  # noqa: E402
from core.checker import TRANSFORMS  # noqa: E402
from core.runlog import RunLog  # noqa: E402

SEED = 20261019
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "synthetic"
SPLITS = [  # name, misconception set, n_incorrect, n_clean
    ("train", "seen", 6000, 2000),
    ("dev", "seen", 375, 125),
    ("test_seen", "seen", 750, 250),
    ("test_heldout", "heldout", 750, 250),
]
MISC = {"seen": g.SEEN, "heldout": g.HELDOUT}
LENGTH_SHARES = {3: 0.30, 4: 0.30, 5: 0.25, 6: 0.15}  # seen splits
PILOT_PER_TYPE = 400
PILOT_MIN = 15  # a cell is reachable if the pilot saw it at least this often
MAX_TRIES = 3_000_000


def canonical(start) -> str:
    lhs, rhs = g.render(start).split("=")
    parse = lambda s: parse_expr(s, transformations=TRANSFORMS, evaluate=False)  # noqa: E731
    return sp.srepr(parse(lhs)) + " = " + sp.srepr(parse(rhs))


def pilot(mids, rng):
    """For each (length, position) cell: misconception -> start types that reach it; plus clean lengths."""
    cells, clean_len, drops = {}, {t: set() for t in g.START_TYPES}, Counter()
    for t in g.START_TYPES:
        for _ in range(PILOT_PER_TYPE):
            start = g.sample_problem(t, rng)
            if not g.valid_start(start):
                continue
            try:
                clean = g.clean_solution(start, rng)
            except g.Degenerate:
                continue
            clean_len[t].add(len(clean.states))
            for m in mids:
                for c in g.injections(start, clean, m, rng, drops):
                    cells.setdefault((len(c.states), c.first_error), Counter())[(t, m)] += 1
    reachable = {}
    for cell, tm in cells.items():
        by_m = {}
        for (t, m), n in tm.items():
            by_m.setdefault(m, Counter())[t] += n
        by_m = {m: sorted(ts) for m, ts in by_m.items() if sum(ts.values()) >= PILOT_MIN}
        if by_m:
            reachable[cell] = by_m
    return reachable, {t: sorted(v) for t, v in clean_len.items()}


def quotas(cells, kind, n):
    if kind == "heldout":
        return {c: n / len(cells) for c in cells}
    per_len = Counter(L for L, _ in cells)
    return {(L, k): n * LENGTH_SHARES[L] / per_len[L] for L, k in cells}


def to_record(sol: g.Solution, split: str) -> dict:
    m = g.MISCONCEPTIONS[sol.misconception] if sol.misconception else None
    return {
        "split": split,
        "start_type": sol.start[0],
        "coefficients": list(sol.start[1]),
        "problem": g.render(sol.start),
        "steps": sol.texts,
        "n_steps": len(sol.texts),
        "first_error": sol.first_error,
        "misconception": sol.misconception,
        "family": m.family if m else None,
        "rule": m.rule if m else None,
        "answer": f"x = {g.num(g.solution(sol.start))}",
        "path": g.state_path(sol),
    }


def build_split(name, kind, n_incorrect, n_clean, rng, used, cells, clean_len, drops):
    mids = MISC[kind]
    quota = quotas(cells, kind, n_incorrect)
    items, m_count, cell_count = [], Counter({m: 0 for m in mids}), Counter()
    tries = 0

    def fresh_start(types, length=None):
        nonlocal tries
        while True:
            tries += 1
            if tries > MAX_TRIES:
                raise RuntimeError(f"{name}: gave up after {MAX_TRIES} tries")
            start = g.sample_problem(rng.choice(types), rng)
            if not g.valid_start(start):
                drops["answer_not_simple"] += 1
                continue
            key = canonical(start)
            if key in used:
                drops["duplicate_equation"] += 1
                continue
            for _ in range(20):  # T12 has two routes; retry until the wanted length comes up
                try:
                    clean = g.clean_solution(start, rng)
                except g.Degenerate:
                    drops["degenerate_clean_chain"] += 1
                    break
                if length is None or len(clean.states) == length:
                    return start, key, clean

    while len(items) < n_incorrect:
        cell = min(cells, key=lambda c: (cell_count[c] / quota[c], rng.random()))
        low = min(m_count[m] for m in cells[cell])
        mid = rng.choice(sorted(m for m in cells[cell] if m_count[m] == low))
        start, key, clean = fresh_start(cells[cell][mid])
        cands = [c for c in g.injections(start, clean, mid, rng, drops)
                 if (len(c.states), c.first_error) == cell]
        if not cands:
            drops["no_injection_in_target_cell"] += 1
            continue
        sol = rng.choice(cands)
        used.add(key)
        m_count[sol.misconception] += 1
        cell_count[cell] += 1
        items.append(to_record(sol, name))

    len_counts = Counter(r["n_steps"] for r in items)
    possible = {L: [t for t in g.START_TYPES if L in clean_len[t]] for L in len_counts}
    possible = {L: ts for L, ts in possible.items() if ts}
    total = sum(len_counts[L] for L in possible)
    clean_quota = {L: round(n_clean * len_counts[L] / total) for L in possible}
    clean_quota[max(clean_quota, key=clean_quota.get)] += n_clean - sum(clean_quota.values())
    for L, q in sorted(clean_quota.items()):
        for _ in range(q):
            start, key, clean = fresh_start(possible[L], length=L)
            used.add(key)
            items.append(to_record(clean, name))

    rng.shuffle(items)
    for i, r in enumerate(items):
        r["id"] = f"{name}-{i:05d}"
    return items


def position_only(fit_items, eval_items):
    """Most common first error per solution length (ties -> earlier step), fit on the incorrect
    items of one set and scored on the incorrect items of another (first-error accuracy)."""
    by_len = {}
    for r in (r for r in fit_items if r["first_error"]):
        by_len.setdefault(r["n_steps"], Counter())[r["first_error"]] += 1
    mode = lambda c: min(c, key=lambda k: (-c[k], k))  # noqa: E731
    prior = {L: mode(c) for L, c in by_len.items()}
    inc = [r for r in eval_items if r["first_error"]]
    return sum(prior.get(r["n_steps"]) == r["first_error"] for r in inc) / len(inc)


def describe(items):
    inc = [r for r in items if r["first_error"]]
    return {
        "n": len(items),
        "incorrect": len(inc),
        "clean": len(items) - len(inc),
        "misconceptions": dict(sorted(Counter(r["misconception"] for r in inc).items())),
        "families": dict(sorted(Counter(r["family"] for r in inc).items())),
        "start_types": dict(sorted(Counter(r["start_type"] for r in items).items())),
        "n_steps_incorrect": dict(sorted(Counter(r["n_steps"] for r in inc).items())),
        "n_steps_clean": dict(sorted(Counter(r["n_steps"] for r in items if not r["first_error"]).items())),
        "first_error_position": dict(sorted(Counter(r["first_error"] for r in inc).items())),
        "length_x_position": {f"{L}:{k}": v for (L, k), v in
                              sorted(Counter((r["n_steps"], r["first_error"]) for r in inc).items())},
        "position_only_oracle_acc": position_only(items, items),
    }


def main():
    rng = random.Random(SEED)
    config = {"seed": SEED, "splits": SPLITS, "coef_range": [-12, 12],
              "steps": [g.MIN_STEPS, g.MAX_STEPS], "max_denominator": g.MAX_DENOMINATOR,
              "seen": g.SEEN, "heldout": g.HELDOUT, "length_shares_seen": LENGTH_SHARES,
              "pilot_per_type": PILOT_PER_TYPE, "pilot_min": PILOT_MIN,
              "step_convention": "1-based, 0 = no error"}
    pilots = {kind: pilot(MISC[kind], random.Random(SEED + 1)) for kind in MISC}
    used: set[str] = set()
    manifest = {"config": config,
                "reachable_cells": {kind: {f"{L}:{k}": ms for (L, k), ms in sorted(p[0].items())}
                                    for kind, p in pilots.items()},
                "clean_lengths_by_start_type": pilots["seen"][1],
                "splits": {}, "rejected_candidates": {}}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built = {}
    with RunLog("phase1_generate", config, SEED) as log:
        for name, kind, n_inc, n_clean in SPLITS:
            drops = Counter()
            cells, clean_len = pilots[kind][0], {t: set(v) for t, v in pilots["seen"][1].items()}
            items = build_split(name, kind, n_inc, n_clean, rng, used, cells, clean_len, drops)
            built[name] = items
            path = OUT_DIR / f"{name}.jsonl"
            with path.open("w", encoding="utf-8", newline="\n") as f:
                for r in items:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            stats = describe(items)
            stats["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest["splits"][name] = stats
            manifest["rejected_candidates"][name] = dict(sorted(drops.items()))
            log.write({"type": "split", "split": name, "stats": stats, "rejected": dict(drops)})
            print(f"{name}: {stats['n']} items ({stats['incorrect']} incorrect); "
                  f"position-only oracle {stats['position_only_oracle_acc']:.3f}; rejected {dict(drops)}")
        manifest["position_only_fit_on_dev"] = {
            name: position_only(built["dev"], built[name]) for name in ("test_seen", "test_heldout")}
        log.write({"type": "results", "position_only_fit_on_dev": manifest["position_only_fit_on_dev"]})
        manifest["run_log"] = log.path.name
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("position-only (fit on dev):", manifest["position_only_fit_on_dev"])


if __name__ == "__main__":
    main()
