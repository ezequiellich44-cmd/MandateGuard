import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta


class Ledger:
    """Append-only SHA-256 hash chain ledger."""

    def __init__(self, path: str = "mandateguard_audit.jsonl"):
        self._path = Path(path)
        self._chain: list[dict] = []
        self._load()

    def _load(self):
        if not self._path.exists():
            return
        with open(self._path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    self._chain.append(json.loads(line))

    def chain(self) -> list[dict]:
        return list(self._chain)

    def append(self, entry: dict) -> str:
        prev_hash = self._chain[-1]["hash"] if self._chain else "0" * 64
        entry["prev_hash"] = prev_hash
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        entry["hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        self._chain.append(entry)
        with open(self._path, "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry["hash"]

    def verify(self) -> bool:
        prev = "0" * 64
        for entry in self._chain:
            if entry["prev_hash"] != prev:
                return False
            stored = entry.pop("hash")
            canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
            computed = hashlib.sha256(canonical.encode()).hexdigest()
            entry["hash"] = stored
            if computed != stored:
                return False
            prev = stored
        return True


class LedgerBudgetStore:
    """Reconstructs budget/rate-limit state from the append-only ledger chain.

    This solves the restart-reset vulnerability: instead of holding ephemeral
    counters in memory, we replay the ledger chain at boot to reconstruct
    spent amounts and call counts per actor.

    Properties:
    - Same inputs -> same verdict (deterministic)
    - No new trusted state (ledger is the single source of truth)
    - O(n) replay at boot, O(1) per decision
    - Zero new dependencies (stdlib only)
    """

    def __init__(self, ledger: Ledger):
        self._ledger = ledger
        self._spend: dict[str, float] = {}
        self._calls: dict[str, int] = {}
        self._window_start: dict[str, float] = {}
        self._rebuild()

    def _rebuild(self):
        """Replay the chain to reconstruct spent/calls per actor."""
        for entry in self._ledger.chain():
            actor = entry.get("actor", "unknown")
            if entry.get("verdict") == "approved":
                amount = entry.get("amount", 0)
                self._spend[actor] = self._spend.get(actor, 0) + amount
                self._calls[actor] = self._calls.get(actor, 0) + 1
                ts = entry.get("timestamp")
                if ts and actor not in self._window_start:
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        self._window_start[actor] = dt.timestamp()
                    except (ValueError, TypeError):
                        self._window_start[actor] = time.monotonic()

    def get_spent(self, actor: str) -> float:
        return self._spend.get(actor, 0)

    def get_calls(self, actor: str) -> int:
        return self._calls.get(actor, 0)

    def get_window_start(self, actor: str) -> float:
        return self._window_start.get(actor, time.monotonic())

    def record_spend(self, actor: str, amount: float):
        self._spend[actor] = self._spend.get(actor, 0) + amount
        self._calls[actor] = self._calls.get(actor, 0) + 1
        if actor not in self._window_start:
            self._window_start[actor] = time.monotonic()
