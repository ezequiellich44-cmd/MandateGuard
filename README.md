# MandateGuard

**Deterministic, auditable payment policy for autonomous AI agents.**

MandateGuard is a pre-action enforcement layer that sits between an agent and
its tools/wallet. Every tool call that moves money is evaluated by a *pure,
deterministic engine* — budgets, allowlists, denylists, rate limits, and
signed mandates — before anything executes. **No LLM is ever in the decision
path**, which is exactly what makes every verdict reproducible and every
ledger entry verifiable.

It ships with an MCP server so any agent (Claude, Cursor, or your own
harness) can mount it as a guardrail in minutes.

---

## Why

The 2026 agentic-economy reality:

- **OWASP LLM08 — Excessive Agency** is one of the top LLM app risks. Agents
  given wallets are getting drained: the SoK on agentic commerce documents
  **$40M+ in real losses** (drain attacks, memory poisoning, tool abuse).
- Payment standards (Google **AP2**'s Intent/Cart/Payment mandates, Coinbase
  **x402**, ERC-8004) define *what* a mandate is — but none of them ship the
  *enforcement* layer that actually blocks an agent mid-flight.
- Gartner: **40% of enterprise apps** will embed agents by end of 2026.
  Those agents will move money. They need rails.

The market gap: a **deterministic** (non-LLM) policy engine + audit trail +
MCP distribution. That is this repo.

## Features

- **Deterministic engine** — same inputs, same verdict, always. Auditable by
  replay, no model sampling in the decision.
- **Per-actor scopes** — allowed tools, allowed destinations, per-call max,
  currency, per-window call limits.
- **Global guards** — total budget caps, destination allowlist/denylist.
- **Signed mandates** (Ed25519) — short-lived, nonce-bound, issuer-signed
  authorizations in the AP2 / x402 style. An agent cannot widen its own scope.
- **Tamper-evident ledger** — every decision is append-only and SHA-256
  chained. Any edit, reorder, or deletion is detected by a linear scan.
- **MCP server** — mount as a guardrail; tools for policy, authorize, mandate
  issuance, and ledger health.
- **Zero deps in the decision path** — `cryptography` only for mandates;
  the core rules run on the stdlib alone.

## Install

```bash
pip install mandateguard
# with MCP server:
pip install "mandateguard[mcp]"
```

## Quickstart

```python
from mandateguard import Intent, Policy, PolicyEngine, Scope

policy = Policy(
    scopes={
        "wallet-agent": Scope(
            tools=("pay",),
            destinations=("0xGOOD",),
            max_amount=1000,          # per call
            currency="usd",
            max_calls_per_window=5,
        )
    },
    global_max_amount=2000,           # per actor
    allowlist=("0xGOOD",),
    denylist=("0xSCAM",),
)
engine = PolicyEngine(policy)

decision = engine.authorize(
    Intent(tool="pay", destination="0xGOOD", amount=800, actor="wallet-agent")
)
print(decision.status)   # DecisionStatus.APPROVED
```

Denied calls are blocked with structured reasons; state (spend/rate) commits
only on approval, so replays are deterministic.

### MCP server

```bash
python -m mandateguard.mcp.server
```

Exposed tools: `set_scope`, `set_global_policy`, `authorize`, `init_ledger`,
`ledger_status`, `create_mandate_signer`, `issue_mandate`, `check_mandate`,
`reset_state`.

### Mandates

```python
from mandateguard import Mandate, MandateSigner, verify_mandate

issuer = MandateSigner()
m = Mandate(actor="wallet-agent", max_amount=500, currency="usd",
            tools=("pay",), destinations=("0xGOOD",),
            not_before="2026-01-01T00:00:00+00:00",
            not_after="2099-01-01T00:00:00+00:00", nonce="abc", issuer="you")
sig = issuer.sign(m)
verify_mandate(issuer.public_key_bytes, m, sig)   # True
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the decision flow and
state model, and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for what this
does and does not protect against.

```
Agent intent ──> authorize(intent) ──> PolicyEngine
                                          │  scope? allowlist? denylist?
                                          │  budget? rate limit? mandate?
                                          ▼
                                     APPROVED / DENIED / REQUIRES_APPROVAL
                                          │
                                          ▼
                              append-only SHA-256 ledger (audit)
```

## Tests

```bash
python -m pytest -q
```

## License

MIT. See [LICENSE](LICENSE).
