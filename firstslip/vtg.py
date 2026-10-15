"""Loading and splitting VtG (eth-nlped/stepverify).

Convention used throughout FirstSlip: steps are numbered from 1 and 0 means
"no error". VtG's `incorrect_index` is 0-based, so first_error = index + 1.
"""
import json
import random
from pathlib import Path

DATASET_ID = "eth-nlped/stepverify"
SPLIT_FILE = Path(__file__).resolve().parent.parent / "data" / "vtg" / "split_ids.json"
NOTA = "None of the above"


def load_rows() -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset(DATASET_ID)["train"]
    rows = []
    for i, r in enumerate(ds):
        rows.append({
            "id": i,
            "problem": r["problem"],
            "steps": list(r["student_incorrect_solution"]),
            "first_error": r["incorrect_index"] + 1,
            "error_category": r["error_category"],
            "error_description": r["error_description"],
            "reference_solution": r["reference_solution"],
        })
    return rows


def make_split(rows: list[dict], dev_size: int, seed: int) -> dict:
    """Split by problem text so no problem appears in both dev and test.

    Groups are shuffled and added to dev unless they would overshoot dev_size,
    so dev holds exactly dev_size rows.
    """
    groups: dict[str, list[int]] = {}
    for r in rows:
        groups.setdefault(r["problem"], []).append(r["id"])
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    dev: list[int] = []
    for k in keys:
        if len(dev) + len(groups[k]) <= dev_size:
            dev.extend(groups[k])
        if len(dev) == dev_size:
            break
    dev_set = set(dev)
    test = [r["id"] for r in rows if r["id"] not in dev_set]
    return {"seed": seed, "dev_size": dev_size, "group_by": "problem",
            "dev": sorted(dev), "test": test}


def load_split() -> dict:
    return json.loads(SPLIT_FILE.read_text())
