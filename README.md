<!-- mcp-name: io.github.ezequiellich44-cmd/mandateguard -->

# MandateGuard

[![CI](https://github.com/ezequiellich44-cmd/MandateGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/ezequiellich44-cmd/MandateGuard/actions)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-active-22d3ee)](https://registry.modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-34d399.svg)](https://opensource.org/licenses/MIT)

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
# from this repo (works today; also on the official MCP Registry)
git clone https://github.com/ezequiellich44-cmd/MandateGuard.git
cd MandateGuard
python -m pip install -e .

# or directly from the source:
python -m pip install "git+https://github.com/ezequiellich44-cmd/MandateGuard.git"
```

> Note: `mandateguard` on PyPI is pending Trusted Publisher setup; until then
> the repo URL is the canonical install path. The MCP bundle is live on the
> official MCP Registry (`io.github.ezequiellich44-cmd/mandateguard`), so
> MCP-aware clients can install it without any Python step.

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

The package ships an installable MCP server entrypoint:

```bash
python -m pip install -e ".[mcp]"
mandateguard-mcp            # stdio server, ready for Claude/Cursor/harness
```

For Claude Code:

```bash
claude mcp add mandateguard -- mandateguard-mcp
```

MandateGuard is **published on the official MCP Registry**:
`io.github.ezequiellich44-cmd/mandateguard` (version 1.0.0, `mcpb` bundle,
active). MCP-aware clients that sync the registry can discover and install it
directly. The bundle ships the same stdio server and 14-tool surface.

Exposed tools: `set_scope`, `set_global_policy`, `authorize`, `init_ledger`,
`ledger_status`, `create_mandate_signer`, `issue_mandate`, `check_mandate`,
`activate_license`, `license_status`, `reset_state`, plus Pro-gated
`revoke_mandate` and `persist_state` behind a signed Pro license (USDT
purchase — see the [Buy section](https://ezequiellich44-cmd.github.io/MandateGuard)).

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
state model, [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for what this does
and does not protect against, and [docs/LAUNCH.md](docs/LAUNCH.md) for the
commercial pitch and go-to-market kit.

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

## Buying MandateGuard Pro

Fully automated, self-service:

1. Open [buy.html](https://ezequiellich44-cmd.github.io/MandateGuard/buy.html), pick a plan (Pro monthly **99 USDT launch price** (was 149) / annual 1,430 USDT) and chain (Solana or Ethereum).
2. Send the exact USDT amount to the displayed address (QR provided).
3. Click **I've Paid** — a pre-filled GitHub issue opens; paste your transaction hash and submit.
4. A bot verifies your payment on-chain and replies with your signed Ed25519 license within minutes. No humans in the loop.

Free 14-day Pro trial: open a [trial issue](https://github.com/ezequiellich44-cmd/MandateGuard/issues/new?template=trial-request.md&title=%5BTRIAL%5D%20Trial%20request) and the bot delivers a license automatically.

Enterprise / custom terms: ezequiellich44@gmail.com

## License

MIT core. Pro features require a signed license — see [Buying MandateGuard Pro](#buying-mandateguard-pro).

## Security Model

**Fail-closed:** If the policy engine is unreachable or errors, payment calls are denied. No silent failures.

**Key storage:** Signing keys loaded from environment variables or file, never hardcoded. Recommended: use OS keychain or vault for production.

**Policy mutation:** Policy files are read-only at startup. Hot-reload requires signed policy update (Ed25519). Rollback: keep previous policy hash, revert to last known-good.

**Recovery:** If authorization fails, the agent receives a denial with reason. The agent can retry with different parameters or escalate to human approval.