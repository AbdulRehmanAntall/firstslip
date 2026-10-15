import random
from collections import Counter

import pytest

from core import generator as g
from core.checker import check


def test_misconception_split_matches_preregistration():
    assert len(g.MISCONCEPTIONS) == 19
    assert sorted(g.HELDOUT) == ["M11", "M20_S20", "M2_S3", "M6"]
    assert len(g.SEEN) == 15


def test_rendering():
    assert g.render(("T5", (3, -5, 11))) == "3x - 5 = 11"
    assert g.render(("T9", (2, -3, -1, 4))) == "2x = -3(-x + 4)"
    assert g.render(("T10", (2, 1, 3, -4))) == "2x = 1 + 3*(-4)"
    assert g.render(("X", (g.Fraction(-7, 3),))) == "x = -7/3"


def test_examples_from_table_1():
    # T9 2x = 3(x + 4): M2_S3 distributes to the first term only -> 2x = 3x + 4.
    (state, _), = g.RULES["M2_S3"][0](("T9", (2, 3, 1, 4)))
    assert g.render(state) == "2x = 3x + 4"
    # M20_S20 divides one side only: 4x = 12 -> x = 12.
    (state, _), = g.RULES["M20_S20"][0](("T1", (4, 12)))
    assert g.render(state) == "x = 12"
    # M6 only fires with a negative factor and a minus inside: -2(3x - 5) -> -6x - 10.
    (state, _), = g.RULES["M6"][0](("T9", (1, -2, 3, -5)))
    assert g.render(state) == "x = -6x - 10"
    assert g.RULES["M6"][0](("T9", (1, 2, 3, -5))) == []


@pytest.mark.parametrize("mid", sorted(g.MISCONCEPTIONS))
def test_injections_are_single_error_and_checker_agrees(mid):
    rng = random.Random(sorted(g.MISCONCEPTIONS).index(mid))
    drops, found = Counter(), 0
    for _ in range(4000):
        start = g.sample_problem(rng.choice(g.START_TYPES), rng)
        if not g.valid_start(start):
            continue
        try:
            clean = g.clean_solution(start, rng)
        except g.Degenerate:
            continue
        assert check(g.render(start), clean.texts).first_error == 0
        for sol in g.injections(start, clean, mid, rng, drops):
            assert g.MIN_STEPS <= len(sol.texts) <= g.MAX_STEPS
            assert check(g.render(start), sol.texts).first_error == sol.first_error
            assert g.solution(sol.states[-1]) != g.solution(start)
            found += 1
        if found >= 5:
            break
    assert found >= 5, f"{mid}: only {found} injections"
