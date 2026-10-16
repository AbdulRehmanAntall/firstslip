"""Rule-based extractor: which step does a feedback sentence talk about?

Faithfulness (PREREGISTRATION.md §5) is the share of feedback sentences that refer
to the step the model flagged. The extractor looks, in order, for

  1. an explicit reference: "step 3", "line 3", "3rd step", "the third step";
  2. a quoted piece of maths that occurs in exactly one step (spaces, `*` and
     unicode minus ignored). If spans from several steps are quoted ("-3x = -10
     does not follow from -3x = 2x - 12"), the latest step is taken: feedback
     that quotes two steps is describing the move into the later one.

It returns a step number, or None when the sentence names no identifiable step.
The flagged step itself never counts as evidence: only the feedback text is read.
"""
import re

ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
            "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}
EXPLICIT = [
    re.compile(r"\b(?:step|line)\s*#?\s*(\d+)\b", re.I),
    re.compile(r"\b(\d+)(?:st|nd|rd|th)\s+(?:step|line)\b", re.I),
    re.compile(r"\b(" + "|".join(ORDINALS) + r")\s+(?:step|line)\b", re.I),
]
# Runs of maths: digits, x, operators, brackets, `=`; must hold an operator or `=`.
MATH_SPAN = re.compile(r"[-−(]?[0-9x(][0-9x+\-−*/^=().·×\s]*[0-9x)]")


def _norm(s: str) -> str:
    s = s.replace("−", "-").replace("·", "").replace("×", "").replace("*", "")
    return re.sub(r"\s+", "", s).lower()


def explicit_step(text: str) -> int | None:
    hits = []
    for pat in EXPLICIT:
        for m in pat.finditer(text):
            g = m.group(1).lower()
            hits.append((m.start(), ORDINALS.get(g) or int(g)))
    return min(hits)[1] if hits else None  # the first step named in the sentence


def quoted_step(text: str, steps: list[str]) -> int | None:
    normed = [_norm(s) for s in steps]
    candidates = []
    for m in MATH_SPAN.finditer(text):
        span = _norm(m.group(0))
        if len(span) < 3 or not re.search(r"[-+/=x]", span[1:]):
            continue  # a lone number like "12" or "-3" is too weak to tie to a step
        where = [i for i, s in enumerate(normed, start=1) if span in s]
        if len(where) == 1:
            candidates.append(where[0])
    return max(candidates) if candidates else None


def mentioned_step(feedback: str | None, steps: list[str]) -> int | None:
    if not feedback:
        return None
    k = explicit_step(feedback)
    return k if k is not None else quoted_step(feedback, steps)


def faithfulness_label(flagged: int | None, feedback: str | None, steps: list[str]) -> str | None:
    """'faithful', 'unfaithful' (names another step) or 'unspecified'; None when not scorable."""
    if flagged is None or flagged == 0:
        return None
    k = mentioned_step(feedback, steps)
    if k is None:
        return "unspecified"
    return "faithful" if k == flagged else "unfaithful"
