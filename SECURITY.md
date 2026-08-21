# Security Policy

## Reporting Vulnerabilities

Report security vulnerabilities via GitHub Issues (private if possible).

## Threat Model

MandateGuard is a **deterministic pre-action enforcement engine** for autonomous AI agents.

**In scope:**
- Prompt injection leading to unauthorized payments
- Excessive agency (agent spending beyond limits)
- Supply chain attacks on MCP tool dependencies
- Replay attacks on signed mandates

**Out of scope:**
- Compromise of the host system (OS-level attacks)
- Compromise of the signing key itself (key management is the user's responsibility)
- Attacks that bypass the MCP server entirely (direct tool access)

## Key Management

- Signing keys (`LICENSE_PRIVATE_KEY`) loaded from environment variables
- Never hardcode keys in source code
- Recommended: use OS keychain or vault for production
- Key rotation: generate new keypair, update environment, revoke old key

## Failure Modes

- **Fail-closed:** If the policy engine is unreachable or errors, payment calls are denied
- **No silent failures:** All authorization failures are logged and returned as deny
- **Rate limiter:** Fails closed (deny on error)

## Audit Trail

- SHA-256 hash chain provides local tamper-evidence
- Does not prove tail deletion or full-ledger replacement without external checkpoint
- For high-assurance audit: integrate with external timestamping service or append-only log

## Policy Mutation

- Policy files are read-only at startup
- Hot-reload requires signed policy update (Ed25519)
- Rollback: keep previous policy hash, revert to last known-good


## LedgerBudgetStore

Budget and rate-limit state is reconstructed from the append-only ledger chain at boot. This prevents the restart-reset vulnerability (issue #3).
