"""Fix the VtG dev/test split (Phase 0). Writes data/vtg/split_ids.json and the row files."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vtg  # noqa: E402

SEED = 20261016
DEV_SIZE = 200

rows = vtg.load_rows()
split = vtg.make_split(rows, DEV_SIZE, SEED)
vtg.SPLIT_FILE.parent.mkdir(parents=True, exist_ok=True)
vtg.SPLIT_FILE.write_text(json.dumps(split, indent=1))

by_id = {r["id"]: r for r in rows}
for name in ("dev", "test"):
    path = vtg.SPLIT_FILE.parent / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for i in split[name]:
            f.write(json.dumps(by_id[i], ensure_ascii=False) + "\n")
    print(f"{name}: {len(split[name])} rows -> {path}")

dev_problems = {by_id[i]["problem"] for i in split["dev"]}
test_problems = {by_id[i]["problem"] for i in split["test"]}
print("problems shared between dev and test:", len(dev_problems & test_problems))
