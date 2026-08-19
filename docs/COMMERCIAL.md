# Selling MandateGuard

How the product makes money, and how you (the maintainer) run the sales
motion. The MIT core is the marketing; the Pro/Enterprise license is the
product.

## Product tiers

| Tier | Price | What unlocks | License |
| ---- | ----- | ------------ | ------- |
| Community | Free | Engine, scopes, mandates, ledger, basic MCP | MIT |
| Pro | $149/mo · per instance | Revocation, persistence, RBAC, multi-tenant, webhooks | Signed Pro license |
| Enterprise | Custom | SSO/SAML, audit notary, SLA, on-prem, volume | Signed Enterprise license |

All tiers share the same binary: Pro/Enterprise are activated with a signed
license key. This keeps distribution trivial (one wheel) and upgrades
instant (one string).

## Licensing mechanics

1. Generate your vendor keys once (keep private key secret):

   ```bash
   python tools/issue_license.py genkey
   ```

2. Issue a license for a paying customer:

   ```bash
   python tools/issue_license.py issue \
     --private-key <hex> --customer Acme --plan pro --seats 5 \
     --not-after 2027-08-19T00:00:00+00:00
   ```

3. Customer activates it (MCP tool `activate_license` or CLI
   `mandateguard license-verify`). Features gate automatically.

## Pricing playbook

- **Land and expand**: Community converts evaluation → Pro when teams hit
  revocation/persistence needs. Anchor Pro at the price of one agent wallet
  incident (drains average $10k–$45M).
- **Seats**: price by seats for multi-tenant; seats are encoded in the
  license.
- **Audit notary** (Enterprise) is a compliance sell: externalized hash
  anchoring for SOC 2 / financial audits.
- **Renewals**: licenses expire (`not_after`); re-issue at renewal. No
  calls-to-home required in this version (offline verification).

## Channels

- **GitHub**: stars + issues are the funnel. Landing page
  (`https://ezequiellich44-cmd.github.io/MandateGuard`) is the conversion
  point.
- **MCP marketplaces**: publish the MCP server (skills.sh, PulseMCP,
  mcpmarket) — "the new app store". Community edition is the sampler.
- **PyPI**: `pip install mandateguard` — run `tools/publish_pypi.sh` with a
  PyPI API token (`TWINE_USERNAME=__token__`).
- **Direct sales**: enterprise deals via `ezequiellich44@gmail.com`.

## What NOT to do

- Do not hardcode the private key into the repo or product.
- Do not weaken the MIT core to force upgrades — the deterministic engine
  being open is the trust story that sells Pro.
- Do not add phone-home licensing in the OSS build; offline verification is
  a feature.

## Income checklist (getting to first revenue)

1. [ ] Publish to PyPI (needs API token).
2. [ ] Enable GitHub Pages for the landing site (repo settings).
3. [ ] Verify your GitHub Sponsors profile.
4. [ ] Publish the MCP server to 2+ marketplaces.
5. [ ] Post launch (HN "Show HN", Product Hunt, r/LocalLLaMA) — include the
       drain statistics and the demo.
6. [ ] Offer 5 founding-customer Pro licenses at a discount to collect
       testimonials and pricing signal.
