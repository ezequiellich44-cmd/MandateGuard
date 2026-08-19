import json

import pytest

from mandateguard.ledger.chain import (
    Ledger,
    LedgerEntry,
    LedgerIntegrityError,
    verify_chain,
)


def test_empty_chain_verifies():
    assert verify_chain([])
    assert Ledger().verify()


def test_append_and_verify():
    ledger = Ledger()
    for payload in ("a", "b", "c"):
        ledger.append(payload)
    assert len(ledger) == 3
    assert ledger.verify()
    assert ledger.head_hash == ledger.entries[-1].entry_hash


def test_entries_are_chained():
    ledger = Ledger()
    ledger.append("a")
    ledger.append("b")
    a, b = ledger.entries
    assert b.prev_hash == a.entry_hash
    assert b.index == a.index + 1


def test_tamper_detected():
    ledger = Ledger()
    ledger.append("a")
    ledger.append("b")
    tampered = list(ledger.entries)
    tampered[0] = LedgerEntry(
        index=0,
        prev_hash="0" * 64,
        payload="EVIL",
        entry_hash="0" * 64,
        recorded_at="x",
    )
    assert not verify_chain(tampered)


def test_reorder_detected():
    ledger = Ledger()
    ledger.append("a")
    ledger.append("b")
    first, second = ledger.entries
    assert not verify_chain([second, first])


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path)
    ledger.append(json.dumps({"event": "authorize", "status": "approved"}))
    ledger.append("second")

    loaded = Ledger(path)
    assert len(loaded) == 2
    assert loaded.verify()
    assert loaded.head_hash == ledger.head_hash


def test_tampered_file_detected(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path)
    ledger.append("a")
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["entries"][0]["payload"] = "EVIL"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(LedgerIntegrityError):
        Ledger(path)
