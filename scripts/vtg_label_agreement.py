"""How often do VtG teachers agree on the first error when the same solution is annotated twice?"""
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from firstslip import vtg  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "results" / "phase0" / "vtg_label_agreement.json"

rows = vtg.load_rows()
split = vtg.load_split()
split_of = {i: name for name in ("dev", "test") for i in split[name]}
groups = defaultdict(list)
for r in rows:
    groups[(r["problem"], tuple(s.strip() for s in r["steps"]))].append(r)
multi = [g for g in groups.values() if len(g) > 1]

pairs = agree = 0
for g in multi:
    for a, b in itertools.combinations(g, 2):
        pairs += 1
        agree += a["first_error"] == b["first_error"]

result = {
    "rows": len(rows),
    "unique_solutions": len(groups),
    "solutions_annotated_more_than_once": len(multi),
    "rows_in_those": sum(map(len, multi)),
    "groups_with_disagreeing_first_error": sum(len({r["first_error"] for r in g}) > 1 for g in multi),
    "pairwise_first_error_agreement": agree / pairs,
    "pairs": pairs,
    "groups_spanning_dev_and_test": sum(len({split_of[r["id"]] for r in g}) > 1 for g in multi),
    "missing_teacher_description": sum(not r["error_description"] for r in rows),
    "final_element_is_answer_only_rows": sum(len(r["steps"][-1].strip()) <= 10 for r in rows),
    "first_error_is_final_answer_rows": sum(r["first_error"] == len(r["steps"]) for r in rows),
    "error_category_counts": Counter(r["error_category"] for r in rows),
}
OUT.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
