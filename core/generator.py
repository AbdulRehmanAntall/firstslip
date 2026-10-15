"""Synthetic algebra solutions with one injected misconception (Phase 1).

Rebuilt from scratch from Sonkar et al. (2024), Table 1 and Figure 1 (MalAlgoPy's
code is not public). A *state* is an equation type plus its integer coefficients.
A correct reduction maps a state to the next state in one step; a misconception
maps it to a wrong state instead, and the solution then continues with correct
reductions from that wrong state, so the injected step is the only error.

Every state knows its own solution exactly (`linear` gives a*x = b over Fractions),
so labels here never depend on the SymPy checker; the checker is tested against
them in scripts/phase1_gate.py.
"""
import random
from dataclasses import dataclass
from fractions import Fraction

MIN_STEPS, MAX_STEPS = 3, 6
COEF_RANGE = [v for v in range(-12, 13) if v != 0]
MAX_DENOMINATOR = 12  # "integers or simple fractions"


class Degenerate(ValueError):
    """A state that cannot be shown as a sensible step (zero x coefficient, 0*(...), ...)."""


# --------------------------------------------------------------------------- rendering

def xt(c) -> str:
    if c == 0:
        raise Degenerate("zero x coefficient")
    return "x" if c == 1 else "-x" if c == -1 else f"{c}x"


def num(v) -> str:
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def fac(v) -> str:
    """A factor in a product: negatives in parentheses."""
    return f"({v})" if v < 0 else str(v)


def fmt_sum(items) -> str:
    """Join signed term strings ("3x", "-5", "2*(-4)") as "3x - 5 + 2*(-4)". None and 0 are skipped."""
    items = [t for t in items if t is not None and t != "0"]
    if not items:
        return "0"
    out = items[0]
    for t in items[1:]:
        out += f" - {t[1:]}" if t.startswith("-") else f" + {t}"
    return out


def c0(v):
    return str(v)


def dist(k, inner: str) -> str:
    if k == 0:
        raise Degenerate("zero factor")
    head = "" if k == 1 else "-" if k == -1 else str(k)
    return f"{head}({inner})"


# --------------------------------------------------------------------------- equation types
# Each type: render(c) -> text, linear(c) -> (a, b) meaning a*x = b, step(c) -> correct next states.
# Coefficient names follow the type's form, e.g. T5 is (A, B, C) for "Ax + B = C".

TYPES = {
    "T1": dict(form="Ax = B",
               render=lambda a, b: f"{xt(a)} = {c0(b)}",
               linear=lambda a, b: (a, b),
               step=lambda a, b: [("X", (Fraction(b, a),))] if a != 0 else []),
    "X": dict(form="x = v",
              render=lambda v: f"x = {num(v)}",
              linear=lambda v: (1, v),
              step=lambda v: []),
    "T2": dict(form="Ax = B + C",
               render=lambda a, b, c: f"{xt(a)} = {fmt_sum([c0(b), c0(c)])}",
               linear=lambda a, b, c: (a, b + c),
               step=lambda a, b, c: [("T1", (a, b + c))]),
    "T3": dict(form="Ax = B·C",
               render=lambda a, b, c: f"{xt(a)} = {b}*{fac(c)}",
               linear=lambda a, b, c: (a, b * c),
               step=lambda a, b, c: [("T1", (a, b * c))]),
    "T4": dict(form="Ax + Bx = C",
               render=lambda a, b, c: f"{fmt_sum([xt(a), xt(b)])} = {c0(c)}",
               linear=lambda a, b, c: (a + b, c),
               step=lambda a, b, c: [("T1", (a + b, c))]),
    "T5": dict(form="Ax + B = C",
               render=lambda a, b, c: f"{fmt_sum([xt(a), c0(b)])} = {c0(c)}",
               linear=lambda a, b, c: (a, c - b),
               step=lambda a, b, c: [("T2", (a, c, -b))]),
    "T6": dict(form="A + Bx = C",
               render=lambda a, b, c: f"{fmt_sum([c0(a), xt(b)])} = {c0(c)}",
               linear=lambda a, b, c: (b, c - a),
               step=lambda a, b, c: [("T2", (b, c, -a))]),
    "T7": dict(form="Ax = Bx + C",
               render=lambda a, b, c: f"{xt(a)} = {fmt_sum([xt(b), c0(c)])}",
               linear=lambda a, b, c: (a - b, c),
               step=lambda a, b, c: [("T4", (a, -b, c))]),
    "T8": dict(form="Ax = B(C·D)",
               render=lambda a, b, c, d: f"{xt(a)} = {dist(b, f'{c}*{fac(d)}')}",
               linear=lambda a, b, c, d: (a, b * c * d),
               step=lambda a, b, c, d: [("T3", (a, b, c * d))]),
    "T9": dict(form="Ax = B(Cx + D)",
               render=lambda a, b, c, d: f"{xt(a)} = {dist(b, fmt_sum([xt(c), c0(d)]))}",
               linear=lambda a, b, c, d: (a - b * c, b * d),
               step=lambda a, b, c, d: [("T7", (a, b * c, b * d))]),
    "T10": dict(form="Ax = B + C·D",
                render=lambda a, b, c, d: f"{xt(a)} = {fmt_sum([c0(b), f'{c}*{fac(d)}'])}",
                linear=lambda a, b, c, d: (a, b + c * d),
                step=lambda a, b, c, d: [("T2", (a, b, c * d))]),
    "T11": dict(form="A + Bx + Cx = D",
                render=lambda a, b, c, d: f"{fmt_sum([c0(a), xt(b), xt(c)])} = {c0(d)}",
                linear=lambda a, b, c, d: (b + c, d - a),
                step=lambda a, b, c, d: [("T6", (a, b + c, d))]),
    "T12": dict(form="Ax = B + C(Dx + E)",
                render=lambda a, b, c, d, e: f"{xt(a)} = {fmt_sum([c0(b), dist(c, fmt_sum([xt(d), c0(e)]))])}",
                linear=lambda a, b, c, d, e: (a - c * d, b + c * e),
                step=lambda a, b, c, d, e: [("T12d", (a, b, c * d, c * e)), ("T12m", (a, -b, c, d, e))]),
    # T12d (T12 after distributing) and T12m (T12 after moving B) are not among
    # Sonkar et al.'s forms; they give T12 two correct routes, of 5 and 6 steps.
    "T12m": dict(form="Ax + B = C(Dx + E)",
                 render=lambda a, b, c, d, e: f"{fmt_sum([xt(a), c0(b)])} = {dist(c, fmt_sum([xt(d), c0(e)]))}",
                 linear=lambda a, b, c, d, e: (a - c * d, c * e - b),
                 step=lambda a, b, c, d, e: [("T14", (a, b, c * d, c * e))]),
    "T12d": dict(form="Ax = B + Cx + D",
                 render=lambda a, b, c, d: f"{xt(a)} = {fmt_sum([c0(b), xt(c), c0(d)])}",
                 linear=lambda a, b, c, d: (a - c, b + d),
                 step=lambda a, b, c, d: [("T15", (a, -c, b, d))]),
    "T14": dict(form="Ax + B = Cx + D",
                render=lambda a, b, c, d: f"{fmt_sum([xt(a), c0(b)])} = {fmt_sum([xt(c), c0(d)])}",
                linear=lambda a, b, c, d: (a - c, d - b),
                step=lambda a, b, c, d: [("T15", (a, -c, d, -b))]),
    "T15": dict(form="Ax + Bx = C + D",
                render=lambda a, b, c, d: f"{fmt_sum([xt(a), xt(b)])} = {fmt_sum([c0(c), c0(d)])}",
                linear=lambda a, b, c, d: (a + b, c + d),
                step=lambda a, b, c, d: [("T2", (a + b, c, d)), ("T4", (a, b, c + d))]),
    "T16": dict(form="Ax = Bx + C + D",
                render=lambda a, b, c, d: f"{xt(a)} = {fmt_sum([xt(b), c0(c), c0(d)])}",
                linear=lambda a, b, c, d: (a - b, c + d),
                step=lambda a, b, c, d: [("T15", (a, -b, c, d))]),
}

START_TYPES = ["T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12", "T14", "T15", "T16"]
# Positions (0-based) of coefficients that are multiplicative factors; |factor| >= 2.
FACTORS = {"T8": (1, 2, 3), "T9": (1,), "T10": (2, 3), "T12": (2,)}
ARITY = {"T5": 3, "T6": 3, "T7": 3, "T8": 4, "T9": 4, "T10": 4, "T11": 4, "T12": 5,
         "T14": 4, "T15": 4, "T16": 4}


def render(state) -> str:
    t, c = state
    return TYPES[t]["render"](*c)


def solution(state):
    """The unique solution of a state, or None if it has none or infinitely many."""
    t, c = state
    a, b = TYPES[t]["linear"](*c)
    return None if a == 0 else Fraction(b) / Fraction(a)


def correct_steps(state, rng: random.Random):
    nxt = TYPES[state[0]]["step"](*state[1])
    return rng.choice(nxt) if nxt else None


# --------------------------------------------------------------------------- misconceptions
# Sonkar et al. (2024), Table 1. Family and split follow PREREGISTRATION.md section 2.

@dataclass(frozen=True)
class Misconception:
    id: str
    rule: str
    family: str
    heldout: bool
    types: tuple  # state types the rule is applied to here


def _pair(p, q, mid):
    """M14/M15/M17/M18 on a displayed pair "p + q" (q > 0) or "p - |q|" (q < 0)."""
    if mid == "M14" and q > 0:
        return p - q
    if mid == "M15" and q < 0:
        return p - q
    if mid == "M17" and q > 0:
        return q - p
    if mid == "M18" and q < 0:
        return -q - p
    return None


def _apply_pair(state, mid):
    """Apply a pair rule to every "+"/"-" pair in the state. Returns [(new_state, custom_text)]."""
    t, c = state
    out = []
    if t == "T2":
        a, b, cc = c
        if (v := _pair(b, cc, mid)) is not None:
            out.append((("T1", (a, v)), None))
    elif t == "T4":
        a, b, cc = c
        if (v := _pair(a, b, mid)) is not None:
            out.append((("T1", (v, cc)), None))
    elif t == "T11":
        a, b, cc, d = c
        if (v := _pair(b, cc, mid)) is not None:
            out.append((("T6", (a, v, d)), None))
    elif t == "T15":
        a, b, cc, d = c
        if (v := _pair(a, b, mid)) is not None:
            out.append((("T2", (v, cc, d)), None))
        if (v := _pair(cc, d, mid)) is not None:
            out.append((("T4", (a, b, v)), None))
    return out


def _m1(state):
    t, c = state
    if t == "T8":
        a, b, cc, d = c
        return [(("T10", (a, b, cc, d)), None)]
    if t == "T9":
        a, b, cc, d = c
        return [(("T12d", (a, b, cc, d)), None)]
    if t == "T12":
        a, b, cc, d, e = c
        text = f"{xt(a)} = {fmt_sum([c0(b), c0(cc), xt(d), c0(e)])}"
        return [(("T12d", (a, b + cc, d, e)), text)]
    if t == "T12m":
        a, b, cc, d, e = c
        text = f"{fmt_sum([xt(a), c0(b)])} = {fmt_sum([c0(cc), xt(d), c0(e)])}"
        return [(("T14", (a, b, d, cc + e)), text)]
    return []


def _m2(state):  # A(Bx ± C) -> ABx ± C
    t, c = state
    if t == "T9":
        a, b, cc, d = c
        return [(("T7", (a, b * cc, d)), None)]
    if t == "T12":
        a, b, cc, d, e = c
        return [(("T12d", (a, b, cc * d, e)), None)]
    if t == "T12m":
        a, b, cc, d, e = c
        return [(("T14", (a, b, cc * d, e)), None)]
    return []


def _m3(state):  # A ± B(part) -> (A ± B)(part)
    t, c = state
    if t == "T10":
        a, b, cc, d = c
        return [(("T3", (a, b + cc, d)), None)]
    if t == "T12":
        a, b, cc, d, e = c
        return [(("T9", (a, b + cc, d, e)), None)]
    return []


def _m4(state):  # A(B·C) -> AB·AC
    t, c = state
    if t == "T8":
        a, b, cc, d = c
        return [(("T3", (a, b * cc, b * d)), None)]
    return []


def _m5(state):  # A(Bx ± C) -> A(ABx ± AC)
    t, c = state
    if t == "T9":
        a, b, cc, d = c
        return [(("T9", (a, b, b * cc, b * d)), None)]
    if t == "T12":
        a, b, cc, d, e = c
        return [(("T12", (a, b, cc, cc * d, cc * e)), None)]
    if t == "T12m":
        a, b, cc, d, e = c
        return [(("T12m", (a, b, cc, cc * d, cc * e)), None)]
    return []


def _m6(state):  # -A(Bx - C) -> -ABx - AC
    t, c = state
    if t == "T9":
        a, b, cc, d = c
        if b < 0 and d < 0:
            return [(("T7", (a, b * cc, -b * d)), None)]
    if t == "T12":
        a, b, cc, d, e = c
        if cc < 0 and e < 0:
            return [(("T12d", (a, b, cc * d, -cc * e)), None)]
    if t == "T12m":
        a, b, cc, d, e = c
        if cc < 0 and e < 0:
            return [(("T14", (a, b, cc * d, -cc * e)), None)]
    return []


def _m8(state):  # A(Bx ± C) -> Bx ± AC
    t, c = state
    if t == "T9":
        a, b, cc, d = c
        return [(("T7", (a, cc, b * d)), None)]
    if t == "T12":
        a, b, cc, d, e = c
        return [(("T12d", (a, b, d, cc * e)), None)]
    if t == "T12m":
        a, b, cc, d, e = c
        return [(("T14", (a, b, d, cc * e)), None)]
    return []


def _m11(state):  # Ax ± B = Cx ± D -> Ax + Cx = B + D (moves terms without changing sign)
    t, c = state
    if t == "T14":
        a, b, cc, d = c
        return [(("T15", (a, cc, b, d)), None)]
    return []


def _m12(state):  # Ax ± B -> (A ± B)x
    t, c = state
    if t == "T5":
        a, b, cc = c
        return [(("T1", (a + b, cc)), None)]
    if t == "T6":
        a, b, cc = c
        return [(("T1", (a + b, cc)), None)]
    if t == "T7":
        a, b, cc = c
        return [(("T7", (a, b + cc, 0)), None)]
    return []


def _m13(state):  # Ax ± B -> (A ± B): the x is dropped
    t, c = state
    if t == "T7":
        a, b, cc = c
        return [(("T1", (a, b + cc)), None)]
    return []


def _m16(state):  # part1 · part2 -> part1 + part2
    t, c = state
    if t == "T3":
        a, b, cc = c
        return [(("T2", (a, b, cc)), None)]
    if t == "T10":
        a, b, cc, d = c
        return [(("T2", (a, b, cc + d)), f"{xt(a)} = {fmt_sum([c0(b), c0(cc), c0(d)])}")]
    return []


def _division(fn):
    def apply(state):
        t, c = state
        if t != "T1":
            return []
        v = fn(*c)
        return [] if v is None else [(("X", (Fraction(v),)), None)]
    return apply


RULES = {
    "M1": (_m1, "A(part) -> A + (part)", "distribution", False, ("T8", "T9", "T12", "T12m")),
    "M2_S3": (_m2, "A(Bx ± C) -> ABx ± C", "distribution", True, ("T9", "T12", "T12m")),
    "M3": (_m3, "A ± B(part) -> (A ± B)(part)", "distribution", False, ("T10", "T12")),
    "M4": (_m4, "A(B·C) -> AB·AC", "distribution", False, ("T8",)),
    "M5": (_m5, "A(Bx ± C) -> A(ABx ± AC)", "distribution", False, ("T9", "T12", "T12m")),
    "M6": (_m6, "-A(Bx - C) -> -ABx - AC", "sign", True, ("T9", "T12", "T12m")),
    "M8": (_m8, "A(Bx ± C) -> Bx ± AC", "distribution", False, ("T9", "T12", "T12m")),
    "M11": (_m11, "Ax ± B = Cx ± D -> Ax + Cx = B + D", "term-combining", True, ("T14",)),
    "M12_S15": (_m12, "Ax ± B -> (A ± B)x", "term-combining", False, ("T5", "T6", "T7")),
    "M13": (_m13, "Ax ± B -> (A ± B)", "term-combining", False, ("T7",)),
    "M14": (lambda s: _apply_pair(s, "M14"), "part1 + part2 -> part1 - part2", "sign", False, ("T2", "T4", "T11", "T15")),
    "M15": (lambda s: _apply_pair(s, "M15"), "part1 - part2 -> part1 + part2", "sign", False, ("T2", "T4", "T11", "T15")),
    "M16": (_m16, "part1 · part2 -> part1 + part2", "sign", False, ("T3", "T10")),
    "M17": (lambda s: _apply_pair(s, "M17"), "A + B -> B - A", "sign", False, ("T2", "T4", "T11", "T15")),
    "M18": (lambda s: _apply_pair(s, "M18"), "A - B -> B - A", "sign", False, ("T2", "T4", "T11", "T15")),
    "M19": (_division(lambda a, b: a + b), "Ax = B -> x = A + B", "division", False, ("T1",)),
    "M20_S20": (_division(lambda a, b: b), "Ax = B -> x = B (divides one side only)", "division", True, ("T1",)),
    "M21": (_division(lambda a, b: a - b), "Ax = B -> x = A - B", "division", False, ("T1",)),
    "M22_S1": (_division(lambda a, b: Fraction(a, b) if b else None), "Ax = B -> x = A / B", "division", False, ("T1",)),
}
MISCONCEPTIONS = {k: Misconception(k, rule, fam, held, types) for k, (_, rule, fam, held, types) in RULES.items()}
SEEN = [k for k, m in MISCONCEPTIONS.items() if not m.heldout]
HELDOUT = [k for k, m in MISCONCEPTIONS.items() if m.heldout]


# --------------------------------------------------------------------------- solutions

def sample_problem(t: str, rng: random.Random):
    c = [rng.choice(COEF_RANGE) for _ in range(ARITY[t])]
    for i in FACTORS.get(t, ()):
        while abs(c[i]) < 2:
            c[i] = rng.choice(COEF_RANGE)
    return (t, tuple(c))


def continue_chain(state, rng: random.Random) -> list:
    """Correct reductions from `state` until x = v; returns the states after `state`."""
    out = []
    while state[0] != "X":
        state = correct_steps(state, rng)
        if state is None:
            raise Degenerate("no correct reduction (zero coefficient)")
        out.append(state)
        if len(out) > MAX_STEPS + 2:
            raise Degenerate("chain too long")
    return out


def lines_ok(problem_text: str, lines: list[str]) -> None:
    prev = problem_text
    for ln in lines:
        if ln == prev:
            raise Degenerate("repeated line")
        prev = ln


@dataclass
class Solution:
    start: tuple
    states: list  # states after the problem, one per step
    texts: list  # rendered steps
    first_error: int  # 1-based, 0 = clean
    misconception: str | None = None


def clean_solution(start, rng: random.Random) -> Solution:
    states = continue_chain(start, rng)
    if not MIN_STEPS <= len(states) <= MAX_STEPS:
        raise Degenerate("length")
    texts = [render(s) for s in states]
    lines_ok(render(start), texts)
    return Solution(start, states, texts, 0)


def injections(start, clean: Solution, mid: str, rng: random.Random, drops: dict) -> list[Solution]:
    """Every way to inject `mid` into the clean chain, keeping the steps before it identical."""
    fn = RULES[mid][0]
    truth = solution(start)
    chain = [start] + clean.states
    out = []
    for k in range(1, len(chain)):  # step k replaces chain[k-1] -> chain[k]
        before = chain[k - 1]
        try:
            options = fn(before)
        except Degenerate:
            drops["degenerate"] += 1
            continue
        for wrong, custom in options:
            try:
                rest = continue_chain(wrong, rng)
                wrong_text = custom if custom is not None else render(wrong)
                texts = clean.texts[:k - 1] + [wrong_text] + [render(s) for s in rest]
                lines_ok(render(start), texts)
            except Degenerate:
                drops["degenerate"] += 1
                continue
            states = clean.states[:k - 1] + [wrong] + rest
            if not MIN_STEPS <= len(states) <= MAX_STEPS:
                drops["length"] += 1
                continue
            sols = [solution(s) for s in states[k - 1:]]
            if any(s is None for s in sols):
                drops["no_unique_solution"] += 1
                continue
            if sols[0] == solution(before):
                drops["no_change_at_injected_step"] += 1
                continue
            if any(s == truth for s in sols):
                drops["accidental_recovery"] += 1
                continue
            out.append(Solution(start, states, texts, k, mid))
    return out


def valid_start(start) -> bool:
    s = solution(start)
    return s is not None and s.denominator <= MAX_DENOMINATOR


def state_path(sol: Solution) -> list[str]:
    return [sol.start[0]] + [s[0] for s in sol.states]
