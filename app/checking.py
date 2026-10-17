"""Per-step checking for the app: the Phase 1 checker, one line at a time.

Same logic as core.checker.check (each readable line is compared with the last
readable one), but each line is read on its own path: plain text first, LaTeX as
a fallback. Everything returned here is verified by SymPy; nothing comes from a model.
"""
from dataclasses import dataclass, field

import sympy as sp

from core.checker import X, Line, Unreadable, parse_line, same

from .mathnorm import latex_to_plain, pretty

MAX_STEPS = 12
MAX_CHARS = 200

STATUS_TEXT = {
    "same": "Follows from the line before.",
    "changed": "This step changes the answer.",
    "unreadable": "Could not read this line.",
    "incomparable": "Can't compare this line with the one before (equation vs. expression).",
    "empty": "Empty line, skipped.",
}


@dataclass
class Read:
    latex: str
    line: Line | None
    display: str  # plain text for the model prompt, or the raw LaTeX if it could not be converted


def read(latex: str) -> Read:
    latex = (latex or "")[:MAX_CHARS]
    plain = latex_to_plain(latex)
    display = latex_to_plain(latex, exact=False)
    attempts = [(plain, False)] if plain else []
    attempts.append((latex, True))
    for text, is_latex in attempts:
        try:
            line = parse_line(text, is_latex)
        except Unreadable:
            continue
        if line.kind == "expr" and line.value.free_symbols - {X}:
            continue  # the checker only knows x
        return Read(latex, line, pretty(display) if display else latex)
    return Read(latex, None, pretty(display) if display else latex)


def describe(line: Line) -> dict:
    """A solution set or expression, as text and LaTeX."""
    v = line.value
    if line.kind == "expr":
        return {"text": str(v), "latex": sp.latex(v)}
    if v == sp.S.EmptySet:
        return {"text": "no solution", "latex": r"\text{no solution}"}
    if v == sp.S.Reals:
        return {"text": "every x", "latex": r"\text{every } x"}
    if isinstance(v, sp.FiniteSet):
        vals = sorted(v, key=lambda e: float(e)) if all(e.is_real for e in v) else list(v)
        return {"text": ", ".join(f"x = {e}" for e in vals),
                "latex": r",\ ".join(f"x = {sp.latex(e)}" for e in vals)}
    return {"text": str(v), "latex": sp.latex(v)}


@dataclass
class Report:
    problem_ok: bool
    first_error: int = 0
    steps: list[dict] = field(default_factory=list)
    verified: list[dict] = field(default_factory=list)  # checker claims shown to the student
    problem_display: str = ""
    step_displays: list[str] = field(default_factory=list)


def check_solution(problem: str, steps: list[str]) -> Report:
    steps = steps[:MAX_STEPS]
    p = read(problem)
    rep = Report(problem_ok=p.line is not None and p.line.kind == "eq", problem_display=p.display)
    if not rep.problem_ok:
        rep.verified.append({"kind": "error", "text": "Could not read the problem. Type one equation in x, "
                             "for example 3(x - 2) = 12."})
        return rep
    prev, prev_index = p.line, 0
    for i, latex in enumerate(steps, start=1):
        r = read(latex)
        rep.step_displays.append(r.display)
        if not latex.strip():
            status = "empty"
        elif r.line is None:
            status = "unreadable"
        else:
            verdict = same(prev, r.line)
            status = {True: "same", False: "changed", None: "incomparable"}[verdict]
            if verdict is False and rep.first_error == 0:
                rep.first_error = i
                before = "The problem's solution is" if prev_index == 0 else f"Up to step {prev_index} the solution is"
                rep.verified.append({
                    "kind": "error", "step": i,
                    "text": f"Step {i} is the first step that changes the answer. "
                            f"{before} {describe(prev)['text']}, but step {i} gives {describe(r.line)['text']}.",
                    "before": describe(prev), "after": describe(r.line),
                })
            prev, prev_index = r.line, i
        rep.steps.append({"index": i, "status": status, "message": STATUS_TEXT[status]})
    unread = [s["index"] for s in rep.steps if s["status"] == "unreadable"]
    if unread:
        rep.verified.append({"kind": "unreadable", "steps": unread,
                             "text": "Could not read " + ", ".join(f"step {k}" for k in unread)
                                     + ". These lines were skipped, not marked right or wrong."})
    if rep.first_error == 0 and any(s["status"] == "same" for s in rep.steps):
        sol = describe(p.line)["text"]
        rep.verified.append({"kind": "ok", "text": f"Every step the checker could read keeps the same "
                             f"solution as the problem: {sol}."})
    return rep


def report_dict(rep: Report) -> dict:
    """The checker part of the API response (also what the browser build returns)."""
    return {"problem_ok": rep.problem_ok, "first_error": rep.first_error, "steps": rep.steps,
            "verified": rep.verified}


# Files the browser build (Pyodide) loads to run this module unchanged.
BROWSER_FILES = ["core/__init__.py", "core/checker.py", "app/__init__.py", "app/checking.py", "app/mathnorm.py"]
