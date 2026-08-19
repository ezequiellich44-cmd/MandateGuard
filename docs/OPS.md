# MandateGuard operations — sales runbook

How to sell, verify payment, and issue licenses. All state is local files
(`.mandateguard_orders.json`, `.mandateguard_vendor.key` — both gitignored).

## Pipeline (verified end-to-end 2026-08-19)

```
sell setup   → vendor Ed25519 keypair (keep private key secret)
sell order   → create invoice MG-NNNN, print pay-to wallets + amount
monitor      → polls both wallets; flags order PAID when USDT arrives
sell satisfy → on-chain verify → issue signed Pro license JWT
sell check   → validate a license before delivery
```

## Vendor keys

```bash
python tools/sell.py setup
# prints:
#   LICENSE_PRIVATE_KEY=<64 hex>
#   LICENSE_PUBLIC_KEY=<64 hex>
```

Save to `.mandateguard_vendor.key` (gitignored) or a secrets manager.
NEVER commit the private key.

## Create an order

```bash
python tools/sell.py order --customer "Acme Corp" --plan pro --seats 5 --months 12
# prints: ORDER MG-0002, AMOUNT 149.00 USDT, both pay-to wallets
```

Wallets:
- Solana USDT-SPL: `3fZSMAyCEMhZwWiynbJDjoYNUT97aiV9BLzoUNroEMAz`
- Ethereum USDT-ERC20: `0x4Ed4D0750453C027FA8398067d5af980Bcc9B6eD`

## Detect payment (auto)

```bash
python tools/monitor_payments.py --interval 60
# prints per pending order: "pending <reason>" or "ORDER MG-0001 PAID (149 USDT)"
```

## Issue the license once paid

```bash
# auto mode (monitor found the balance):
python tools/sell.py satisfy --order MG-0001 --key <PRIV_KEY> --chain solana
# or confirm a specific tx the customer shared:
python tools/sell.py satisfy --order MG-0001 --key <PRIV_KEY> \
    --chain solana --tx-hash <txhash>
```

`satisfy` verifies on-chain, marks the order paid, and prints the signed
license token. Send that token to the customer.

## Verify a license before sending

```bash
python tools/sell.py check --key <PUB_KEY> --license <JWT>
# VALID customer=... plan=pro seats=5 not_after=... features=...
```

## Pricing

| Plan       | Price                   | Includes |
|------------|-------------------------|----------|
| Community  | Free (MIT)              | engine, scopes, mandates, ledger, basic MCP |
| Pro        | 149 USDT/mo · 5 seats   | + revocation registry, persistence, RBAC, webhooks |
| Enterprise | custom (from $990/mo)   | + SSO/SAML, audit notary, SLA, on-prem |