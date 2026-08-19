#!/usr/bin/env python
"""MandateGuard sales helper: orders, on-chain payment, licenses.

This is the direct-revenue path. Flow:

    python tools/sell.py setup                         # vendor keys (store privately)
    python tools/sell.py order --customer Acme --plan pro --seats 5 --months 12
                                                        # prints invoice + wallet + amount
    # customer pays USDT to the printed wallet (SOL or ETH)
    python tools/sell.py satisfy --order MG-0001 --key <hex> --chain solana --expected-usdt 149
                                                        # verifies payment + issues license
    python tools/sell.py check --key <pub> --license <b64>   # verify before delivery

    python tools/sell.py license --key <hex> --customer Acme --plan pro \
        --seats 5 --months 12                  # issue without payment check (e.g. invoice)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mandateguard.licensing import (
    InvalidLicense,
    License,
    LicenseIssuer,
    generate_private_key_hex,
    verify_license,
)

PRICING = {
    "pro": {"per_seat_month": 29.8, "base": 149, "seats_included": 5},
    "enterprise": {"per_seat_month": 15, "base": 990, "seats_included": 10},
}

SOLANA_WALLET = "3fZSMAyCEMhZwWiynbJDjoYNUT97aiV9BLzoUNroEMAz"
ETH_WALLET = "0x4Ed4D0750453C027FA8398067d5af980Bcc9B6eD"

ORDERS_FILE = ".mandateguard_orders.json"


def _price(plan: str, seats: int) -> float:
    p = PRICING[plan]
    return p["base"] + max(0, seats - p["seats_included"]) * p["per_seat_month"]


def _load_orders() -> dict:
    if Path(ORDERS_FILE).is_file():
        return json.loads(Path(ORDERS_FILE).read_text(encoding="utf-8"))
    return {}


def _save_orders(orders: dict) -> None:
    Path(ORDERS_FILE).write_text(json.dumps(orders, indent=2, sort_keys=True), encoding="utf-8")


def cmd_setup(args: argparse.Namespace) -> None:
    priv = generate_private_key_hex()
    pub = LicenseIssuer(bytes.fromhex(priv)).public_key_bytes.hex()
    print("# Keep this file out of git. Store in a secrets manager.")
    print(f"LICENSE_PRIVATE_KEY={priv}")
    print(f"LICENSE_PUBLIC_KEY={pub}")


def cmd_order(args: argparse.Namespace) -> None:
    total = _price(args.plan, args.seats)
    orders = _load_orders()
    order_id = f"MG-{len(orders) + 1:04d}"
    orders[order_id] = {
        "customer": args.customer,
        "plan": args.plan,
        "seats": args.seats,
        "months": args.months,
        "usdt": total,
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    _save_orders(orders)
    print(f"ORDER {order_id} for {args.customer} ({args.plan}, {args.seats} seats, {args.months} mo)")
    print(f"AMOUNT: {total:,.2f} USDT")
    print(f"PAY TO (Solana USDT-SPL): {SOLANA_WALLET}")
    print(f"PAY TO (Ethereum USDT-ERC20): {ETH_WALLET}")
    print("Ask the customer to include the order id in the memo/note.")


def cmd_satisfy(args: argparse.Namespace) -> None:
    orders = _load_orders()
    order = orders.get(args.order)
    if order is None:
        print(f"ERROR: order {args.order} not found")
        sys.exit(2)
    expected = order["usdt"]
    if args.expected_usdt:
        expected = args.expected_usdt
    verify = Path(__file__).parent / "verify_payment.py"
    cmd = [sys.executable, str(verify), "--chain", args.chain,
           "--invoice", args.order, "--expected-usdt", str(expected)]
    if args.tx_hash:
        cmd += ["--tx-hash", args.tx_hash]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print(f"Payment not confirmed (code {proc.returncode}).", file=sys.stderr)
        sys.exit(1)
    order["status"] = "paid"
    _save_orders(orders)
    expires = (datetime.now(timezone.utc) + timedelta(days=order["months"] * 30)).isoformat()
    issuer = LicenseIssuer(bytes.fromhex(args.key))
    lic = License(customer=order["customer"], plan=order["plan"], seats=order["seats"],
                  not_after=expires, features=[])
    token = issuer.issue(lic)
    print("\nPAYMENT CONFIRMED - license issued:")
    print(token)


def cmd_license(args: argparse.Namespace) -> None:
    expires = (datetime.now(timezone.utc) + timedelta(days=args.months * 30)).isoformat()
    issuer = LicenseIssuer(bytes.fromhex(args.key))
    lic = License(customer=args.customer, plan=args.plan, seats=args.seats,
                  not_after=expires, features=[])
    token = issuer.issue(lic)
    price = PRICING[args.plan]
    total = _price(args.plan, args.seats)
    print(f"# {args.customer} | {args.plan} | {args.seats} seats | {args.months} months")
    print(f"# suggested invoice: ${total:,.0f}  (expires {expires})")
    print(token)


def cmd_check(args: argparse.Namespace) -> None:
    try:
        lic = verify_license(bytes.fromhex(args.key), args.license)
    except InvalidLicense as exc:
        print(f"INVALID: {exc}")
        sys.exit(1)
    print(f"VALID customer={lic.customer} plan={lic.plan} seats={lic.seats} "
          f"not_after={lic.not_after} features={len(lic.features)}")


def cmd_orders(args: argparse.Namespace) -> None:
    orders = _load_orders()
    if not orders:
        print("no orders yet")
        return
    for oid, o in orders.items():
        print(f"{oid} | {o['customer']} | {o['plan']} | {o['seats']} seats "
              f"| {o['usdt']:,.2f} USDT | {o['status']}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="sell", description="MandateGuard sales tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup", help="generate vendor keypair")
    p.set_defaults(fn=cmd_setup)

    p = sub.add_parser("order", help="create an order and print the pay-to address")
    p.add_argument("--customer", required=True)
    p.add_argument("--plan", required=True, choices=["pro", "enterprise"])
    p.add_argument("--seats", type=int, default=5)
    p.add_argument("--months", type=int, default=12)
    p.set_defaults(fn=cmd_order)

    p = sub.add_parser("satisfy", help="verify payment and issue the license")
    p.add_argument("--order", required=True)
    p.add_argument("--key", required=True, help="LICENSE_PRIVATE_KEY hex")
    p.add_argument("--chain", required=True, choices=["solana", "ethereum"])
    p.add_argument("--expected-usdt", type=float, default=0)
    p.add_argument("--tx-hash", default=None)
    p.set_defaults(fn=cmd_satisfy)

    p = sub.add_parser("license", help="issue a paid license (manual / invoice)")
    p.add_argument("--key", required=True)
    p.add_argument("--customer", required=True)
    p.add_argument("--plan", required=True, choices=["pro", "enterprise"])
    p.add_argument("--seats", type=int, default=5)
    p.add_argument("--months", type=int, default=12)
    p.set_defaults(fn=cmd_license)

    p = sub.add_parser("check", help="verify a license before delivery")
    p.add_argument("--key", required=True, help="public key hex")
    p.add_argument("--license", required=True)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("orders", help="list orders")
    p.set_defaults(fn=cmd_orders)

    args = parser.parse_args()
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())