"""Tamper-evident audit ledger for every policy decision.

Each entry carries the SHA-256 digest of the previous entry, chaining the
whole history. Altering, reordering, or removing any entry breaks the chain
and can be detected with a single linear scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


class LedgerIntegrityError(Exception):
    pass


@dataclass(frozen=True)
class LedgerEntry:
    index: int
    prev_hash: str
    payload: str
    entry_hash: str
    recorded_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "prev_hash": self.prev_hash,
            "payload": self.payload,
            "entry_hash": self.entry_hash,
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LedgerEntry":
        return cls(
            index=int(data["index"]),
            prev_hash=str(data["prev_hash"]),
            payload=str(data["payload"]),
            entry_hash=str(data["entry_hash"]),
            recorded_at=str(data["recorded_at"]),
        )


def _hash(prev_hash: str, index: int, payload: str) -> str:
    body = f"{prev_hash}|{index}|{payload}".encode("utf-8")
    return sha256(body).hexdigest()


def _entry(index: int, prev_hash: str, payload: str) -> LedgerEntry:
    return LedgerEntry(
        index=index,
        prev_hash=prev_hash,
        payload=payload,
        entry_hash=_hash(prev_hash, index, payload),
        recorded_at=datetime.now(timezone.utc).isoformat(),
    )


def verify_chain(entries: list[LedgerEntry]) -> bool:
    """Returns True only if the whole chain is intact."""
    if not entries:
        return True
    if entries[0].index != 0:
        return False
    if entries[0].prev_hash != "0" * 64:
        return False
    for entry in entries:
        expected = _hash(entry.prev_hash, entry.index, entry.payload)
        if entry.entry_hash != expected:
            return False
    for prev, cur in zip(entries, entries[1:]):
        if cur.index != prev.index + 1:
            return False
        if cur.prev_hash != prev.entry_hash:
            return False
    return True


class Ledger:
    """Append-only, verifiable record of policy decisions."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else None
        self._entries: list[LedgerEntry] = []
        self._loaded = False
        if self.path and self.path.is_file():
            self._load()

    def _load(self) -> None:
        import json

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._entries = [LedgerEntry.from_dict(e) for e in raw.get("entries", [])]
        self._loaded = True
        if not verify_chain(self._entries):
            raise LedgerIntegrityError("ledger failed integrity verification")

    @property
    def entries(self) -> list[LedgerEntry]:
        return list(self._entries)

    @property
    def head_hash(self) -> str:
        if not self._entries:
            return "0" * 64
        return self._entries[-1].entry_hash

    def append(self, payload: str) -> LedgerEntry:
        index = len(self._entries)
        entry = _entry(index, self.head_hash, payload)
        self._entries.append(entry)
        if self.path is not None:
            self._flush()
        return entry

    def append_json(self, payload: Any) -> LedgerEntry:
        import json

        return self.append(json.dumps(payload, sort_keys=True, default=str))

    def _flush(self) -> None:
        import json

        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema": "mandateguard/ledger/v1", "entries": [e.to_dict() for e in self._entries]}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def verify(self) -> bool:
        return verify_chain(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
