"""Persistence for policy and engine state (JSON, atomic writes).

State is separate from the ledger on purpose: the ledger is append-only and
tamper-evident, while the policy/state file is authoritative config that can
be replaced by an operator.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from mandateguard.engine import PolicyEngine
from mandateguard.model import Policy


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True, default=str)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


class PolicyStore:
    """Loads and saves a Policy to a JSON file."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self) -> Policy:
        if not self.path.is_file():
            return Policy()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return Policy.from_dict(data)

    def save(self, policy: Policy) -> None:
        _atomic_write(self.path, policy.to_dict())


class EngineStateStore:
    """Loads and saves PolicyEngine spend/call state."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load_into(self, engine: PolicyEngine) -> None:
        if not self.path.is_file():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        engine._spend = data.get("spend", {})
        engine._calls = data.get("calls", {})
        engine._window_start = {k: float(v) for k, v in data.get("window_start", {}).items()}

    def save_from(self, engine: PolicyEngine) -> None:
        _atomic_write(
            self.path,
            {
                "spend": engine._spend,
                "calls": engine._calls,
                "window_start": engine._window_start,
            },
        )
