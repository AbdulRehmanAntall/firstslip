"""OpenAI client with a response cache and a hard spending cap.

- Cache: every response is stored in SQLite (`.cache/llm.sqlite`), keyed by a hash
  of (model, instructions, input, params). A cached call costs nothing and is
  never sent again.
- Spending cap: before each paid call the worst-case cost (input estimate plus
  max_output_tokens at the output price) is reserved against the cap in the same
  database; after the call the reservation is replaced by the actual cost. A call
  that could push total spend over the cap raises BudgetExceeded and is not sent.
- Prices (USD per 1M tokens) and the cap live in config/phase2.json.
"""
import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "phase2.json"
CACHE_PATH = ROOT / ".cache" / "llm.sqlite"


class BudgetExceeded(RuntimeError):
    pass


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def est_tokens(text: str) -> int:
    return len(text) // 3 + 1  # deliberately high (≈4 chars/token in English)


@dataclass
class Reply:
    text: str
    model_version: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost: float
    cached: bool


class Ledger:
    """Cache and spend ledger in one SQLite file, safe across threads."""

    def __init__(self, path: Path = CACHE_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, model TEXT, reply TEXT, time REAL)")
            self._db.execute("CREATE TABLE IF NOT EXISTS spend (key TEXT PRIMARY KEY, model TEXT, cost REAL, final INTEGER, time REAL)")
            self._db.execute("DELETE FROM spend WHERE final = 0")  # reservations left by a crashed run

    def get(self, key: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT reply FROM cache WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def spent(self) -> float:
        with self._lock:
            return self._db.execute("SELECT COALESCE(SUM(cost), 0) FROM spend").fetchone()[0]

    def reserve(self, key: str, model: str, worst: float, cap: float) -> None:
        with self._lock, self._db:
            total = self._db.execute("SELECT COALESCE(SUM(cost), 0) FROM spend").fetchone()[0]
            if total + worst > cap:
                raise BudgetExceeded(f"spent+reserved ${total:.4f} + worst case ${worst:.4f} > cap ${cap:.2f}")
            self._db.execute("INSERT OR REPLACE INTO spend VALUES (?, ?, ?, 0, ?)", (key, model, worst, time.time()))

    def release(self, key: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM spend WHERE key = ? AND final = 0", (key,))

    def commit(self, key: str, model: str, reply: dict, cost: float) -> None:
        with self._lock, self._db:
            self._db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)", (key, model, json.dumps(reply), time.time()))
            self._db.execute("INSERT OR REPLACE INTO spend VALUES (?, ?, ?, 1, ?)", (key, model, cost, time.time()))


def request_key(model: str, instructions: str, input: str, params: dict) -> str:
    blob = json.dumps({"model": model, "instructions": instructions, "input": input, "params": params}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


class Client:
    def __init__(self, model_name: str, config: dict | None = None, ledger: Ledger | None = None, api=None):
        config = config or load_config()
        self.cap = float(config["spend_cap_usd"])
        spec = config["models"][model_name]
        self.model = spec["model"]
        self.prices = spec["prices"]  # USD per 1M tokens: input, cached_input, output
        self.params = {k: spec[k] for k in ("reasoning_effort", "max_output_tokens", "service_tier") if spec.get(k) is not None}
        self.ledger = ledger or Ledger()
        self._api = api  # injected in tests; created lazily otherwise

    @property
    def api(self):
        if self._api is None:
            from openai import OpenAI
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is not set")
            self._api = OpenAI(max_retries=5, timeout=900)
        return self._api

    def cost(self, input_tokens: int, cached: int, output_tokens: int) -> float:
        p = self.prices
        return ((input_tokens - cached) * p["input"] + cached * p["cached_input"] + output_tokens * p["output"]) / 1e6

    def worst_case(self, instructions: str, input: str) -> float:
        return self.cost(est_tokens(instructions + input) + 50, 0, self.params.get("max_output_tokens", 4000))

    def is_cached(self, instructions: str, input: str) -> bool:
        return self.ledger.get(request_key(self.model, instructions, input, self.params)) is not None

    def complete(self, instructions: str, input: str) -> Reply:
        key = request_key(self.model, instructions, input, self.params)
        hit = self.ledger.get(key)
        if hit is not None:
            return Reply(**{**hit, "cost": 0.0, "cached": True})
        self.ledger.reserve(key, self.model, self.worst_case(instructions, input), self.cap)
        try:
            kwargs = {"model": self.model, "instructions": instructions, "input": input, "store": False}
            if "reasoning_effort" in self.params:
                kwargs["reasoning"] = {"effort": self.params["reasoning_effort"]}
            if "max_output_tokens" in self.params:
                kwargs["max_output_tokens"] = self.params["max_output_tokens"]
            if "service_tier" in self.params:
                kwargs["service_tier"] = self.params["service_tier"]
            resp = self.api.responses.create(**kwargs)
        except BaseException:
            self.ledger.release(key)
            raise
        u = resp.usage
        cached_in = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        reasoning = getattr(getattr(u, "output_tokens_details", None), "reasoning_tokens", 0) or 0
        cost = self.cost(u.input_tokens, cached_in, u.output_tokens)
        reply = {"text": resp.output_text or "", "model_version": resp.model,
                 "input_tokens": u.input_tokens, "cached_input_tokens": cached_in,
                 "output_tokens": u.output_tokens, "reasoning_tokens": reasoning}
        self.ledger.commit(key, self.model, reply, cost)
        return Reply(**reply, cost=cost, cached=False)
