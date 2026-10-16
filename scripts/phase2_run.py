"""Run one Phase 2 experiment on one split with one API model (cached, spend-capped).

    python scripts/phase2_run.py --model gpt-mini --exp e1 --split dev --dry-run
    python scripts/phase2_run.py --model gpt-mini --exp e1 --split dev
    python scripts/phase2_run.py --model gpt-frontier --exp e3 --split test_seen --sample 300

--dry-run sends nothing: it counts uncached requests and projects their cost from
--est-output tokens per reply (measure it on dev first) and from the worst case.
Every response goes to one run log in runs/; cached responses are logged too.
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.llm import BudgetExceeded, Client, est_tokens, load_config  # noqa: E402
from core.phase2 import EXPERIMENTS, record, requests_for, run_config  # noqa: E402
from core.runlog import RunLog  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="key in config/phase2.json models")
    ap.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS))
    ap.add_argument("--split", required=True)
    ap.add_argument("--sample", type=int, default=None, help="fixed nested subsample of items")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--est-output", type=int, default=300, help="expected output tokens per reply (dry run)")
    args = ap.parse_args()

    config = load_config()
    client = Client(args.model, config)
    pairs = requests_for(args.exp, args.split, args.sample)
    todo = [(it, rq) for it, rq in pairs if not client.is_cached(rq.instructions, rq.input)]
    in_tok = sum(est_tokens(rq.instructions + rq.input) for _, rq in todo)
    expected = client.cost(in_tok, 0, args.est_output * len(todo))
    worst = sum(client.worst_case(rq.instructions, rq.input) for _, rq in todo)
    spent = client.ledger.spent()
    print(f"{args.model} ({client.model}) {args.exp}/{args.split}: {len(pairs)} requests, {len(todo)} uncached; "
          f"~{in_tok:,} input tokens; projected ${expected:.3f} (worst ${worst:.3f}); "
          f"spent so far ${spent:.3f} of ${client.cap:.2f}")
    if args.dry_run:
        return

    model_info = {"name": args.model, "id": client.model, **client.params}
    name = f"phase2_{args.exp}_{args.split}_{args.model}"
    stats = {"sent": 0, "cached": 0, "cost": 0.0, "budget_stops": 0}
    with RunLog(name, run_config(args.exp, args.split, model_info, args.sample), seed=0) as log:
        def one(pair):
            item, req = pair
            try:
                r = client.complete(req.instructions, req.input)
            except BudgetExceeded as e:
                return item, req, None, str(e)
            return item, req, r, None

        with ThreadPoolExecutor(args.workers) as pool:
            for i, (item, req, r, err) in enumerate(pool.map(one, pairs), start=1):
                if r is None:
                    stats["budget_stops"] += 1
                    log.write({"type": "skipped", "id": item["id"], "condition": req.condition, "reason": err})
                    continue
                meta = {"model_version": r.model_version, "input_tokens": r.input_tokens,
                        "cached_input_tokens": r.cached_input_tokens, "output_tokens": r.output_tokens,
                        "reasoning_tokens": r.reasoning_tokens, "cost": r.cost, "cache_hit": r.cached}
                log.write(record(item, req, r.text, meta))
                stats["cached" if r.cached else "sent"] += 1
                stats["cost"] += r.cost
                if i % 100 == 0:
                    print(f"  {i}/{len(pairs)}  ${stats['cost']:.3f}", flush=True)
        stats["spent_total"] = client.ledger.spent()
        log.write({"type": "summary", **stats})
    print(f"done: {stats}  ->  {log.path.name}")
    if stats["budget_stops"]:
        print(f"WARNING: {stats['budget_stops']} requests were not sent (spending cap)")


if __name__ == "__main__":
    main()
