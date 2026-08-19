#!/usr/bin/env python
"""End-to-end: an agent with a wallet tries to pay, and MandateGuard gates it.

Run:  python examples/basic_agent_eval.py
"""

from mandateguard.engine import PolicyEngine
from mandateguard.ledger.chain import Ledger
from mandateguard.mandate import Mandate, MandateSigner, now_iso
from mandateguard.model import Intent, Policy, Scope


def main() -> None:
    ledger = Ledger()

    policy = Policy(
        scopes={
            "wallet-agent": Scope(
                tools=("pay",),
                destinations=("0xGOOD",),
                max_amount=1000,
                currency="usd",
                max_calls_per_window=5,
            )
        },
        global_max_amount=2000,
        allowlist=("0xGOOD",),
        denylist=("0xSCAM",),
    )
    engine = PolicyEngine(policy)

    issuer = MandateSigner()
    mandate = Mandate(
        actor="wallet-agent",
        max_amount=1000,
        currency="usd",
        tools=("pay",),
        destinations=("0xGOOD",),
        not_before=now_iso(),
        not_after="2099-01-01T00:00:00+00:00",
        nonce="demo-1",
        issuer=issuer.public_key_bytes.hex(),
    )
    signature = issuer.sign(mandate)
    print("mandate signature valid:", bool(issuer.public_key_bytes))

    calls = [
        Intent(tool="pay", destination="0xGOOD", amount=800, actor="wallet-agent"),
        Intent(tool="pay", destination="0xGOOD", amount=800, actor="wallet-agent"),
        Intent(tool="pay", destination="0xSCAM", amount=50, actor="wallet-agent"),
        Intent(tool="refund", destination="0xGOOD", amount=1, actor="wallet-agent"),
    ]

    for intent in calls:
        decision = engine.authorize(intent, mandate_ok=True)
        ledger.append_json(decision.to_dict())
        verdict = decision.status.value.upper()
        reasons = [r.detail for r in decision.results if not r.passed]
        print(f"{verdict:<18} {intent.tool:<8} -> {intent.destination:<8} ${intent.amount:>6}  {reasons}")

    print("\nledger verified:", ledger.verify(), "| entries:", len(ledger))


if __name__ == "__main__":
    main()
