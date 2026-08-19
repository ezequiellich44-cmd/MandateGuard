# Threat Model

Scope: what MandateGuard protects against, and the boundaries of that
protection. It is a **pre-action authorization layer** for money-moving tool
calls made by AI agents.

## In scope — mitigated by MandateGuard

| Threat | How it's mitigated |
|---|---|
| **Drain attack / excessive spend** (agent calls `pay` repeatedly) | Per-call max, per-actor global budget, per-window rate limit |
| **Destination squatting / address confusion** | Destination allowlist + denylist at policy and scope level |
| **Tool abuse** (agent invokes unintended privileged tool) | Per-actor tool allowlist in scope |
| **Self-escalation** (agent edits its own policy/limits) | Immutable `Policy` model; policy updates are separate, authenticated, MCP-side operations |
| **Unbounded time window** (agent keeps acting for days) | Signed mandates with `not_before` / `not_after` windows |
| **Forged or replayed mandates** | Ed25519 signatures + nonce per mandate |
| **Silent history tampering** (attacker edits the audit log) | SHA-256 hash-chained, append-only ledger; `verify_chain` detects any edit/reorder/delete |
| **Non-repudiation of decisions** | Every decision recorded with actor, intent, per-rule results, timestamp, and chain hash |

## Out of scope — you must handle elsewhere

- **Key management**: the private key used by `MandateSigner` and any MCP
  admin credentials are your responsibility. Compromised keys nullify mandate
  guarantees.
- **MCP transport security**: this project exposes the engine over MCP; wire
  auth, TLS, and tool permissions are configured at the MCP layer, not here.
- **Model-level attacks**: prompt injection, jailbreaks, and memory poisoning
  are **not** blocked here. MandateGuard limits the *blast radius* of a
  compromised agent; it does not make the model trustworthy.
- **Execution correctness**: MandateGuard decides; it does not execute the
  tool call. A buggy `pay` implementation downstream is out of scope.
- **DoS of the policy plane**: the engine is synchronous and in-process.
- **Mandate circulation**: this repo verifies signatures and windows but does
  not implement revocation lists or blockchain settlement.

## Security invariants (tests)

- Same inputs ⇒ same verdict (determinism test).
- State commits only on approval (budget test asserts denied calls don't
  consume spend).
- Mandate signature forgery/tamper/expiry all fail verification.
- Ledger tamper (edit, reorder, corrupt file) is detected.

## Deployment checklist

1. Generate `MandateSigner` keys out-of-band; store the private key in a
   secrets manager.
2. Set scopes to the minimum tools/destinations needed.
3. Prefer allowlist over denylist; default-deny destinations.
4. Keep the audit ledger on an append-only / object-lock storage or ship
   hashes to an external notary.
5. Lock MCP `set_scope`/`set_global_policy` behind authenticated admin tools.
