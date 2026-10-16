from types import SimpleNamespace

import pytest

from core import prompts
from core.faithfulness import faithfulness_label, mentioned_step
from core.llm import BudgetExceeded, Client, Ledger
from core.misconceptions import map_feedback
from core.phase2 import load_synthetic, record, sample
from core.stats import holm, mcnemar, paired_bootstrap_diff

ITEM = {"id": "t-1", "source": "synthetic", "split": "dev", "problem": "-3x = 2(x - 6)",
        "steps": ["-3x = 2x - 12", "-3x = -10", "x = 10/3"], "first_error": 2, "misconception": "M13"}


# --- prompt and parser ---------------------------------------------------------

def test_parse_plain_and_markdown():
    assert prompts.parse_response("Step: 2\nFeedback: You dropped the x.") == prompts.Parsed(2, "You dropped the x.")
    assert prompts.parse_response("**Step:** 3\n**Feedback:** Wrong sign.").step == 3
    assert prompts.parse_response("<think>step: 9</think>\nStep: 0\nFeedback: All correct.").step == 0


def test_parse_failure_is_none():
    assert prompts.parse_response("The error is in step 2.").step is None
    assert prompts.parse_response("").step is None


def test_parse_solve():
    assert prompts.parse_solve("Answer: x = -12/5") == "x = -12/5"
    assert prompts.parse_solve("x is 3") is None


def test_supplied_locations():
    assert prompts.supplied_location(ITEM, "none") is None
    assert prompts.supplied_location(ITEM, "true") == 2
    assert prompts.supplied_location(ITEM, "off1") in (1, 3)
    assert prompts.supplied_location(ITEM, "rand") in (1, 3)
    # deterministic, and never the true step
    for c in ("off1", "rand"):
        assert prompts.supplied_location(ITEM, c) == prompts.supplied_location(ITEM, c)
    edge = {**ITEM, "first_error": 1}
    assert prompts.supplied_location(edge, "off1") == 2
    with pytest.raises(ValueError):
        prompts.supplied_location({**ITEM, "first_error": 0}, "true")


def test_request_text():
    r = prompts.build_request(ITEM, "rand")
    assert "Step 3: x = 10/3" in r.input and f"step {r.supplied}." in r.input
    assert "checker" not in prompts.build_request(ITEM, "none").input


def test_record_fields():
    req = prompts.build_request(ITEM, "none")
    rec = record(ITEM, req, "Step: 2\nFeedback: In step 2 you dropped the x.", {"cost": 0})
    assert rec["pred"] == 2 and rec["gold"] == 2 and rec["n_steps"] == 3


# --- faithfulness ----------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("In step 2 you combined -12 with x.", 2),
    ("Your third step divides wrongly.", 3),
    ("The 2nd line drops the x.", 2),
    ("-3x = -10 does not follow from -3x = 2x - 12.", 2),  # two steps quoted: the later one
    ("You made an error here.", None),
    ("You wrote 12.", None),  # lone number: too weak
])
def test_mentioned_step(text, expected):
    assert mentioned_step(text, ITEM["steps"]) == expected


def test_faithfulness_label():
    assert faithfulness_label(2, "Step 2 drops x.", ITEM["steps"]) == "faithful"
    assert faithfulness_label(3, "Step 2 drops x.", ITEM["steps"]) == "unfaithful"
    assert faithfulness_label(2, "Something is off.", ITEM["steps"]) == "unspecified"
    assert faithfulness_label(0, "All good.", ITEM["steps"]) is None


# --- misconception mapping -------------------------------------------------------

@pytest.mark.parametrize("text,label", [
    ("You divided only one side by -3.", "M20_S20"),
    ("You inverted the division: it should be -10 divided by -3.", "M22_S1"),
    ("You dropped the x when combining -3x and 2x.", "M13"),
    ("You distributed the 3 only to the first term.", "M2_S3"),
    ("You moved 4 across the equals sign without changing its sign.", "M11"),
    ("You added the numbers instead of multiplying them.", "M16"),
    ("You subtracted 5 instead of adding it.", "M14"),
    ("You added 5 instead of subtracting it.", "M15"),
    ("You added 3 instead of dividing by it.", "M19"),
    ("Nice work.", None),
])
def test_map_feedback(text, label):
    assert map_feedback(text) == label


# --- statistics ------------------------------------------------------------------

def test_mcnemar_and_holm():
    r = mcnemar([1] * 20 + [0] * 5, [0] * 20 + [0] * 5)
    assert r["only_a"] == 20 and r["only_b"] == 0 and r["p"] < 1e-5
    assert mcnemar([1, 0], [1, 0])["p"] == 1.0
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    d, lo, hi = paired_bootstrap_diff([1, 1, 1, 0], [0, 0, 1, 0])
    assert d == 0.5 and lo <= d <= hi


# --- client: cache and spending cap ------------------------------------------------

class FakeAPI:
    def __init__(self):
        self.calls = 0
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls += 1
        usage = SimpleNamespace(input_tokens=100, output_tokens=50,
                                input_tokens_details=SimpleNamespace(cached_tokens=0),
                                output_tokens_details=SimpleNamespace(reasoning_tokens=20))
        return SimpleNamespace(output_text="Step: 1\nFeedback: x.", model=kw["model"] + "-2026", usage=usage)


def _client(tmp_path, cap):
    cfg = {"spend_cap_usd": cap, "models": {"m": {"model": "fake", "max_output_tokens": 100,
                                                  "prices": {"input": 1.0, "cached_input": 0.1, "output": 10.0}}}}
    return Client("m", cfg, Ledger(tmp_path / "c.sqlite"), api=FakeAPI())


def test_cache_never_pays_twice(tmp_path):
    c = _client(tmp_path, cap=1.0)
    a = c.complete("ins", "in")
    b = c.complete("ins", "in")
    assert c.api.calls == 1 and not a.cached and b.cached and b.cost == 0
    assert a.cost == pytest.approx((100 * 1.0 + 50 * 10.0) / 1e6)
    assert c.ledger.spent() == pytest.approx(a.cost)


def test_cap_blocks_before_sending(tmp_path):
    c = _client(tmp_path, cap=0.0005)  # worst case of one call is ~0.001
    with pytest.raises(BudgetExceeded):
        c.complete("ins", "in")
    assert c.api.calls == 0 and c.ledger.spent() == 0


# --- sampling --------------------------------------------------------------------

def test_sample_nested_and_balanced():
    items = load_synthetic("dev")
    s100, s200 = sample(items, 100), sample(items, 200)
    assert len(s100) == 100 and {r["id"] for r in s100} <= {r["id"] for r in s200}
    assert sum(r["first_error"] == 0 for r in s100) == 25
