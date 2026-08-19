"""Command-line interface for MandateGuard.

Operational tooling: policy CRUD, authorize, mandates, ledger health,
and (vendor-side) license issuance.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from mandateguard.engine import PolicyEngine
from mandateguard.ledger.chain import Ledger, LedgerIntegrityError
from mandateguard.licensing import (
    InvalidLicense,
    License,
    LicenseIssuer,
    generate_private_key_hex,
    verify_license,
)
from mandateguard.mandate import Mandate, MandateSigner, now_iso
from mandateguard.model import Intent, Policy, Scope
from mandateguard.revoke import RevocationRegistry
from mandateguard.store import EngineStateStore, PolicyStore


def _policy(args) -> Policy:
    return PolicyStore(args.state_dir / "policy.json").load()


def _engine(args) -> tuple[PolicyEngine, EngineStateStore]:
    policy = _policy(args)
    engine = PolicyEngine(policy)
    store = EngineStateStore(args.state_dir / "state.json")
    store.load_into(engine)
    return engine, store


def _save(args, engine: PolicyEngine) -> None:
    EngineStateStore(args.state_dir / "state.json").save_from(engine)


def _ledger(args) -> Ledger:
    return Ledger(args.state_dir / "ledger.json")


def cmd_show(args) -> None:
    policy = _policy(args)
    print(json.dumps(policy.to_dict(), indent=2))
    print("\nengine state:")
    for actor in policy.scopes:
        engine, _ = _engine(args)
        print(f"  {actor}: {engine.state(actor)}")


def cmd_set_scope(args) -> None:
    store = PolicyStore(args.state_dir / "policy.json")
    policy = store.load()
    policy.scopes[args.actor] = Scope(
        tools=tuple(args.tools),
        destinations=tuple(args.destinations or ()),
        max_amount=args.max_amount,
        currency=args.currency,
        max_calls_per_window=args.max_calls,
        window_seconds=args.window,
    )
    store.save(policy)
    print(f"scope set for {args.actor}")


def cmd_set_global(args) -> None:
    store = PolicyStore(args.state_dir / "policy.json")
    policy = store.load()
    if args.global_max is not None:
        policy.global_max_amount = args.global_max
    if args.allowlist is not None:
        policy.allowlist = tuple(args.allowlist)
    if args.denylist is not None:
        policy.denylist = tuple(args.denylist)
    if args.require_mandate is not None:
        policy.require_mandate = args.require_mandate
    store.save(policy)
    print("global policy updated")


def cmd_authorize(args) -> None:
    engine, store = _engine(args)
    mandate_ok = True
    if _policy(args).require_mandate:
        reg = RevocationRegistry(args.state_dir / "revoked.json")
        mandate_ok = not (args.mandate and reg.is_revoked(args.mandate))
    decision = engine.authorize(
        Intent(tool=args.tool, destination=args.destination, amount=args.amount,
               currency=args.currency, actor=args.actor),
        mandate_ok=mandate_ok,
    )
    _save(args, engine)
    ledger = _ledger(args)
    ledger.append_json(decision.to_dict())
    print(json.dumps(decision.to_dict(), indent=2))
    sys.exit(0 if decision.approved else 1)


def cmd_mandate_issue(args) -> None:
    signer = MandateSigner()
    mandate = Mandate(
        actor=args.actor,
        max_amount=args.max_amount,
        currency=args.currency,
        tools=tuple(args.tools),
        destinations=tuple(args.destinations or ()),
        not_before=now_iso(),
        not_after=args.not_after,
        nonce=args.nonce or uuid.uuid4().hex[:16],
        issuer=signer.public_key_bytes.hex(),
    )
    print(json.dumps({"mandate": mandate.to_dict(), "signature": signer.sign(mandate)}, indent=2))


def cmd_mandate_verify(args) -> None:
    from mandateguard.mandate import verify_mandate

    data = json.loads(args.mandate)
    mandate = Mandate(
        actor=data["actor"], max_amount=data["max_amount"], currency=data["currency"],
        tools=tuple(data["tools"]), destinations=tuple(data["destinations"]),
        not_before=data["not_before"], not_after=data["not_after"],
        nonce=data["nonce"], issuer=data["issuer"],
    )
    reg = RevocationRegistry(args.state_dir / "revoked.json")
    valid = verify_mandate(bytes.fromhex(args.public_key), mandate, args.signature)
    if reg.is_revoked(mandate.nonce):
        valid = False
        print("revoked")
    print("valid" if valid else "invalid")
    sys.exit(0 if valid else 1)


def cmd_mandate_revoke(args) -> None:
    reg = RevocationRegistry(args.state_dir / "revoked.json")
    reg.revoke(args.nonce)
    print(f"revoked {args.nonce}")


def cmd_ledger_verify(args) -> None:
    try:
        ledger = _ledger(args)
        ok = ledger.verify()
    except LedgerIntegrityError as exc:
        print(f"INTEGRITY ERROR: {exc}")
        sys.exit(2)
    print(f"verified={ok} entries={len(ledger)} head={ledger.head_hash[:16]}...")
    sys.exit(0 if ok else 1)


def cmd_license_genkey(args) -> None:
    key = generate_private_key_hex()
    print(f"LICENSE_PRIVATE_KEY={key}")
    print(f"LICENSE_PUBLIC_KEY={LicenseIssuer(bytes.fromhex(key)).public_key_bytes.hex()}")


def cmd_license_issue(args) -> None:
    key_hex = args.private_key
    features = args.features or []
    if args.plan in _plan_features():
        features = _plan_features()[args.plan]
    issuer = LicenseIssuer(bytes.fromhex(key_hex))
    lic = License(customer=args.customer, plan=args.plan, seats=args.seats,
                  not_after=args.not_after, features=features)
    print(issuer.issue(lic))


def _plan_features() -> dict:
    from mandateguard.licensing import PLANS
    return {name: p["features"] for name, p in PLANS.items()}


def cmd_license_verify(args) -> None:
    lic = verify_license(bytes.fromhex(args.public_key), args.license)
    print(json.dumps(lic.to_payload(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mandateguard", description="Deterministic payment policy for AI agents")
    parser.add_argument("--state-dir", type=Path, default=Path(".mandateguard"), help="state directory (default: .mandateguard)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("show", help="show policy and state")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("set-scope", help="configure an actor scope")
    p.add_argument("--actor", required=True)
    p.add_argument("--tools", nargs="+", required=True)
    p.add_argument("--destinations", nargs="+", default=())
    p.add_argument("--max-amount", type=int, default=0)
    p.add_argument("--currency", default="usd")
    p.add_argument("--max-calls", type=int, default=0)
    p.add_argument("--window", type=int, default=3600)
    p.set_defaults(fn=cmd_set_scope)

    p = sub.add_parser("set-global", help="configure global guards")
    p.add_argument("--global-max", type=int, default=None)
    p.add_argument("--allowlist", nargs="+", default=None)
    p.add_argument("--denylist", nargs="+", default=None)
    p.add_argument("--require-mandate", type=lambda v: v.lower() == "true", default=None)
    p.set_defaults(fn=cmd_set_global)

    p = sub.add_parser("authorize", help="evaluate a tool call")
    p.add_argument("--tool", required=True)
    p.add_argument("--destination", required=True)
    p.add_argument("--amount", type=int, default=0)
    p.add_argument("--currency", default="usd")
    p.add_argument("--actor", default="agent")
    p.add_argument("--mandate", default=None, help="mandate nonce (if require_mandate)")
    p.set_defaults(fn=cmd_authorize)

    p = sub.add_parser("mandate-issue", help="issue a signed mandate")
    p.add_argument("--actor", required=True)
    p.add_argument("--max-amount", type=int, required=True)
    p.add_argument("--currency", default="usd")
    p.add_argument("--tools", nargs="+", required=True)
    p.add_argument("--destinations", nargs="+", default=())
    p.add_argument("--not-after", required=True, help="ISO8601 expiry")
    p.add_argument("--nonce", default=None)
    p.set_defaults(fn=cmd_mandate_issue)

    p = sub.add_parser("mandate-verify", help="verify a mandate signature")
    p.add_argument("--public-key", required=True, help="issuer public key (hex)")
    p.add_argument("--signature", required=True, help="signature (hex)")
    p.add_argument("--mandate", required=True, help="mandate JSON")
    p.set_defaults(fn=cmd_mandate_verify)

    p = sub.add_parser("mandate-revoke", help="revoke a mandate nonce")
    p.add_argument("--nonce", required=True)
    p.set_defaults(fn=cmd_mandate_revoke)

    p = sub.add_parser("ledger-verify", help="verify ledger integrity")
    p.set_defaults(fn=cmd_ledger_verify)

    p = sub.add_parser("license-genkey", help="generate vendor signing keys")
    p.set_defaults(fn=cmd_license_genkey)

    p = sub.add_parser("license-issue", help="issue a Pro/Enterprise license")
    p.add_argument("--private-key", required=True)
    p.add_argument("--customer", required=True)
    p.add_argument("--plan", required=True, choices=["pro", "enterprise"])
    p.add_argument("--seats", type=int, default=1)
    p.add_argument("--not-after", required=True)
    p.add_argument("--features", nargs="+", default=None)
    p.set_defaults(fn=cmd_license_issue)

    p = sub.add_parser("license-verify", help="verify a license")
    p.add_argument("--public-key", required=True)
    p.add_argument("--license", required=True, help="license b64")
    p.set_defaults(fn=cmd_license_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.fn(args)
    except LedgerIntegrityError as exc:
        print(f"LEDGER INTEGRITY ERROR: {exc}", file=sys.stderr)
        return 2
    except InvalidLicense as exc:
        print(f"INVALID LICENSE: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
