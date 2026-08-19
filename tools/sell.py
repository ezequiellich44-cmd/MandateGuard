#!/usr/bin/env python
"""MandateGuard sales helper: generate vendor keys and the first licenses.

This is the direct-revenue path. Usage:

    python tools/sell.py setup                 # generate vendor keys (store privately)
    python tools/sell.py license --key <hex> --customer Acme --plan pro \
        --seats 5 --months 12                  # issue a paid license
    python tools/sell.py license --key <hex> --customer Acme --plan enterprise \
        --seats 50 --months 12                 # enterprise
    python tools/sell.py check --key <hex> --license <b64>   # verify before delivery
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from mandateguard.licensing import (
    InvalidLicense,
    License,
    LicenseIssuer,
    generate_private_key_hex,
    verify_license,
)

PRICING = {
    "pro": {"per_seat_month": 29.8, "base": 149},          # $149/mo incl 5 seats
    "enterprise": {"per_seat_month": 15, "base": 990},     # custom floor $990/mo
}


def cmd_setup(args: argparse.Namespace) -> None:
    priv = generate_private_key_hex()
    pub = LicenseIssuer(bytes.fromhex(priv)).public_key_bytes.hex()
    print("# Keep this file out of git. Store in a secrets manager.")
    print(f"LICENSE_PRIVATE_KEY={priv}")
    print(f"LICENSE_PUBLIC_KEY={pub}")
    print()
    print("# Public key ships with the product (safe to embed):")
    print("#   mandateguard license-verify --public-key <pub> --license <b64>")


def cmd_license(args: argparse.Namespace) -> None:
    expires = (datetime.now(timezone.utc) + timedelta(days=args.months * 30)).isoformat()
    issuer = LicenseIssuer(bytes.fromhex(args.key))
    lic = License(
        customer=args.customer,
        plan=args.plan,
        seats=args.seats,
        not_after=expires,
        features=[],
    )
    token = issuer.issue(lic)
    price = PRICING[args.plan]
    total = price["base"] + max(0, args.seats - 5) * price["per_seat_month"]
    print(f"# {args.customer} | {args.plan} | {args.seats} seats | {args.months} months")
    print(f"# suggested invoice: ${total:,.0f}/mo  (expires {expires})")
    print(token)


def cmd_check(args: argparse.Namespace) -> None:
    try:
        lic = verify_license(bytes.fromhex(args.key), args.license)
    except InvalidLicense as exc:
        print(f"INVALID: {exc}")
        sys.exit(1)
    print(f"VALID customer={lic.customer} plan={lic.plan} seats={lic.seats} "
          f"not_after={lic.not_after} features={len(lic.features)}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="sell", description="MandateGuard sales tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup", help="generate vendor keypair")
    p.set_defaults(fn=cmd_setup)

    p = sub.add_parser("license", help="issue a paid license")
    p.add_argument("--key", required=True, help="LICENSE_PRIVATE_KEY hex")
    p.add_argument("--customer", required=True)
    p.add_argument("--plan", required=True, choices=["pro", "enterprise"])
    p.add_argument("--seats", type=int, default=5)
    p.add_argument("--months", type=int, default=12)
    p.set_defaults(fn=cmd_license)

    p = sub.add_parser("check", help="verify a license before delivery")
    p.add_argument("--key", required=True, help="public key hex")
    p.add_argument("--license", required=True)
    p.set_defaults(fn=cmd_check)

    args = parser.parse_args()
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())