from core.checker import Unreadable, check, parse_line, same


def test_clean_solution_has_no_error():
    r = check("3x + 5 = 11", ["3x = 11 - 5", "3x = 6", "x = 2"])
    assert r.first_error == 0 and r.complete


def test_first_changed_step_is_reported():
    # Distributes to the first term only (M2_S3) at step 1; later steps follow from it.
    r = check("2x = 3(x + 4)", ["2x = 3x + 4", "-x = 4", "x = -4"])
    assert r.first_error == 1
    assert [s.status for s in r.steps] == ["changed", "same", "same"]


def test_error_on_last_step():
    r = check("4x = 12", ["x = 12"])
    assert r.first_error == 1


def test_unreadable_line_is_skipped_not_guessed():
    r = check("3x + 5 = 11", ["3x = 6", "x = = 2", "x = 2"])
    assert r.first_error == 0
    assert [s.status for s in r.steps] == ["same", "unreadable", "same"]
    assert not r.complete


def test_plain_text_rejects_code():
    for bad in ["__import__('os')", "x = y", "2x = sin(x)"]:
        try:
            parse_line(bad)
        except Unreadable:
            continue
        raise AssertionError(f"accepted {bad!r}")


def test_latex_lines():
    r = check(r"3x+5=11", [r"3x=6", r"x=\frac{6}{3}"], latex=True)
    assert r.first_error == 0
    r = check(r"2(x+1)=10", [r"2x+1=10"], latex=True)
    assert r.first_error == 1


def test_expressions_use_simplify_and_spot_checks():
    assert same(parse_line("2(x + 3)"), parse_line("2x + 6"))
    assert not same(parse_line("2(x + 3)"), parse_line("2x + 3"))
    assert same(parse_line("x = 1"), parse_line("2x + 6")) is None  # equation vs expression


def test_no_solution_and_identity_are_sets_too():
    assert check("x + 1 = x + 2", ["0 = 1"]).first_error == 0
    assert check("2x = 2x", ["0 = 0"]).first_error == 0
    assert check("2x = 4", ["0 = 0"]).first_error == 1
