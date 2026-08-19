"""MCP server exposing MandateGuard as a guardrail any agent can mount.

This is the primary distribution channel: an agent (Claude, Cursor, custom
harness) adds this MCP server and every payment/tool call is gated by the
deterministic engine *before* execution. Tools here are intentionally
callable by the agent itself so the whole envelope is self-guarding.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastmcp import FastMCP

from mandateguard.engine import PolicyEngine
from mandateguard.ledger.chain import Ledger, LedgerIntegrityError
from mandateguard.mandate import Mandate, MandateSigner, verify_mandate
from mandateguard.model import Decision, Intent, Policy, Scope

log = logging.getLogger("mandateguard.mcp")

mcp = FastMCP("mandateguard")

_policy = Policy()
_engine = PolicyEngine(_policy)
_ledger: Ledger | None = None
_signer: MandateSigner | None = None
_signer_pubkey: bytes | None = None


def _record(intent: Intent, decision: Decision) -> None:
    if _ledger is None:
        return
    _ledger.append_json(
        {
            "event": "authorize",
            "decision": decision.status.value,
            "actor": intent.actor,
            "tool": intent.tool,
            "destination": intent.destination,
            "amount": intent.amount,
            "currency": intent.currency,
            "results": [r.__dict__ for r in decision.results],
        }
    )


@mcp.tool
def set_scope(
    actor: str,
    tools: list[str],
    destinations: list[str] | None = None,
    max_amount: int = 0,
    currency: str = "usd",
    max_calls_per_window: int = 0,
    window_seconds: int = 3600,
) -> dict[str, Any]:
    """Define what an actor is allowed to do. Replaces any prior scope for the actor."""
    scope = Scope(
        tools=tuple(tools),
        destinations=tuple(destinations or ()),
        max_amount=max_amount,
        currency=currency,
        max_calls_per_window=max_calls_per_window,
        window_seconds=window_seconds,
    )
    _policy.scopes[actor] = scope
    if _ledger is not None:
        _ledger.append_json({"event": "set_scope", "actor": actor, "scope": scope.__dict__})
    return {"ok": True, "actor": actor, "scope": scope.__dict__}


@mcp.tool
def set_global_policy(
    global_max_amount: int = 0,
    allowlist: list[str] | None = None,
    denylist: list[str] | None = None,
    require_mandate: bool = False,
) -> dict[str, Any]:
    """Configure global guards applied to every actor."""
    _policy.global_max_amount = global_max_amount
    _policy.allowlist = tuple(allowlist or ())
    _policy.denylist = tuple(denylist or ())
    _policy.require_mandate = require_mandate
    return {
        "ok": True,
        "global_max_amount": global_max_amount,
        "allowlist": list(_policy.allowlist),
        "denylist": list(_policy.denylist),
        "require_mandate": require_mandate,
    }


@mcp.tool
def authorize(
    tool: str,
    destination: str,
    amount: int = 0,
    currency: str = "usd",
    actor: str = "agent",
) -> dict[str, Any]:
    """Evaluate a tool call against policy. This is the ONLY gate an agent must pass before executing a paid action."""
    intent = Intent(tool=tool, destination=destination, amount=amount, currency=currency, actor=actor)
    mandate_ok = _satisfies_mandate(intent, actor)
    decision = _engine.authorize(intent, mandate_ok=mandate_ok)
    _record(intent, decision)
    return decision.to_dict()


def _satisfies_mandate(intent: Intent, actor: str) -> bool:
    if _signer_pubkey is None:
        return True
    # a real deployment would resolve the stored mandate per actor here
    return True


@mcp.tool
def init_ledger(path: str | None = None) -> dict[str, Any]:
    """Initialize (or load) the tamper-evident audit ledger."""
    global _ledger
    try:
        _ledger = Ledger(path) if path else Ledger()
    except LedgerIntegrityError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "entries": len(_ledger), "head_hash": _ledger.head_hash}


@mcp.tool
def ledger_status() -> dict[str, Any]:
    """Report ledger integrity and head hash."""
    if _ledger is None:
        return {"ok": False, "error": "ledger not initialized"}
    return {
        "ok": True,
        "verified": _ledger.verify(),
        "entries": len(_ledger),
        "head_hash": _ledger.head_hash,
    }


@mcp.tool
def create_mandate_signer() -> dict[str, Any]:
    """Generate a fresh Ed25519 keypair for issuing agent mandates."""
    global _signer, _signer_pubkey
    _signer = MandateSigner()
    _signer_pubkey = _signer.public_key_bytes
    return {"ok": True, "public_key": _signer_pubkey.hex()}


@mcp.tool
def issue_mandate(
    actor: str,
    max_amount: int,
    not_after: str,
    tools: list[str],
    destinations: list[str] | None = None,
    currency: str = "usd",
    nonce: str = "auto",
) -> dict[str, Any]:
    """Issue a signed, time-boxed mandate for an actor."""
    if _signer is None:
        return {"ok": False, "error": "no signer; call create_mandate_signer first"}
    import uuid
    from mandateguard.mandate import now_iso

    mandate = Mandate(
        actor=actor,
        max_amount=max_amount,
        currency=currency,
        tools=tuple(tools),
        destinations=tuple(destinations or ()),
        not_before=now_iso(),
        not_after=not_after,
        nonce=nonce if nonce != "auto" else uuid.uuid4().hex[:16],
        issuer=_signer_pubkey.hex(),
    )
    signature = _signer.sign(mandate)
    return {"ok": True, "mandate": mandate.to_dict(), "signature": signature}


@mcp.tool
def check_mandate(public_key_hex: str, mandate_json: str, signature_hex: str) -> dict[str, Any]:
    """Verify a mandate's signature and validity window."""
    import json as _json

    data = _json.loads(mandate_json)
    mandate = Mandate(
        actor=data["actor"],
        max_amount=data["max_amount"],
        currency=data["currency"],
        tools=tuple(data["tools"]),
        destinations=tuple(data["destinations"]),
        not_before=data["not_before"],
        not_after=data["not_after"],
        nonce=data["nonce"],
        issuer=data["issuer"],
    )
    valid = verify_mandate(bytes.fromhex(public_key_hex), mandate, signature_hex)
    return {"ok": valid, "expired": mandate.is_expired()}


@mcp.tool
def reset_state() -> dict[str, Any]:
    """Reset spend/rate counters (for demos and tests)."""
    global _engine
    _engine = PolicyEngine(_policy)
    return {"ok": True}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
