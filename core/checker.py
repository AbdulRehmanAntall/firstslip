"""SymPy step checker: the first step whose solution set differs from the step before it.

Steps are numbered from 1; step 0 is the problem itself, and 0 means "no error"
(the same convention as core/vtg.py). Each line is either an equation (one `=`)
or an expression. Equations are compared by their solution sets (`solveset` over
the reals); expressions by `simplify(a - b) == 0` plus random numeric spot checks.
A line that cannot be read is marked "unreadable" and skipped: the next readable
line is compared with the last readable one.
"""
import random
import re
from dataclasses import dataclass, field
from functools import lru_cache

import sympy as sp
from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                        parse_expr, standard_transformations)

X = sp.Symbol("x")
TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
# parse_expr calls eval, so plain-text input is restricted to arithmetic on x.
PLAIN_OK = re.compile(r"^[0-9x+\-*/^().\s]+$")
SPOT_CHECKS = 5


class Unreadable(ValueError):
    pass


@dataclass(frozen=True)
class Line:
    kind: str  # "eq" or "expr"
    value: object  # solution set (eq) or SymPy expression (expr)


@dataclass
class StepResult:
    index: int
    text: str
    status: str  # "same", "changed", "unreadable" or "incomparable"


@dataclass
class CheckResult:
    first_error: int  # 0 = no error found among readable steps
    steps: list[StepResult] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return all(s.status in ("same", "changed") for s in self.steps)


def _parse_side(text: str, latex: bool):
    if latex:
        from sympy.parsing.latex import parse_latex
        return parse_latex(text, backend="lark")
    if not PLAIN_OK.match(text):
        raise Unreadable(text)
    return parse_expr(text, transformations=TRANSFORMS)


@lru_cache(maxsize=200_000)
def parse_line(text: str, latex: bool = False) -> Line:
    try:
        if latex:
            node = _parse_side(text, latex=True)
            if isinstance(node, sp.Eq):
                lhs, rhs = node.lhs, node.rhs
            elif isinstance(node, sp.Expr):
                return Line("expr", node)
            else:
                raise Unreadable(text)
        else:
            parts = text.split("=")
            if len(parts) == 1:
                return Line("expr", _parse_side(parts[0], latex=False))
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                raise Unreadable(text)
            lhs, rhs = (_parse_side(p, latex=False) for p in parts)
    except Unreadable:
        raise
    except Exception as e:  # tokenizer, syntax and LaTeX errors all mean "could not read"
        raise Unreadable(text) from e
    if (lhs - rhs).free_symbols - {X}:
        raise Unreadable(text)
    return Line("eq", sp.solveset(sp.Eq(lhs, rhs), X, domain=sp.S.Reals))


def _same_expr(a, b, seed: int = 0) -> bool:
    if sp.simplify(a - b) != 0:
        return False
    rng = random.Random(seed)
    for _ in range(SPOT_CHECKS):
        v = sp.Rational(rng.randint(-50, 50), rng.randint(1, 9))
        try:
            if abs(complex(sp.N((a - b).subs(X, v)))) > 1e-9:
                return False
        except (TypeError, ZeroDivisionError):
            continue  # pole at v; skip this point
    return True


def same(a: Line, b: Line) -> bool | None:
    """True if two readable lines agree, False if not, None if they are not comparable."""
    if a.kind != b.kind:
        return None
    if a.kind == "eq":
        return a.value == b.value
    return _same_expr(a.value, b.value)


def check(problem: str, steps: list[str], latex: bool = False) -> CheckResult:
    """Return the first step (1-based) whose solution set differs from the step before it."""
    prev = parse_line(problem, latex)
    result = CheckResult(first_error=0)
    for i, text in enumerate(steps, start=1):
        try:
            line = parse_line(text, latex)
        except Unreadable:
            result.steps.append(StepResult(i, text, "unreadable"))
            continue
        verdict = same(prev, line)
        status = {True: "same", False: "changed", None: "incomparable"}[verdict]
        result.steps.append(StepResult(i, text, status))
        if verdict is False and result.first_error == 0:
            result.first_error = i
        prev = line
    return result


def solution_set(text: str, latex: bool = False):
    """Solution set of one equation line (used for the no-recovery check and tests)."""
    line = parse_line(text, latex)
    if line.kind != "eq":
        raise Unreadable(text)
    return line.value
