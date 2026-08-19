#!/usr/bin/env python
"""Monitor the MandateGuard pay wallet and auto-flag paid orders.

Polls verify_payment.py for each pending order and marks it PAID when the
expected USDT arrives at the pay-to wallet. A later `satisfy` step issues the
license. Run: python tools/monitor_payments.py --interval 60

Use the same verification logic as tools/verify_payment.py via subprocess so
nothing drifts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "tools" / "verify_payment.py"
ORDERS_FILE = ROOT / ".mandateguard_orders.json"

PYTHON = sys.executable


def load_orders() -> dict:
    if not ORDERS_FILE.exists():
        return {}
    return json.loads(ORDERS_FILE.read_text(encoding="utf-8"))


def save_orders(orders: dict) -> None:
    ORDERS_FILE.write_text(
        json.dumps(orders, indent=2, sort_keys=True), encoding="utf-8"
    )


def verify(order: dict) -> tuple[bool, str]:
    amount = order.get("usdt") or order.get("amount")
    chains = ["solana", "ethereum"]
    if order.get("network"):
        chains = [order["network"]]
    for chain in chains:
        cmd = [
            PYTHON, str(VERIFY),
            "--chain", chain,
            "--invoice", order.get("id", "MG-?"),
            "--expected-usdt", str(amount),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            return True, f"{chain} {proc.stdout.strip()[:300]}"
    return False, f"no payment on {', '.join(chains)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single pass, then exit")
    ap.add_argument("--interval", type=int, default=60, help="poll seconds")
    args = ap.parse_args()

    print(f"watching {ORDERS_FILE}", flush=True)
    while True:
        orders = load_orders()
        changed = False
        for oid, order in orders.items():
            if order.get("status") != "pending":
                continue
            paid, detail = verify(order)
            if paid:
                order["status"] = "paid"
                order["paid_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                order["verify_detail"] = detail
                changed = True
                print(f"ORDER {oid} PAID ({order.get('usdt')} USDT) {detail}", flush=True)
            else:
                print(f"ORDER {oid}: pending {detail}", flush=True)
        if changed:
            save_orders(orders)
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
