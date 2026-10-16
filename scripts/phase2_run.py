"""Run Phase 2 experiments with an API model (cached, spend-capped).

    python scripts/phase2_run.py --model gpt-mini --grid dev --dry-run
    python scripts/phase2_run.py --model gpt-mini --grid dev
    python scripts/phase2_run.py --model gpt-mini --exp e3 --split test_seen

--grid runs every (exp, split) of core.phase2.GRIDS; --exp/--split runs one.
--dry-run sends nothing: it counts uncached requests and projects their cost from
--est-output tokens per reply (measure it on dev first) and from the worst case.
Every response goes to one run log per (exp, split) in runs/; cached responses
are logged too. Open models run through scripts/phase2_run_vllm.py instead.
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.llm import BudgetExceeded, Client, est_tokens, load_config  # noqa: E402
from core.phase2 import EXPERIMENTS, GRIDS, record, requests_for, run_config  # noqa: E402
from core.runlog import RunLog  # noqa: E402


def project(client: Client, pairs, est_output: int) -> dict:
    todo = [rq for _, rq in pairs if not client.is_cached(rq.instructions, rq.input)]
    in_tok = sum(est_tokens(rq.instructions + rq.input) for rq in todo)
    return {"requests": len(pairs), "uncached": len(todo), "input_tokens": in_tok,
            "expected": client.cost(in_tok, 0, est_output * len(todo)),
            "worst": sum(client.worst_case(rq.instructions, rq.input) for rq in todo)}


def run(client: Client, name: str, exp: str, split: str, sample: int | None, workers: int) -> dict:
    pairs = requests_for(exp, split, sample)
    model_info = {"name": name, "id": client.model, **client.params}
    stats = {"sent": 0, "cached": 0, "cost": 0.0, "budget_stops": 0}

    def one(pair):
        item, req = pair
        try:
            return item, req, client.complete(req.instructions, req.input), None
        except BudgetExceeded as e:
            return item, req, None, str(e)

    with RunLog(f"phase2_{exp}_{split}_{name}", run_config(exp, split, model_info, sample), seed=0) as log:
        with ThreadPoolExecutor(workers) as pool:
            for i, (item, req, r, err) in enumerate(pool.map(one, pairs), start=1):
                if r is None:
                    stats["budget_stops"] += 1
                    log.write({"type": "skipped", "id": item["id"], "condition": req.condition, "reason": err})
                    continue
                log.write(record(item, req, r.text, {
                    "model_version": r.model_version, "input_tokens": r.input_tokens,
                    "cached_input_tokens": r.cached_input_tokens, "output_tokens": r.output_tokens,
                    "reasoning_tokens": r.reasoning_tokens, "cost": r.cost, "cache_hit": r.cached}))
                stats["cached" if r.cached else "sent"] += 1
                stats["cost"] += r.cost
                if i % 200 == 0:
                    print(f"  {i}/{len(pairs)}  ${stats['cost']:.3f}", flush=True)
        stats["spent_total"] = client.ledger.spent()
        log.write({"type": "summary", **stats})
    stats["log"] = log.path.name
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="key in config/phase2.json models")
    ap.add_argument("--grid", choices=sorted(GRIDS))
    ap.add_argument("--exp", choices=sorted(EXPERIMENTS))
    ap.add_argument("--split")
    ap.add_argument("--sample", type=int, default=None, help="fixed nested subsample of items")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--est-output", type=int, default=300, help="expected output tokens per reply (dry run)")
    args = ap.parse_args()
    if bool(args.grid) == bool(args.exp and args.split):
        ap.error("give either --grid or both --exp and --split")
    jobs = GRIDS[args.grid] if args.grid else [(args.exp, args.split)]

    client = Client(args.model, load_config())
    total = 0.0
    for exp, split in jobs:
        p = project(client, requests_for(exp, split, args.sample), args.est_output)
        total += p["expected"]
        print(f"{args.model} ({client.model}) {exp}/{split}: {p['requests']} requests, {p['uncached']} uncached; "
              f"projected ${p['expected']:.3f} (worst ${p['worst']:.3f})")
    print(f"projected total ${total:.3f}; spent so far ${client.ledger.spent():.3f} of ${client.cap:.2f}")
    if args.dry_run:
        return

    for exp, split in jobs:
        stats = run(client, args.model, exp, split, args.sample, args.workers)
        print(f"{exp}/{split}: {stats}")
        if stats["budget_stops"]:
            sys.exit(f"stopped: {stats['budget_stops']} requests not sent (spending cap)")


if __name__ == "__main__":
    main()
