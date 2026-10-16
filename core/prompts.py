"""The Phase 2 prompt template and output parser (one template for every model).

Every model answers in the fixed format of PREREGISTRATION.md §5:

    Step: <first wrong step, or 0 if every step is correct>
    Feedback: <one sentence to the student about that step>

Conditions (the same template, with or without a supplied location):
  none   E1, and the "no location" arm of E2
  true   E2 "checker location given" (= E3 "true")
  off1   E3, location one step away from the true step
  rand   E3, a random wrong step
  solve  H1, the model solves the problem itself (test-seen only)

Supplied locations are drawn from an RNG seeded by (seed, item id, condition), so
the API runner and the Colab notebook build identical requests.
"""
import random
import re
from dataclasses import dataclass

PROMPT_VERSION = "p2-v1"  # bump on any change; frozen before test runs
LOCATION_SEED = 20261028
CONDITIONS = ("none", "true", "off1", "rand")

INSTRUCTIONS = """You are a maths tutor checking a student's worked solution.
Find the FIRST step that is mathematically wrong. A step is wrong if it does not follow correctly from the step before it (for the first step, from the problem). Later steps that correctly continue from an earlier mistake do not count.

Answer in exactly two lines and nothing else:
Step: <number of the first wrong step, or 0 if every step is correct>
Feedback: <one sentence to the student saying what went wrong in that step, or confirming the solution if it is correct>"""

LOCATION_LINE = "An automatic checker reports that the first wrong step is step {k}."

SOLVE_INSTRUCTIONS = """Solve the equation for x.
Answer in exactly one line and nothing else:
Answer: x = <value, as an integer or a fraction a/b>"""


@dataclass(frozen=True)
class Request:
    item_id: str
    condition: str
    supplied: int | None  # location given to the model (None for "none"/"solve")
    instructions: str
    input: str


def _numbered(steps: list[str]) -> str:
    return "\n".join(f"Step {i}: {s}" for i, s in enumerate(steps, start=1))


def problem_text(item: dict) -> str:
    if item["source"] == "synthetic":
        return f"Problem: Solve for x: {item['problem']}"
    return f"Problem: {item['problem']}"


def supplied_location(item: dict, condition: str, seed: int = LOCATION_SEED) -> int | None:
    k, n = item["first_error"], len(item["steps"])
    if condition in ("none", "solve"):
        return None
    if k == 0:
        raise ValueError(f"{item['id']}: no location to supply on a clean item")
    if condition == "true":
        return k
    rng = random.Random(f"{seed}|{item['id']}|{condition}")
    if condition == "off1":
        options = [j for j in (k - 1, k + 1) if 1 <= j <= n]
    elif condition == "rand":
        options = [j for j in range(1, n + 1) if j != k]
    else:
        raise ValueError(condition)
    return rng.choice(options)


def build_request(item: dict, condition: str) -> Request:
    if condition == "solve":
        return Request(item["id"], "solve", None, SOLVE_INSTRUCTIONS, f"Equation: {item['problem']}")
    loc = supplied_location(item, condition)
    parts = [problem_text(item), "", "Student solution:", _numbered(item["steps"])]
    if loc is not None:
        parts += ["", LOCATION_LINE.format(k=loc)]
    return Request(item["id"], condition, loc, INSTRUCTIONS, "\n".join(parts))


# --- parsing -----------------------------------------------------------------

THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
STEP_RE = re.compile(r"^\W*step\W*:\W*(\d+)\b", re.I | re.M)
FEEDBACK_RE = re.compile(r"^\W*feedback\W*:\s*(.+?)\s*$", re.I | re.M)
ANSWER_RE = re.compile(r"^\W*answer\W*:\s*(.+?)\s*$", re.I | re.M)


@dataclass(frozen=True)
class Parsed:
    step: int | None  # None = the answer did not parse
    feedback: str | None


def clean_output(text: str) -> str:
    text = THINK.sub("", text or "")
    return text.split("</think>")[-1]  # unterminated opening tag stripped by a chat template


def parse_response(text: str) -> Parsed:
    """Strict: a `Step: <int>` line is required. Markdown bold and case are tolerated."""
    text = clean_output(text)
    m = STEP_RE.search(text)
    f = FEEDBACK_RE.search(text)
    return Parsed(int(m.group(1)) if m else None, f.group(1).strip("* ") if f else None)


def parse_solve(text: str) -> str | None:
    m = ANSWER_RE.search(clean_output(text))
    return m.group(1).strip("*` .") if m else None
