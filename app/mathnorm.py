"""Turn MathLive LaTeX into the plain arithmetic that core/checker.py reads.

The plain path (implicit multiplication, x only) is more forgiving than SymPy's
LaTeX grammar: it reads "5x\\cdot2", Unicode minus signs and decimals, which the
LaTeX parser rejects or turns into floats. Anything that cannot be converted
(\\sqrt, unknown commands) returns None, and the caller falls back to LaTeX.
"""
import re

PLAIN_OK = re.compile(r"^[0-9x+\-*/^().=]+$")  # core.checker.PLAIN_OK, plus "="

_SIMPLE = [
    ("−", "-"), ("×", "*"), ("·", "*"), ("÷", "/"),
    (r"\left", ""), (r"\right", ""), (r"\cdot", "*"), (r"\times", "*"), (r"\div", "/"),
    (r"\lparen", "("), (r"\rparen", ")"), (r"\,", ""), (r"\;", ""), (r"\:", ""), (r"\!", ""),
    (r"\ ", ""), ("~", ""), (r"\mathrm{x}", "x"),
]
_DECIMAL = re.compile(r"(\d+)\.(\d+)")


def _group(s: str, i: int) -> tuple[str, int]:
    """Return the contents of the brace group (or single character) at s[i], and the index after it."""
    if s[i] != "{":
        return s[i], i + 1
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j], j + 1
    raise ValueError("unbalanced braces")


def _fracs(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        for cmd in (r"\dfrac", r"\tfrac", r"\frac"):
            if s.startswith(cmd, i):
                num, i = _group(s, i + len(cmd))
                den, i = _group(s, i)
                out.append(f"(({_fracs(num)})/({_fracs(den)}))")
                break
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def latex_to_plain(latex: str, exact: bool = True) -> str | None:
    """Plain text for the checker; exact=False keeps decimals as typed (for display)."""
    s = latex.strip()
    if not s or "placeholder" in s:
        return None
    for a, b in _SIMPLE:
        s = s.replace(a, b)
    try:
        s = _fracs(s)
    except (ValueError, IndexError):
        return None
    s = s.replace("{", "(").replace("}", ")").replace(" ", "")
    if "\\" in s or not PLAIN_OK.match(s):
        return None
    if not exact:
        return s
    # Decimals as exact fractions, so 0.5x = 1 has the solution {2}, not {2.0}.
    return _DECIMAL.sub(lambda m: f"({int(m[1] + m[2])}/{10 ** len(m[2])})", s)


def pretty(plain: str) -> str:
    """Spacing for display and for the model prompt: '-3x=2(x-6)' -> '-3x = 2(x - 6)'."""
    s = re.sub(r"\s*=\s*", " = ", plain)
    return re.sub(r"(?<=[\w)])\s*([+\-])\s*", r" \1 ", s)
