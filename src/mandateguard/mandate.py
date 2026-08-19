"""Signed, scoped mandates (AP2-style intent/cart/payment authorization).

A mandate is a short-lived, cryptographically signed permission that lets an
agent act within an explicit envelope: maximum amount, allowed destinations,
allowed tools, and an expiry. The engine verifies the signature and envelope
before any execution - the agent cannot widen its own scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

SCHEMA = "mandateguard/mandate/v1"


@dataclass(frozen=True)
class Mandate:
    actor: str
    max_amount: int
    currency: str
    tools: tuple[str, ...]
    destinations: tuple[str, ...]
    not_before: str
    not_after: str
    nonce: str
    issuer: str

    def to_bytes(self) -> bytes:
        payload = (
            f"{SCHEMA}|{self.actor}|{self.max_amount}|{self.currency}|"
            f"{','.join(self.tools)}|{','.join(self.destinations)}|"
            f"{self.not_before}|{self.not_after}|{self.nonce}|{self.issuer}"
        )
        return payload.encode("utf-8")

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "actor": self.actor,
            "max_amount": self.max_amount,
            "currency": self.currency,
            "tools": list(self.tools),
            "destinations": list(self.destinations),
            "not_before": self.not_before,
            "not_after": self.not_after,
            "nonce": self.nonce,
            "issuer": self.issuer,
        }

    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        after = datetime.fromisoformat(self.not_after)
        before = datetime.fromisoformat(self.not_before)
        return now < before or now > after


class MandateSigner:
    """Creates and verifies Ed25519-signed mandates."""

    def __init__(self, private_key: bytes | None = None):
        if private_key is None:
            self._private = ed25519.Ed25519PrivateKey.generate()
        else:
            self._private = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
        self._public = self._private.public_key()

    @property
    def public_key_bytes(self) -> bytes:
        return self._public.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    def sign(self, mandate: Mandate) -> str:
        return self._private.sign(mandate.to_bytes()).hex()

    @classmethod
    def verify(cls, public_key: bytes, mandate: Mandate, signature_hex: str) -> bool:
        try:
            public = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
            public.verify(bytes.fromhex(signature_hex), mandate.to_bytes())
            return True
        except (InvalidSignature, ValueError):
            return False


def verify_mandate(
    public_key: bytes,
    mandate: Mandate,
    signature_hex: str,
    *,
    require_not_expired: bool = True,
) -> bool:
    if require_not_expired and mandate.is_expired():
        return False
    return MandateSigner.verify(public_key, mandate, signature_hex)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
