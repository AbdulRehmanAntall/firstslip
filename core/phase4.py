"""Phase 4 (E4): training data, the step-only SFT target and the checker reward.

Every condition (Base, SFT, GRPO) sees the frozen Phase 2 prompt (p2-v1, "none"
condition), so trained and prompted models are scored on identical inputs.

Labels come from the SymPy checker (core.checker.check), not from the generator:
the reward is the checker's verdict. On all 10,500 synthetic items the two agree
(results/phase1/gate.json), and prepare() asserts this again for every item.

SFT target (Amendment 6): "Step: k\\nFeedback:" with no end-of-turn token. Only
the step number is supervised, as in GRPO, so the feedback sentence is the base
model's own continuation in every condition and E6 compares like with like.

GRPO reward (PREREGISTRATION.md §6):
    1.0  correct step, or a correct 0 on a clean solution
    0.2  one step off (both the prediction and the truth are steps, i.e. not 0)
    0    anything else
   +0.1  the answer parses (a "Step: <int>" line)
The feedback sentence is never rewarded.
"""
import json
from pathlib import Path

from core.checker import check
from core.prompts import build_request, parse_response

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "phase4.json"
DATA = ROOT / "data" / "phase4"
SPLITS = ("train", "dev")
TARGET_VERSION = "t4-v1"  # bump on any change to messages() or sft_target()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def messages(item: dict) -> list[dict]:
    """The E1 ("none") request as chat messages."""
    req = build_request(item, "none")
    return [{"role": "system", "content": req.instructions}, {"role": "user", "content": req.input}]


def checker_step(item: dict) -> int:
    return check(item["problem"], item["steps"]).first_error


def sft_target(step: int) -> str:
    return f"Step: {step}\nFeedback:"


def prepare(item: dict) -> dict:
    """One training row: chat prompt plus the checker's first wrong step."""
    k = checker_step(item)
    if k != item["first_error"]:
        raise ValueError(f"{item['id']}: checker says {k}, generator says {item['first_error']}")
    return {"id": item["id"], "prompt": messages(item), "checker_step": k, "n_steps": len(item["steps"]),
            "misconception": item.get("misconception")}


# --- reward --------------------------------------------------------------------

def _text(completion) -> str:
    """TRL passes plain strings (standard format) or [{"role", "content"}] (conversational)."""
    if isinstance(completion, list):
        return completion[-1]["content"] if completion else ""
    return completion or ""


def step_score(pred: int | None, gold: int) -> float:
    if pred is None:
        return 0.0
    if pred == gold:
        return 1.0
    if pred and gold and abs(pred - gold) == 1:
        return 0.2
    return 0.0


def step_reward(completions, checker_step, **kwargs) -> list[float]:
    return [step_score(parse_response(_text(c)).step, k) for c, k in zip(completions, checker_step)]


def format_reward(completions, **kwargs) -> list[float]:
    return [0.1 if parse_response(_text(c)).step is not None else 0.0 for c in completions]


def load_rows(split: str) -> list[dict]:
    return [json.loads(line) for line in (DATA / f"{split}.jsonl").open(encoding="utf-8")]
