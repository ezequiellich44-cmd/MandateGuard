#!/usr/bin/env python
"""Issue MandateGuard Pro/Enterprise licenses (vendor-side).

This is the sales tool. You generate your vendor keypair once, keep the
private key secret, and run this for each paying customer:

    python tools/issue_license.py genkey
    python tools/issue_license.py issue \
        --private-key <hex> --customer Acme --plan pro --seats 5 \
        --not-after 2027-08-19T00:00:00+00:00

The output license string is what the customer passes to
`activate_license` (MCP) or `mandateguard license-verify`.
"""

from __future__ import annotations

import argparse
import sys

from mandateguard.licensing import (
    PLANS,
    InvalidLicense,
    License,
    LicenseIssuer,
    generate_private_key_hex,
    verify_license,
)


def cmd_genkey(args: argparse.Namespace) -> None:
    priv = generate_private_key_hex()
    pub = LicenseIssuer(bytes.fromhex(priv)).public_key_bytes.hex()
    print(f"LICENSE_PRIVATE_KEY={priv}")
    print(f"LICENSE_PUBLIC_KEY={pub}")
    print("\n# Store the private key in a secrets manager. Publish the public key.")
    print("# Ship the public key with the product; it is safe to embed.")


def cmd_issue(args: argparse.Namespace) -> None:
    issuer = LicenseIssuer(bytes.fromhex(args.private_key))
    features = PLANS[args.plan]["features"]
    lic = License(
        customer=args.customer,
        plan=args.plan,
        seats=args.seats,
        not_after=args.not_after,
        features=features,
    )
    print(issuer.issue(lic))


def cmd_verify(args: argparse.Namespace) -> None:
    try:
        lic = verify_license(bytes.fromhex(args.public_key), args.license)
    except InvalidLicense as exc:
        print(f"INVALID: {exc}")
        sys.exit(1)
    print(f"VALID  customer={lic.customer} plan={lic.plan} seats={lic.seats} "
          f"features={len(lic.features)} not_after={lic.not_after}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="issue_license", description="MandateGuard license vendor tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("genkey", help="generate vendor signing keys")
    p.set_defaults(fn=cmd_genkey)

    p = sub.add_parser("issue", help="issue a license for a customer")
    p.add_argument("--private-key", required=True)
    p.add_argument("--customer", required=True)
    p.add_argument("--plan", required=True, choices=["pro", "enterprise"])
    p.add_argument("--seats", type=int, default=1)
    p.add_argument("--not-after", required=True, help="ISO8601 expiry")
    p.set_defaults(fn=cmd_issue)

    p = sub.add_parser("verify", help="verify a license")
    p.add_argument("--public-key", required=True)
    p.add_argument("--license", required=True)
    p.set_defaults(fn=cmd_verify)

    args = parser.parse_args()
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())