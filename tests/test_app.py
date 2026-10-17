from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import feedback, main
from app.checking import check_solution
from app.mathnorm import latex_to_plain, pretty


@pytest.mark.parametrize("latex, plain", [
    (r"-3x=2\left(x-6\right)", "-3x=2(x-6)"),
    (r"x=\frac{10}{3}", "x=((10)/(3))"),
    (r"5x\cdot2=10", "5x*2=10"),
    ("2x−3=1", "2x-3=1"),
    (r"x^{2}=4", "x^(2)=4"),
    (r"\frac{2x+1}{3}=x-1", "((2x+1)/(3))=x-1"),
])
def test_latex_to_plain(latex, plain):
    assert latex_to_plain(latex) == plain


def test_decimals_become_exact():
    assert latex_to_plain("0.5x=1") == "(5/10)x=1"
    assert latex_to_plain("0.5x=1", exact=False) == "0.5x=1"


@pytest.mark.parametrize("latex", ["", r"\placeholder{}", r"y=3", r"\sqrt{x}=2", r"\frac{1}{2"])
def test_unconvertible_returns_none(latex):
    assert latex_to_plain(latex) is None


def test_pretty():
    assert pretty("-3x=2(x-6)") == "-3x = 2(x - 6)"


def test_first_error_and_marks():
    rep = check_solution(r"-3x=2\left(x-6\right)", ["-3x=2x-12", "-3x=-10", r"x=\frac{10}{3}"])
    assert rep.first_error == 2
    assert [s["status"] for s in rep.steps] == ["same", "changed", "same"]
    err = next(v for v in rep.verified if v["kind"] == "error")
    assert err["before"]["text"] == "x = 12/5" and err["after"]["text"] == "x = 10/3"
    assert rep.step_displays[0] == "-3x = 2x - 12"


def test_clean_solution_with_decimal_and_cdot():
    rep = check_solution("5x\\cdot2=10", ["10x=10", "0.5x=0.5", "x=1"])
    assert rep.first_error == 0
    assert [s["status"] for s in rep.steps] == ["same", "same", "same"]
    assert any(v["kind"] == "ok" for v in rep.verified)


def test_unreadable_line_is_skipped_not_marked():
    rep = check_solution("2x=6", ["2x=6", "y+1", "x=3"])
    assert [s["status"] for s in rep.steps] == ["same", "unreadable", "same"]
    assert rep.first_error == 0
    assert any(v["kind"] == "unreadable" and v["steps"] == [2] for v in rep.verified)


def test_sqrt_falls_back_to_latex():
    rep = check_solution(r"\sqrt{x}=2", ["x=4"])
    assert rep.steps[0]["status"] == "same"


def test_unreadable_problem():
    rep = check_solution("hello", ["x=1"])
    assert not rep.problem_ok and rep.steps == []


class FakeClient:
    def __init__(self, text):
        self.text, self.calls = text, []

    def chat_completion(self, messages, **kw):
        self.calls.append(messages)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))])


def test_explain_uses_frozen_prompt_with_location():
    c = FakeClient("Step: 2\nFeedback: You subtracted 2x from one side only.")
    g = feedback.explain("-3x = 2(x - 6)", ["-3x = 2x - 12", "-3x = -10"], 2, client=c)
    assert g["feedback"].startswith("You subtracted") and g["agrees"] and g["prompt"] == "p2-v1"
    assert "first wrong step is step 2" in c.calls[0][1]["content"]


def test_explain_flags_disagreement():
    g = feedback.explain("2x = 6", ["x = 6", "x = 6"], 1, client=FakeClient("Step: 2\nFeedback: Wrong."))
    assert g["step"] == 2 and not g["agrees"]


@pytest.fixture
def client(monkeypatch):
    main.caps.__init__()
    monkeypatch.setattr(main.feedback, "explain",
                        lambda p, s, k: {"feedback": "fb", "step": k, "agrees": True, "model": "m", "prompt": "p"})
    return TestClient(main.app)


def test_api_check(client):
    r = client.post("/api/check", json={"problem": "4(x+3)=20", "steps": ["4x+3=20", "4x=17"]})
    d = r.json()
    assert r.status_code == 200 and d["first_error"] == 1 and d["guess"]["feedback"] == "fb"
    assert "fs_session" in r.cookies


def test_no_model_call_on_clean_solution(client, monkeypatch):
    monkeypatch.setattr(main.feedback, "explain", lambda *a: pytest.fail("model called"))
    d = client.post("/api/check", json={"problem": "2x=6", "steps": ["x=3"]}).json()
    assert d["first_error"] == 0 and d["guess"] is None


def test_model_unavailable_keeps_checker_result(client, monkeypatch):
    def boom(*a):
        raise feedback.Unavailable("402")
    monkeypatch.setattr(main.feedback, "explain", boom)
    d = client.post("/api/check", json={"problem": "2x=6", "steps": ["x=2"]}).json()
    assert d["first_error"] == 1 and d["guess"] is None and "unavailable" in d["guess_note"]


def test_session_caps(client, monkeypatch):
    monkeypatch.setattr(main, "CHECKS_PER_SESSION", 3)
    monkeypatch.setattr(main, "EXPLAINS_PER_SESSION", 1)
    body = {"problem": "2x=6", "steps": ["x=2"]}
    first = client.post("/api/check", json=body).json()
    second = client.post("/api/check", json=body).json()
    assert first["guess"] and second["guess"] is None and "session" in second["guess_note"]
    assert client.post("/api/check", json=body).status_code == 200
    assert client.post("/api/check", json=body).status_code == 429


def test_daily_explain_cap(client, monkeypatch):
    monkeypatch.setattr(main, "EXPLAINS_PER_DAY", 1)
    body = {"problem": "2x=6", "steps": ["x=2"]}
    assert client.post("/api/check", json=body).json()["guess"]
    client.cookies.clear()  # a new session does not reset the daily cap
    assert "daily" in client.post("/api/check", json=body).json()["guess_note"]


def test_input_limits(client):
    assert client.post("/api/check", json={"problem": "x=1", "steps": ["x=1"] * 13}).status_code == 422
    assert client.post("/api/check", json={"problem": "x" * 201, "steps": []}).status_code == 422


def test_pages(client):
    assert "math-field" in client.get("/").text
    assert "FirstSlip results" in client.get("/results.html").text
    assert client.get("/results/f3_e1.png").status_code == 200
    assert client.get("/docs").status_code == 404


def test_python_sources_for_browser(client):
    assert "def check(" in client.get("/py/core/checker.py").text
    assert client.get("/py/core/llm.py").status_code == 404
    assert client.get("/py/../config/phase2.json").status_code == 404


def test_api_explain(client):
    d = client.post("/api/explain", json={"problem": "2x=6", "steps": ["x=2"]}).json()
    assert d["guess"]["step"] == 1
    assert client.post("/api/explain", json={"problem": "2x=6", "steps": ["x=3"]}).json()["guess"] is None


def test_static_bundle(tmp_path):
    import sys
    sys.path.insert(0, "scripts")
    from deploy_space import bundle_docker, bundle_static
    bundle_static(tmp_path / "s")
    files = {p.relative_to(tmp_path / "s").as_posix() for p in (tmp_path / "s").rglob("*") if p.is_file()}
    assert {"index.html", "app.js", "README.md", "py/core/checker.py", "py/app/checking.py"} <= files
    assert not any(f.startswith(("py/core/llm", "app/")) for f in files)
    bundle_docker(tmp_path / "d")
    assert (tmp_path / "d/Dockerfile").exists() and (tmp_path / "d/app/main.py").exists()
