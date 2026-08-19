"""Commercial licensing for MandateGuard Pro.

The OSS engine is MIT. Enterprises buy a **Pro license**: a signed JSON
payload (Ed25519) granting plan features, seat count, and an expiry window.
The same cryptographic machinery that signs agent mandates signs licenses, so
the verification code is already audited and tested.

A license is: ``base64(json + signature)``. Verify once at startup and pass
the license object into the engine; gated features check ``license.can(...)``.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

LICENSE_SCHEMA = "mandateguard/license/v1"

PLANS = {
    "community": {
        "label": "Community (MIT)",
        "features": ["engine", "ledger", "mcp-basic"],
    },
    "pro": {
        "label": "Pro",
        "features": [
            "engine",
            "ledger",
            "mcp-basic",
            "revocation",
            "persistence",
            "rbac",
            "webhooks",
            "multi-tenant",
        ],
    },
    "enterprise": {
        "label": "Enterprise",
        "features": [
            "engine",
            "ledger",
            "mcp-basic",
            "revocation",
            "persistence",
            "rbac",
            "webhooks",
            "multi-tenant",
            "sso",
            "sla",
            "audit-notary",
        ],
    },
}


@dataclass
class License:
    customer: str
    plan: str
    seats: int = 1
    not_before: str = ""
    not_after: str = ""
    features: list[str] = field(default_factory=list)

    @property
    def is_pro(self) -> bool:
        return self.plan in ("pro", "enterprise")

    def can(self, feature: str) -> bool:
        return feature in self.features

    def to_payload(self) -> dict:
        return {
            "schema": LICENSE_SCHEMA,
            "customer": self.customer,
            "plan": self.plan,
            "seats": self.seats,
            "not_before": self.not_before,
            "not_after": self.not_after,
            "features": self.features,
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_payload(), sort_keys=True).encode("utf-8")

    @classmethod
    def from_payload(cls, data: dict) -> "License":
        return cls(
            customer=str(data["customer"]),
            plan=str(data.get("plan", "community")),
            seats=int(data.get("seats", 1)),
            not_before=str(data.get("not_before", "")),
            not_after=str(data.get("not_after", "")),
            features=list(data.get("features", [])),
        )

    def is_expired(self) -> bool:
        if not self.not_after:
            return False
        now = datetime.now(timezone.utc)
        return now > datetime.fromisoformat(self.not_after)


class LicenseIssuer:
    """Vendor-side: issues signed Pro/Enterprise licenses."""

    def __init__(self, private_key: bytes):
        self._private = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)

    @property
    def public_key_bytes(self) -> bytes:
        return self._private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    def issue(self, license_: License) -> str:
        payload = license_.to_bytes()
        sig = self._private.sign(payload)
        envelope = {"license": license_.to_payload(), "signature": sig.hex()}
        return base64.urlsafe_b64encode(
            json.dumps(envelope, sort_keys=True).encode("utf-8")
        ).decode("ascii")


def verify_license(public_key: bytes, license_b64: str) -> License:
    """Verifies a license envelope and returns the License. Raises on failure."""
    try:
        raw = base64.urlsafe_b64decode(license_b64.encode("ascii"))
        envelope = json.loads(raw)
        sig = bytes.fromhex(envelope["signature"])
        license_ = License.from_payload(envelope["license"])
        pub = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
        pub.verify(sig, license_.to_bytes())
    except (InvalidSignature, ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise InvalidLicense("invalid license signature or envelope")
    if license_.is_expired():
        raise InvalidLicense("license expired")
    if license_.plan in PLANS and license_.plan != "community":
        license_.features = PLANS[license_.plan]["features"]
    return license_


class InvalidLicense(Exception):
    pass


def generate_private_key_hex() -> str:
    key = ed25519.Ed25519PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    ).hex()
