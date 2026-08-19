# Changelog

All notable changes to MandateGuard are documented here.

## [1.0.0] - 2026-08-19

Initial production release.

### Added
- Deterministic `PolicyEngine` with injectable clock (replay-verifiable).
- Per-actor scopes: tools, destinations, per-call max, currency, per-window
  rate limits.
- Global guards: cumulative budget, destination allowlist/denylist.
- Ed25519-signed, time-boxed mandates (`MandateSigner`, `verify_mandate`)
  in the AP2 / x402 / ERC-8004 pattern.
- Tamper-evident SHA-256 chained audit `Ledger` with integrity verification.
- `RevocationRegistry` for mandate nonce revocation (Pro).
- Persistence: `PolicyStore`, `EngineStateStore` (Pro).
- Commercial licensing: `LicenseIssuer`, `verify_license`, `PLANS`
  (Pro/Enterprise feature gates).
- Full CLI (`mandateguard`): policy CRUD, authorize, mandates, ledger,
  license genkey/issue/verify.
- MCP server with Pro feature gates and `activate_license`.
- CI matrix Python 3.10–3.13; 38 tests.
- Vendor tool `tools/issue_license.py` for issuing paid licenses.
- GitHub Pages landing page with pricing.

### Security
- State commits only on approval (denied calls never consume budget).
- Window roll fix: rate-limit windows now reset correctly on expiry.
- License verification validates the originally-signed payload before
  applying plan feature sets.
