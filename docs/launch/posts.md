# Launch posts (draft for copy-paste)

All posts point at: https://ezequiellich44-cmd.github.io/MandateGuard (live)
Repo: https://github.com/ezequiellich44-cmd/MandateGuard
MCP Registry: `io.github.ezequiellich44-cmd/mandateguard`

Pricing: MIT core free · Pro 149 USDT/mo · Enterprise custom.
Buy: USDT-SPL `3fZSMAyCEMhZwWiynbJDjoYNUT97aiV9BLzoUNroEMAz` / USDT-ERC20 `0x4Ed4D0750453C027FA8398067d5af980Bcc9B6eD`

---

## Hacker News (Show HN)

Title: Show HN: MandateGuard – deterministic payment guardrail for AI agents that move money

The problem: once you let an agent call `pay()`, an LLM decides whether that call is OK. Same prompt, different verdict. Nobody can point at the exact reason a $40k transfer went out.

MandateGuard fixes that: a pre-action enforcement layer with NO LLM in the decision path.

How it works:
- Every tool call hits `authorize()` before execution
- Budgets, allowlists, rate limits, tool allowlists — all evaluated by a deterministic engine
- Mandates are Ed25519-signed, time-boxed, single-purpose tokens issued offline by you (not by the agent)
- Same inputs → same verdict, always. Deterministic, auditable, reproducible

It also ships a tamper-evident audit ledger (SHA-256 chained, like git for every decision) and a full MCP tool surface so Claude/Cursor/harnesses can wire it in 2 minutes:

```
pip install "mandateguard[mcp]" && mandateguard-mcp
```

Published on the official MCP Registry as `io.github.ezequiellich44-cmd/mandateguard`.

Core is MIT (free). Pro license for revocation + persistence: 149 USDT/mo.

I'd love feedback from anyone running agents that touch money, wallets, or anything irreversible. What's the current state of the art in your setup — agent-level policy files? Rate limit middleware? Pure vibes?

Repo: https://github.com/ezequiellich44-cmd/MandateGuard
Try it in browser: https://ezequiellich44-cmd.github.io/MandateGuard

---

## Reddit r/LocalLLaMA

Title: [D] Building a deterministic "payment firewall" for AI agents — no LLM in the decision path

We're seeing more and more agent harnesses that can spend money: crypto trading bots, billing agents, e-commerce copilots. The scary part isn't the LLM writing good or bad code — it's that when it decides whether to authorize a payment, the decision itself is probabilistic.

I've been working on MandateGuard: a guardrail layer that sits between the agent and any money-moving tool.

Key design decisions:
1. authorize() is a pure deterministic function. Same (agent, tool, args, budget, policy) → same verdict. Every time.
2. Mandates are Ed25519-signed offline. The agent cannot mint its own authorization.
3. Every decision lands in a SHA-256-chained audit ledger (append-only, tamper-evident).
4. Full MCP server, so it drops into Claude/Cursor/harness workflows.

Pro licensing is honestly a bootstrap test: 149 USDT/mo buys revocation + persistent state, paid in USDT via Phantom.

Curious how others here are handling the authorization problem for agents that can act in the real world. Is anyone using something like a policy-as-code layer, or is it all ad-hoc middleware today?

Repo: https://github.com/ezequiellich44-cmd/MandateGuard

---

## r/artificial

Same as r/LocalLLaMA but with a line: "If you're building agents that call external APIs, spend tokens, or sign transactions — this is the 'who decides and can I prove it after' layer."

---

## X / Twitter (thread)

1/ Agents that move money are the most dangerous code we're shipping right now — because the authorization is probabilistic.
2/ MandateGuard: a deterministic pre-action payment guardrail. No LLM in the decision path.
3/ Budgets · allowlists · rate limits · signed Ed25519 mandates · SHA-256 audit ledger.
4/ Same inputs → same verdict. Every time. That's the whole point.
5/ MIT core, Pro 149 USDT/mo, USDT via Phantom.
6/ https://ezequiellich44-cmd.github.io/MandateGuard

---

## Posting notes
- HN: post from a real account with some karma; post at US morning (~9am ET); link to the live site + repo; answer every comment promptly.
- Reddit: r/LocalLLaMA self-post with [D] tag; engage with replies; don't astroturf.
- X: tag accounts that cover agent security/evals; engage on replies for ~2h after posting.