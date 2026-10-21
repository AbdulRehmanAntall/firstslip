import json
import sys
from pathlib import Path

import pytest

from core import phase4
from core.phase2 import load_synthetic, record, requests_for
from core.prompts import build_request, parse_response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

ITEM = {"id": "t-1", "source": "synthetic", "split": "dev", "problem": "-3x = 2(x - 6)",
        "steps": ["-3x = 2x - 12", "-3x = -10", "x = 10/3"], "first_error": 2, "misconception": "M13"}


# --- reward (PREREGISTRATION.md §6) ----------------------------------------------

@pytest.mark.parametrize("pred,gold,score", [
    (2, 2, 1.0), (0, 0, 1.0),          # correct step; correct "no error"
    (1, 2, 0.2), (3, 2, 0.2),          # one step off
    (4, 2, 0.0), (None, 2, 0.0),       # wrong; did not parse
    (1, 0, 0.0), (0, 1, 0.0),          # 0 is "no error", never "one step off"
])
def test_step_score(pred, gold, score):
    assert phase4.step_score(pred, gold) == score


def test_rewards_standard_and_conversational():
    texts = ["Step: 2\nFeedback: You dropped the x.", "Step: 3\nFeedback: Sign.", "The error is step 2."]
    gold = [2, 2, 2]
    assert phase4.step_reward(texts, checker_step=gold) == [1.0, 0.2, 0.0]
    assert phase4.format_reward(texts) == [0.1, 0.1, 0.0]
    conv = [[{"role": "assistant", "content": t}] for t in texts]
    assert phase4.step_reward(conv, checker_step=gold, prompts=None, completion_ids=None) == [1.0, 0.2, 0.0]
    assert phase4.format_reward(conv) == [0.1, 0.1, 0.0]


def test_feedback_is_never_rewarded():
    a = "Step: 2\nFeedback: You dropped the x when combining."
    b = "Step: 2\nFeedback: Totally unrelated sentence about step 3."
    assert phase4.step_reward([a], checker_step=[2]) == phase4.step_reward([b], checker_step=[2])
    assert phase4.format_reward([a]) == phase4.format_reward([b])


# --- training rows ----------------------------------------------------------------

def test_sft_target_is_step_only_and_parses():
    t = phase4.sft_target(3)
    assert t == "Step: 3\nFeedback:"
    assert parse_response(t).step == 3


def test_messages_match_the_frozen_e1_prompt():
    req = build_request(ITEM, "none")
    assert phase4.messages(ITEM) == [{"role": "system", "content": req.instructions},
                                     {"role": "user", "content": req.input}]


def test_prepare_uses_the_checker_label():
    row = phase4.prepare(ITEM)
    assert row["checker_step"] == 2 and row["n_steps"] == 3
    with pytest.raises(ValueError):
        phase4.prepare({**ITEM, "first_error": 1})


def test_prepare_on_real_dev_items():
    for item in load_synthetic("dev")[:20]:
        assert phase4.prepare(item)["checker_step"] == item["first_error"]


# --- scoring ----------------------------------------------------------------------

def _write_run(runs: Path, split: str, label: str, preds: dict, stamp: str):
    pairs = requests_for("e1", split)
    path = runs / f"{stamp}_phase4_{split}_qwen-2b_{label}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "header", "config": {"split": split, "model": {"label": label}}}) + "\n")
        for item, rq in pairs:
            k = preds(item)
            f.write(json.dumps(record(item, rq, f"Step: {k}\nFeedback: x", {})) + "\n")


def test_score_end_to_end(tmp_path, monkeypatch):
    import phase4_score as sc

    runs = tmp_path / "runs"
    runs.mkdir()
    oracle = lambda it: it["first_error"]  # noqa: E731
    first = lambda it: 1  # noqa: E731
    for split in ("test_seen", "test_heldout"):
        _write_run(runs, split, "base", first, "20260101T000000Z")
        for s in range(3):
            _write_run(runs, split, f"sft-s{s}", oracle, f"2026010{s + 1}T000000Z")
        _write_run(runs, split, "grpo-s0-step50", first, "20260105T000000Z")
    monkeypatch.setattr(sc, "RUNS", runs)
    monkeypatch.setattr(sc, "OUT", tmp_path / "out")
    sc.main()
    res = json.loads((tmp_path / "out" / "tables.json").read_text())
    sft = res["aggregate"]["test_seen"]["sft"]
    assert sft["error_f1"]["mean"] == 1.0 and sft["error_f1"]["sd"] == 0.0
    assert res["tests"]["H3"]["sft"]["improves"] is True
    assert res["tests"]["H3"]["sft"]["holds_gain"] is True
    assert res["tests"]["anti_position"]["sft"]["beats_every_seed"] is True
    assert res["tests"]["anti_position"]["base"]["beats_mean"] is False
    assert "grpo-s0-step50|test_seen" in res["checkpoints"]
    assert (tmp_path / "out" / "f_position.png").exists()
