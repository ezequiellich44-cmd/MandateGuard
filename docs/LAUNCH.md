# MandateGuard — Launch Kit

## One-liner

**MandateGuard is the pre-action payment policy layer for AI agents: deterministic,
auditable, MCP-ready, and drained-agent-proof.**

## The pitch (60-second)

Every day, autonomous agents with wallets get drained. In January 2026 a single
attack took $45M. OWASP calls it **LLM08 — Excessive Agency**, one of the top
LLM app risks. The industry is converging on *mandates* — signed authorizations
like Google's AP2, Coinbase's x402, ERC-8004 — but nobody ships the
**enforcement**: a deterministic engine that blocks a bad call *before* the
tool runs. That's MandateGuard.

It evaluates every money-moving tool call against budgets, allowlists, rate
limits, and signed mandates with **no LLM in the decision path**. Same inputs,
same verdict, always — replayable by auditors from a tamper-evident SHA-256
ledger. It mounts as an MCP server in minutes. MIT core, Pro license for
operations features.

## Target buyers

1. **Startups shipping agents that move money** (payments, refunds, trading,
   subscriptions). First revenue: Pro at $149/mo.
2. **Platforms / agent builders** (MCP marketplaces, agent SDKs) embedding
   guardrails. Volume / Enterprise.
3. **Compliance & security teams** needing audit trails for agentic commerce.
   Audit notary (Enterprise).

## Proof points

- $45M+ documented agent-caused losses (SoK on agentic commerce, 2026).
- Gartner: 40% of enterprise apps embed agents by end of 2026.
- OWASP LLM08 Excessive Agency in top-10 LLM risks.
- Google AP2 / Coinbase x402 / ERC-8004: mandates are the standard; enforcement is the gap.

## Demo script (2 minutes)

1. `git clone https://github.com/ezequiellich44-cmd/MandateGuard && cd MandateGuard && pip install -e ".[mcp]"`
2. Set a scope: agent may `pay` to `0xGOOD`, max $100/call, 5 calls/window.
3. `authorize(pay, 0xGOOD, $80)` → **APPROVED**, ledger entry.
4. `authorize(pay, 0xSCAM, $50)` → **DENIED**, ledger entry.
5. `authorize(pay, 0xGOOD, $80)` again → **DENIED** (budget).
6. `ledger.verify()` → True. Sign a mandate, revoke its nonce, watch it fail.
7. Activate Pro license → revocation/persistence unlock.

## Payment & wallets (USDT — Phantom)

All Pro/Enterprise payments land in USDT. Pipeline is fully automated:

| Chain | Wallet | Token |
| ----- | ------ | ----- |
| Solana | `3fZSMAyCEMhZwWiynbJDjoYNUT97aiV9BLzoUNroEMAz` | USDT-SPL |
| Ethereum | `0x4Ed4D0750453C027FA8398067d5af980Bcc9B6eD` | USDT-ERC20 |

Order → verify → license in one flow:

```bash
python tools/sell.py order --customer Acme --plan pro --seats 5 --months 12
# customer sends USDT, shares tx hash
python tools/sell.py satisfy --order MG-0001 --key <priv> \
    --chain solana --expected-usdt 149 --tx-hash <tx>
```

Landing page already shows the wallets in the **Buy** section and the on-chain
verification is implemented (`tools/verify_payment.py` — Solana RPC + Etherscan).

## Content assets

- **Landing page**: https://ezequiellich44-cmd.github.io/MandateGuard
  (LIVE, Buy page with wallets: https://ezequiellich44-cmd.github.io/MandateGuard/buy.html).
- **Repo**: https://github.com/ezequiellich44-cmd/MandateGuard
- **Release**: v1.1.0 with wheel + sdist + `.mcpb` bundle (assets attached).
- **MCP Registry**: `io.github.ezequiellich44-cmd/mandateguard` (v1.0.0, active).
- **Blog post (SEO)**: https://ezequiellich44-cmd.github.io/MandateGuard/blog/why-agents-shouldnt-authorize-payments.html
- **Screenshot hook**: the `examples/basic_agent_eval.py` terminal output
  (APPROVED/DENIED rows + "ledger verified: True").

## Launch checklist

- [x] Landing page live with Buy page + USDT wallets.
- [x] On-chain payment verification (`tools/verify_payment.py`).
- [x] Order → payment → license pipeline (`tools/sell.py order/satisfy`).
- [x] Auto payment monitor (`tools/monitor_payments.py`).
- [x] Published on official MCP Registry (v1.0.0 active, mcpb bundle).
- [x] Sales runbook (`docs/OPS.md`) — pipeline verified end-to-end.
- [ ] Publish PyPI (**needs Trusted Publisher setup from user**, 30s).
- [ ] GitHub Sponsors profile active (FUNDING.yml points to it).
- [ ] Post to: HN "Show HN", r/LocalLLaMA, r/artificial, Product Hunt.
- [ ] Publish MCP server on 2+ marketplaces (PulseMCP, skills.sh, mcpmarket).
- [ ] 5 founding Pro licenses at 50% off for testimonials.
- [ ] Tweet thread with the drain stats + demo gif.

## Suggested posts

### HN "Show HN: MandateGuard — deterministic payment policy for AI agents"
"We built the enforcement layer the agent-payment standards forgot. $45M+ has
been drained from agents this year (SoK on agentic commerce). Google AP2,
Coinbase x402, ERC-8004 define signed mandates — but nothing stops the agent
from exceeding them at runtime. MandateGuard evaluates every tool call against
budgets/allowlists/rate limits/mandates with NO LLM in the decision path, so
every verdict is replay-verifiable from a tamper-evident ledger. Ships as an
MCP server. MIT core, Pro license. Feedback welcome."

### Email template — cold outreach to agent platforms
Subject: MandateGuard — enforcement for agent payments (MCP-ready)

"Hi {name}, I saw {company} builds {product}. As agents get wallets, teams are
realizing the OWASP LLM08 (excessive agency) problem is a wallet problem: a
single prompt injection can drain funds. We built MandateGuard — a
deterministic, auditable pre-action policy layer that gates every money-moving
tool call before it runs (no LLM in the path, so it's verifiable). It's
MCP-ready and MIT core. Would you be open to a 15-min call to see if it fits
{product}? Happy to share the demo and threat model."