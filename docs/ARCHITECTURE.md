# Architecture

## Goals

1. **Determinism** — the authorization verdict is a pure function of the
   request and prior accepted state. No LLM, no randomness, no sampling.
2. **Verifiability** — any decision can be replayed and any ledger can be
   re-checked from the first entry.
3. **Least privilege** — agents operate inside explicitly granted scopes that
   they cannot widen on their own.

## Components

### `model.py` — plain data
- `Scope`: per-actor envelope (tools, destinations, max per call, currency,
  rate limits).
- `Policy`: scopes + global guards (total budget, allowlist, denylist,
  `require_mandate`).
- `Intent`: one tool call proposed by an agent.
- `Decision`: verdict + per-rule results + timestamp. Serializable.

### `engine.py` — deterministic evaluator
`PolicyEngine.authorize(intent, mandate_ok)` runs rules in fixed order and
short-circuits on first failure:

1. **scope** — does the actor have a scope, is the tool allowed, destination
   allowed, per-call amount within limit, currency correct?
2. **allowlist** — global destination allowlist (if configured).
3. **denylist** — global destination denylist.
4. **budget** — global cumulative spend cap per actor.
5. **rate_limit** — per-window call cap.

State (spend counters, call counters, window start) commits **only on
approval**. This keeps `authorize` deterministic under replay: denied requests
never mutate state.

Decision statuses:
- `APPROVED` — all rules passed, state committed.
- `DENIED` — a hard rule failed.
- `REQUIRES_APPROVAL` — `require_mandate` is set and no valid mandate is
  presented (soft gate: human-in-the-loop).

### `mandate.py` — signed authorizations
AP2/x402-style mandate: a short-lived, nonce-bound, issuer-signed envelope
(actor, max amount, currency, tools, destinations, validity window). Signed
with Ed25519. `verify_mandate` checks signature + expiry. Mandates complement
the policy: policy is config, mandate is *cryptographic proof* the issuer
consented.

### `ledger/chain.py` — tamper-evident audit trail
Every entry stores `(index, prev_hash, payload, entry_hash, recorded_at)`
where `entry_hash = sha256(prev_hash | index | payload)` and the chain is
linked via `prev_hash = parent.entry_hash`. `verify_chain` detects any edit,
reorder, or deletion in O(n). Optionally persisted to a JSON file; loading a
corrupt file raises `LedgerIntegrityError`.

### `mcp/server.py` — distribution channel
FastMCP server exposing the engine as tools an agent can mount. Because the
server itself exposes `set_scope`/`set_global_policy`, deployments should lock
those down via MCP auth/permissions in production.

## Decision flow

```
Intent ──> authorize ──> [scope][allowlist][denylist][budget][rate_limit][mandate]
                                   │ all pass?
                                   ├─ yes ─> commit state ─> APPROVED
                                   ├─ no hard fail ───────> DENIED
                                   └─ mandate required but missing ─> REQUIRES_APPROVAL
                                            │
                                            └─ all decisions → ledger (append-only)
```

## Extensibility

Rules live in `engine.py` as `_rule_*` methods. Adding a rule = add a method
that returns `RuleResult` and register it in the ordered tuple inside
`authorize`. Keep rules pure (no I/O, no wall clock beyond the injected
window) to preserve determinism.

## Non-goals

- Not a wallet, chain, or sequencer — it decides, it does not execute.
- Not an LLM safety classifier — it enforces policy; it does not judge intent
  semantics.
