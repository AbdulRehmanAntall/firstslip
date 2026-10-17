"""FirstSlip student app: check a worked solution step by step.

The page checks every step in the browser: Pyodide runs core/checker.py and
app/checking.py unchanged, so it also works as a free static Space. This server
adds the model's explanation (POST /api/explain), which needs a token and so
cannot run in the browser. POST /api/check is the same checker as an API.

Nothing the student types is logged or stored; the only state is an in-memory
request counter per session cookie.

Run locally:  uvicorn app.main:app --no-access-log
"""
import os
import secrets
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import feedback
from .checking import BROWSER_FILES, MAX_CHARS, MAX_STEPS, check_solution, report_dict

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).parent / "static"
CHECKS_PER_SESSION = int(os.environ.get("CHECKS_PER_SESSION", "40"))
EXPLAINS_PER_SESSION = int(os.environ.get("EXPLAINS_PER_SESSION", "15"))
EXPLAINS_PER_DAY = int(os.environ.get("EXPLAINS_PER_DAY", "300"))  # protects the inference budget
COOKIE = "fs_session"


class Caps:
    """In-memory counters only: session id -> (checks, explanations), plus one daily total."""

    def __init__(self):
        self.lock = threading.Lock()
        self.sessions: dict[str, list[int]] = {}
        self.day, self.explains_today = time.strftime("%Y-%m-%d"), 0

    def take_check(self, sid: str) -> bool:
        with self.lock:
            c = self.sessions.setdefault(sid, [0, 0])
            if c[0] >= CHECKS_PER_SESSION:
                return False
            c[0] += 1
            return True

    def take_explain(self, sid: str) -> str | None:
        """None if allowed, else the reason it is not."""
        with self.lock:
            today = time.strftime("%Y-%m-%d")
            if today != self.day:
                self.day, self.explains_today = today, 0
            c = self.sessions.setdefault(sid, [0, 0])
            if c[1] >= EXPLAINS_PER_SESSION:
                return "session"
            if self.explains_today >= EXPLAINS_PER_DAY:
                return "day"
            c[1] += 1
            self.explains_today += 1
            return None


caps = Caps()
app = FastAPI(title="FirstSlip", docs_url=None, redoc_url=None, openapi_url=None)


class CheckIn(BaseModel):
    problem: str = Field(max_length=MAX_CHARS)
    steps: list[str] = Field(max_length=MAX_STEPS)


def _session(request: Request, response: Response) -> str:
    sid = request.cookies.get(COOKIE)
    if not sid or len(sid) > 64:
        sid = secrets.token_urlsafe(16)
    response.set_cookie(COOKIE, sid, httponly=True, samesite="lax", max_age=12 * 3600)
    return sid


def _explain(rep, sid: str) -> dict:
    """The model's guess for a checked solution, or a note saying why there is none."""
    why = caps.take_explain(sid)
    if why == "session":
        return {"guess": None, "guess_note": "You have used this session's model explanations. The checker still works."}
    if why == "day":
        return {"guess": None, "guess_note": "The model's daily limit has been reached. The checker still works."}
    try:
        return {"guess": feedback.explain(rep.problem_display, rep.step_displays, rep.first_error), "guess_note": None}
    except feedback.Unavailable:
        return {"guess": None, "guess_note": "The model is unavailable right now. The checker's result above still stands."}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/py/{path:path}")
def python_source(path: str):
    """The Python files the browser build runs (and only those)."""
    if path not in BROWSER_FILES:
        raise HTTPException(404)
    return FileResponse(ROOT / path, media_type="text/plain")


@app.post("/api/check")
def api_check(body: CheckIn, request: Request, response: Response):
    sid = _session(request, response)
    if not caps.take_check(sid):
        return JSONResponse({"error": f"You have used all {CHECKS_PER_SESSION} checks for this session. "
                                      "Please come back later."}, status_code=429)
    rep = check_solution(body.problem, body.steps)
    out = report_dict(rep) | {"guess": None, "guess_note": None}
    if rep.first_error:
        out |= _explain(rep, sid)
    return out


@app.post("/api/explain")
def api_explain(body: CheckIn, request: Request, response: Response):
    """The model's guess only. The solution is re-checked here, so the step given to the model is the checker's."""
    sid = _session(request, response)
    rep = check_solution(body.problem, body.steps)
    if not rep.first_error:
        return {"guess": None, "guess_note": None}
    return _explain(rep, sid)


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
