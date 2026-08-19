# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | ✅ |
| < 1.0   | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security bugs.** Email
`ezequiellich44@gmail.com` with:

- Affected version(s)
- Steps to reproduce
- Impact assessment

You will receive an acknowledgment within 48 hours and a fix target date
within 7 days. We credit reporters (unless they prefer anonymity).

## Scope

The deterministic engine (`engine.py`), mandate verification (`mandate.py`),
license verification (`licensing.py`), and ledger (`ledger/chain.py`) are the
security-critical surface. Vulnerabilities in the MCP transport layer must be
reported too but are generally mitigated by deploying behind authenticated
MCP auth.

## Threat model

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md). In short: MandateGuard
limits the blast radius of a compromised agent; it does not make the model
trustworthy, and key management / transport security are deployment
responsibilities.
