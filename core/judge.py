"""LLM judge for the Phase 2 feedback metrics (Amendment 5).

The rule-based extractor and mapping failed their hand audits (results/phase2/audit.json),
so a fixed judge model reads each feedback sentence instead. Two tasks:

  faith  Which step is the feedback about? The judge sees the problem, the numbered
         steps and the feedback, but NOT the step the model flagged, so the answer is
         read from the feedback text alone (as the extractor did).
         Output: `Step: <n>`, or `Step: 0` when no single step can be told.
         Faithful = the judged step equals the flagged step.
  diag   Does the feedback correctly diagnose the real error? The judge sees the
         solution, the true first wrong step and a plain description of the injected
         misconception (synthetic data only).
         Output: `Verdict: yes` or `Verdict: no`.

One template per task for every judged model. Greedy decoding, thinking off.
"""
import re
from dataclasses import dataclass

from core.prompts import THINK, _numbered, problem_text

JUDGE_VERSION = "j-v1"  # bump on any change; frozen on dev before the test run
TASKS = ("faith", "diag")

# What the student did wrong, in words, for the diag judge. Paraphrases PREREGISTRATION.md §2.
DESCRIPTIONS = {
    "M1": "added the outside factor to the bracket instead of multiplying it out: A(part) became A + (part)",
    "M2_S3": "multiplied only the first term inside the bracket by the outside factor: A(Bx ± C) became ABx ± C",
    "M3": "added or subtracted before multiplying out the bracket: A ± B(part) became (A ± B)(part)",
    "M4": "multiplied the outside factor into both factors of a product: A(B·C) became AB·AC",
    "M5": "multiplied the outside factor in but also kept it outside: A(Bx ± C) became A(ABx ± AC)",
    "M6": "made a sign error when multiplying out a negative factor: -A(Bx - C) became -ABx - AC instead of -ABx + AC",
    "M8": "multiplied only the constant term inside the bracket by the outside factor: A(Bx ± C) became Bx ± AC",
    "M11": "moved terms across the equals sign without changing their signs: Ax ± B = Cx ± D became Ax + Cx = B + D",
    "M12_S15": "combined an x term with a constant: Ax ± B became (A ± B)x",
    "M13": "combined an x term with a constant and dropped the x: Ax ± B became (A ± B)",
    "M14": "subtracted where the two numbers should be added",
    "M15": "added where the two numbers should be subtracted",
    "M16": "added where the two numbers should be multiplied",
    "M17": "reversed the order of a sum and subtracted: A + B became B - A",
    "M18": "subtracted in the wrong order: A - B became B - A",
    "M19": "added the coefficient instead of dividing by it: Ax = B became x = A + B",
    "M20_S20": "did not divide by the coefficient of x: Ax = B became x = B",
    "M21": "subtracted the coefficient instead of dividing by it: Ax = B became x = A - B",
    "M22_S1": "divided the wrong way round: Ax = B became x = A / B",
}

FAITH_INSTRUCTIONS = """You are checking a tutor's feedback on a student's worked solution. You are not asked whether the feedback is correct.
Say which step of the student's solution the feedback is about: the step whose working it describes or criticises. A step's working is the change from the step before it (for step 1, from the problem). If the feedback discusses several steps, give the one it finally says is wrong. If it does not point to any single step, answer 0.

Answer in exactly one line and nothing else:
Step: <step number, or 0>"""

DIAG_INSTRUCTIONS = """You are checking a tutor's feedback on a student's worked solution. You are told which step is the first wrong one and what the student actually did wrong there.
Decide whether the feedback correctly identifies that mistake. It does not need the same words, but it must describe the same error in that step. Answer no if the feedback blames a different step, describes a different mistake, says the step is correct, or contradicts itself.

Answer in exactly one line and nothing else:
Verdict: <yes or no>"""


@dataclass(frozen=True)
class JudgeRequest:
    task: str
    item_id: str
    source_exp: str   # experiment of the judged response (e1 / e2)
    condition: str    # condition of the judged response
    instructions: str
    input: str


def faith_request(item: dict, feedback: str, source_exp: str, condition: str) -> JudgeRequest:
    parts = [problem_text(item), "", "Student solution:", _numbered(item["steps"]), "", f"Tutor feedback: {feedback}"]
    return JudgeRequest("faith", item["id"], source_exp, condition, FAITH_INSTRUCTIONS, "\n".join(parts))


def diag_request(item: dict, feedback: str, source_exp: str, condition: str) -> JudgeRequest:
    k = item["first_error"]
    parts = [problem_text(item), "", "Student solution:", _numbered(item["steps"]), "",
             f"The first wrong step is step {k}. In that step the student {DESCRIPTIONS[item['misconception']]}.",
             "", f"Tutor feedback: {feedback}"]
    return JudgeRequest("diag", item["id"], source_exp, condition, DIAG_INSTRUCTIONS, "\n".join(parts))


STEP_RE = re.compile(r"^\W*step\W*:\W*(\d+)\b", re.I | re.M)
VERDICT_RE = re.compile(r"^\W*verdict\W*:\W*(yes|no)\b", re.I | re.M)


def parse_judge(task: str, text: str) -> int | bool | None:
    """faith -> step number (0 = no single step); diag -> True/False. None if it does not parse."""
    text = THINK.sub("", text or "").split("</think>")[-1]
    if task == "faith":
        m = STEP_RE.search(text)
        return int(m.group(1)) if m else None
    m = VERDICT_RE.search(text)
    return m.group(1).lower() == "yes" if m else None


def faith_label(flagged: int | None, judged: int | None) -> str | None:
    """Same classes as core.faithfulness.faithfulness_label, from the judge's step."""
    if not flagged:
        return None
    if not judged:
        return "unspecified"
    return "faithful" if judged == flagged else "unfaithful"
