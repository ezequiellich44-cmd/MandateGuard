"""MCP server exposing MandateGuard as a guardrail any agent can mount.

This is the primary distribution channel: an agent (Claude, Cursor, custom
harness) adds this MCP server and every payment/tool call is gated by the
deterministic engine *before* execution. Tools here are intentionally
callable by the agent itself so the whole envelope is self-guarding.

Pro features (revocation, persistence, multi-tenant) are gated behind a
signed MandateGuard Pro license.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastmcp import FastMCP

from mandateguard.engine import PolicyEngine
from mandateguard.ledger.chain import Ledger, LedgerIntegrityError
from mandateguard.licensing import InvalidLicense, License, verify_license
from mandateguard.mandate import Mandate, MandateSigner, now_iso, verify_mandate
from mandateguard.model import Decision, Intent, Policy, Scope
from mandateguard.revoke import RevocationRegistry

log = logging.getLogger("mandateguard.mcp")

mcp = FastMCP("mandateguard")

_policy = Policy()
_engine = PolicyEngine(_policy)
_ledger: Ledger | None = None
_signers: dict[str, MandateSigner] = {}
_active_signer: str | None = None
_revoked: RevocationRegistry | None = None
_license: License | None = None


def _require_license() -> License | None:
    if _license is None:
        return None
    return _license


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
def activate_license(public_key_hex: str, license_b64: str) -> dict[str, Any]:
    """Activate a MandateGuard Pro license. Required for Pro features."""
    global _license
    try:
        _license = verify_license(bytes.fromhex(public_key_hex), license_b64)
    except InvalidLicense as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "plan": _license.plan, "customer": _license.customer, "seats": _license.seats}


@mcp.tool
def license_status() -> dict[str, Any]:
    """Report current license state."""
    if _license is None:
        return {"ok": True, "plan": "community", "features": []}
    return {"ok": True, "plan": _license.plan, "customer": _license.customer, "seats": _license.seats}


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
    mandate_nonce: str | None = None,
) -> dict[str, Any]:
    """Evaluate a tool call against policy. This is the ONLY gate an agent must pass before executing a paid action."""
    intent = Intent(tool=tool, destination=destination, amount=amount, currency=currency, actor=actor)
    mandate_ok = True
    if _revoked is not None and mandate_nonce:
        mandate_ok = not _revoked.is_revoked(mandate_nonce)
    decision = _engine.authorize(intent, mandate_ok=mandate_ok)
    _record(intent, decision)
    return decision.to_dict()


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
    signer = MandateSigner()
    pub = signer.public_key_bytes.hex()
    _signers[pub] = signer
    global _active_signer
    _active_signer = pub
    return {"ok": True, "public_key": pub}


@mcp.tool
def issue_mandate(
    actor: str,
    max_amount: int,
    not_after: str,
    tools: list[str],
    destinations: list[str] | None = None,
    currency: str = "usd",
    nonce: str = "auto",
    signer_key: str | None = None,
) -> dict[str, Any]:
    """Issue a signed, time-boxed mandate for an actor."""
    key = signer_key or _active_signer
    if key is None or key not in _signers:
        return {"ok": False, "error": "no signer; call create_mandate_signer first"}
    signer = _signers[key]
    mandate = Mandate(
        actor=actor,
        max_amount=max_amount,
        currency=currency,
        tools=tuple(tools),
        destinations=tuple(destinations or ()),
        not_before=now_iso(),
        not_after=not_after,
        nonce=nonce if nonce != "auto" else uuid.uuid4().hex[:16],
        issuer=key,
    )
    signature = signer.sign(mandate)
    return {"ok": True, "mandate": mandate.to_dict(), "signature": signature}


@mcp.tool
def check_mandate(public_key_hex: str, mandate_json: str, signature_hex: str) -> dict[str, Any]:
    """Verify a mandate's signature and validity window."""
    data = json.loads(mandate_json)
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
def revoke_mandate(nonce: str) -> dict[str, Any]:
    """Revoke a mandate by nonce. Pro feature."""
    lic = _require_license()
    if lic is None:
        return {"ok": False, "error": "no license activated; run activate_license first"}
    if not lic.can("revocation"):
        return {"ok": False, "error": "revocation requires MandateGuard Pro"}
    global _revoked
    if _revoked is None:
        _revoked = RevocationRegistry("revoked.json")
    _revoked.revoke(nonce)
    return {"ok": True, "nonce": nonce}


@mcp.tool
def persist_state(path: str) -> dict[str, Any]:
    """Persist current policy and engine state to JSON. Pro feature."""
    lic = _require_license()
    if lic is None:
        return {"ok": False, "error": "no license activated; run activate_license first"}
    if not lic.can("persistence"):
        return {"ok": False, "error": "persistence requires MandateGuard Pro"}
    from mandateguard.store import EngineStateStore, PolicyStore

    PolicyStore(f"{path}/policy.json").save(_policy)
    EngineStateStore(f"{path}/state.json").save_from(_engine)
    return {"ok": True, "path": path}


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