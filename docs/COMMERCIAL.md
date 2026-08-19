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

## Payments (USDT — Phantom wallets)

All Pro/Enterprise sales are paid in **USDT** to the maintainer's wallets:

| Chain | Wallet | Token |
| ----- | ------ | ----- |
| Solana | `3fZSMAyCEMhZwWiynbJDjoYNUT97aiV9BLzoUNroEMAz` | USDT-SPL |
| Ethereum | `0x4Ed4D0750453C027FA8398067d5af980Bcc9B6eD` | USDT-ERC20 |

### Automated order → payment → license pipeline

```bash
# 1. Create the order (prints the pay-to address and USDT amount)
python tools/sell.py order --customer Acme --plan pro --seats 5 --months 12

# 2. Customer sends USDT to the printed wallet, shares the tx hash + order id.

# 3. Verify the payment on-chain and issue the license automatically
python tools/sell.py satisfy --order MG-0001 --key <LICENSE_PRIVATE_KEY> \
    --chain solana --expected-usdt 149 --tx-hash <customer_tx>

# Or verify a specific transfer:
python tools/verify_payment.py --chain solana --invoice MG-0001 \
    --expected-usdt 149 --tx-hash <customer_tx>
```

`satisfy` only issues the license after on-chain confirmation (RPC for Solana,
Etherscan for Ethereum). Keep `.mandateguard_orders.json` as your sales ledger
(`tools/sell.py orders` lists all orders and statuses).

### Getting paid without the pipeline (manual)

1. Agree on plan + seats.
2. Share the relevant wallet above and the amount in USDT.
3. On receipt, verify the tx (Solscan / Etherscan) and run
   `python tools/sell.py license --key <priv> --customer X --plan pro --seats 5 --months 12`.
4. Email the license string; the customer activates via
   `mandateguard license-verify` or MCP `activate_license`.

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
