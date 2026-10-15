"""One JSONL file per run, headed by git commit, seed and config hash."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def git_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip()
        return sha + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def config_hash(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


class RunLog:
    def __init__(self, name: str, config: dict, seed: int):
        RUNS_DIR.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = RUNS_DIR / f"{stamp}_{name}.jsonl"
        self._f = self.path.open("w", encoding="utf-8")
        self.write({
            "type": "header",
            "run": name,
            "time_utc": stamp,
            "git_commit": git_commit(),
            "seed": seed,
            "config_hash": config_hash(config),
            "config": config,
        })

    def write(self, record: dict) -> None:
        self._f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self) -> None:
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
