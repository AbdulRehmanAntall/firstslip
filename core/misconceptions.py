"""Fixed mapping from a feedback sentence to a misconception label (synthetic data only).

Ordered regex rules on the lower-cased sentence; the first rule that matches gives
the label, and no match gives None. More specific rules come first (e.g. "only the
first term" before plain "distribution"). The mapping is frozen on synthetic dev
before any test run and audited by hand on 100 test items (Gate 2).

Some seen misconceptions are hard to tell apart from one sentence (M17 vs M18,
M1 vs M3), so family-level accuracy is reported next to label accuracy.
"""
import re

from core.generator import MISCONCEPTIONS

MAPPING_VERSION = "m-v1"

_DIST = r"(?:distribut|multipl|expand)\w*"
_INSTEAD = r"(?:instead of|rather than|when (?:you|it) should(?: have)?|but should(?: have)?|should have)"

RULES: list[tuple[str, str]] = [
    # Division (Ax = B -> x = ...)
    ("M22_S1", r"\b(?:invert\w*|upside[- ]down|reciprocal|wrong way (?:round|around)|divided \S+ by \S+ instead of \S+ by)\b"),
    ("M20_S20", r"\b(?:only (?:on )?one side|one side only|(?:forgot|did ?n[o']t|failed) to divide (?:the )?(?:other|right|both)|divide both sides|(?:dropped|removed|ignored|left out) the (?:coefficient|\d+)\b(?!.*\bx\b))"),
    ("M19", rf"\badd\w*\b.*{_INSTEAD}\s+divid|\bdivid\w*\b.*\bnot add"),
    ("M21", rf"\bsubtract\w*\b.*{_INSTEAD}\s+divid|\bdivid\w*\b.*\bnot subtract"),
    # Term-combining
    ("M11", r"\b(?:without (?:changing|flipping|switching|reversing) (?:the |their |its )?signs?|sign\w* (?:when|after|while) (?:moving|bringing|transferring)|(?:moving|moved|bringing|brought) .*(?:across|to the other side).*sign)"),
    ("M13", r"\b(?:dropp\w*|los[te]\w*|drop|lose|forgot|omitt\w*|disappear\w*)\b.*\bx\b|\bx\b.*\b(?:dropped|lost|disappeared|vanished)\b"),
    ("M12_S15", r"\b(?:combin\w*|add\w*|merg\w*|lump\w*)\b.*\b(?:constant|number)s?\b.*\b(?:with|and|into|to)\b.*\bx\b|\bunlike terms\b|\blike terms\b"),
    # Distribution
    ("M6", r"\bnegative\b.*\b(?:sign|positive|negative)\b.*\b(?:distribut|multipl|expand)|\b(?:distribut|multipl|expand)\w*\b.*\bnegative\b|\bminus times (?:a )?minus\b|\bsign of the (?:second|constant|last) term\b"),
    ("M2_S3", rf"\b{_DIST}\b.*\bonly (?:to |into |by )?(?:the )?first term\b|\bonly (?:to |into )?(?:the )?(?:x|first) term\b|\b(?:forgot|did ?n[o']t|failed) to {_DIST} .*\b(?:second|constant|last|other) term\b|\bconstant\b.*\bnot (?:distribut|multipl)"),
    ("M8", rf"\b{_DIST}\b.*\bonly (?:to |into )?(?:the )?(?:second|constant|last|number) term\b|\b(?:forgot|did ?n[o']t|failed) to {_DIST} .*\b(?:x|first) term\b"),
    ("M5", rf"\b{_DIST}\b.*\b(?:twice|two times|again)\b|\b(?:kept|left|still) the (?:outside |outer )?(?:factor|number|coefficient)\b"),
    ("M4", rf"\b{_DIST}\b.*\b(?:each|both) (?:factor|number)s?\b|\bmultiplication is not distribut"),
    ("M3", rf"\b(?:add|subtract|combin)\w*\b.*\bbefore (?:multiplying|distributing)\b|\border of operations\b|\b(?:add|subtract|combin)\w*\b.*{_INSTEAD}\s+(?:multiplying|distributing)\b.*\bfirst\b"),
    ("M16", rf"\badd\w*\b.*{_INSTEAD}\s+multipl|\bmultipl\w*\b.*\bnot add"),
    ("M1", rf"\badd\w*\b.*\b(?:outside|factor|number in front)\b.*\b{_INSTEAD}|\b(?:forgot|did ?n[o']t|failed) to (?:distribut|multipl)"),
    # Sign / operation on a pair
    ("M17", r"\b(?:revers\w*|swapp\w*|switch\w*|wrong order|order of subtraction)\b.*\b(?:add|sum|plus)\w*"),
    ("M18", r"\b(?:revers\w*|swapp\w*|switch\w*|wrong order|order of subtraction|subtracted .* from)\b"),
    ("M14", rf"\bsubtract\w*\b.*{_INSTEAD}\s+add|\bshould (?:have )?(?:been )?add|\bnot subtract"),
    ("M15", rf"\badd\w*\b.*{_INSTEAD}\s+subtract|\bshould (?:have )?(?:been )?subtract|\bnot add"),
]
_COMPILED = [(label, re.compile(p, re.I)) for label, p in RULES]
assert {label for label, _ in RULES} == set(MISCONCEPTIONS), "every misconception needs a rule"


def map_feedback(text: str | None) -> str | None:
    if not text:
        return None
    for label, pat in _COMPILED:
        if pat.search(text):
            return label
    return None


def family(label: str | None) -> str | None:
    return MISCONCEPTIONS[label].family if label else None
