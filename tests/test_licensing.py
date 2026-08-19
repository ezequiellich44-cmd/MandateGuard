from mandateguard.engine import PolicyEngine
from mandateguard.licensing import (
    InvalidLicense,
    License,
    LicenseIssuer,
    generate_private_key_hex,
    verify_license,
)
from mandateguard.model import Intent, Policy, Scope

import pytest


def test_license_issue_and_verify_roundtrip():
    priv = generate_private_key_hex()
    issuer = LicenseIssuer(bytes.fromhex(priv))
    lic = License(customer="Acme", plan="pro", seats=5, not_after="2099-01-01T00:00:00+00:00",
                  features=["engine", "ledger", "mcp-basic", "revocation", "persistence"])
    token = issuer.issue(lic)
    verified = verify_license(issuer.public_key_bytes, token)
    assert verified.plan == "pro"
    assert verified.customer == "Acme"
    assert verified.seats == 5
    assert verified.can("revocation")
    assert not verified.can("sso")


def test_license_tamper_detected():
    priv = generate_private_key_hex()
    issuer = LicenseIssuer(bytes.fromhex(priv))
    lic = License(customer="Acme", plan="pro", not_after="2099-01-01T00:00:00+00:00", features=[])
    token = issuer.issue(lic)
    # flip a character in the token
    tampered = ("A" if token[0] != "A" else "B") + token[1:]
    with pytest.raises(InvalidLicense):
        verify_license(issuer.public_key_bytes, tampered)


def test_expired_license_rejected():
    priv = generate_private_key_hex()
    issuer = LicenseIssuer(bytes.fromhex(priv))
    lic = License(customer="Acme", plan="pro", not_after="2000-01-01T00:00:00+00:00", features=[])
    token = issuer.issue(lic)
    with pytest.raises(InvalidLicense):
        verify_license(issuer.public_key_bytes, token)


def test_plan_feature_matrix():
    from mandateguard.licensing import PLANS
    assert "sso" in PLANS["enterprise"]["features"]
    assert "revocation" in PLANS["pro"]["features"]
    assert "engine" in PLANS["community"]["features"]


def test_pro_gate_in_mcp_requires_license():
    from mandateguard.mcp import server as s
    # reset any prior license
    s._license = None
    res = s.revoke_mandate("nonce-x")
    assert res["ok"] is False
    assert "license" in res["error"]
    # activation works end to end
    priv = generate_private_key_hex()
    issuer = LicenseIssuer(bytes.fromhex(priv))
    lic = License(customer="Acme", plan="pro", not_after="2099-01-01T00:00:00+00:00",
                  features=["engine", "ledger", "mcp-basic", "revocation"])
    token = issuer.issue(lic)
    act = s.activate_license(issuer.public_key_bytes.hex(), token)
    assert act["ok"] is True
    assert s.license_status()["plan"] == "pro"
    res = s.revoke_mandate("nonce-x")
    assert res["ok"] is True
    s._license = None