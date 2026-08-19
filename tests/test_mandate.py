from mandateguard.mandate import Mandate, MandateSigner, now_iso, verify_mandate


def _mandate(nonce="n1") -> Mandate:
    return Mandate(
        actor="agent",
        max_amount=500,
        currency="usd",
        tools=("pay",),
        destinations=("0xaaa",),
        not_before=now_iso(),
        not_after="2099-01-01T00:00:00+00:00",
        nonce=nonce,
        issuer="issuer",
    )


def test_sign_and_verify_roundtrip():
    signer = MandateSigner()
    mandate = _mandate()
    sig = signer.sign(mandate)
    assert verify_mandate(signer.public_key_bytes, mandate, sig)


def test_tampered_mandate_fails():
    signer = MandateSigner()
    mandate = _mandate()
    sig = signer.sign(mandate)
    forged = Mandate(
        actor="evil",
        max_amount=999999,
        currency=mandate.currency,
        tools=mandate.tools,
        destinations=mandate.destinations,
        not_before=mandate.not_before,
        not_after=mandate.not_after,
        nonce=mandate.nonce,
        issuer=mandate.issuer,
    )
    assert not verify_mandate(signer.public_key_bytes, forged, sig)


def test_tampered_signature_fails():
    signer = MandateSigner()
    mandate = _mandate()
    sig = signer.sign(mandate)
    bad = "00" + sig[2:]
    assert not verify_mandate(signer.public_key_bytes, mandate, bad)


def test_wrong_key_fails():
    signer_a = MandateSigner()
    signer_b = MandateSigner()
    sig = signer_a.sign(_mandate())
    assert not verify_mandate(signer_b.public_key_bytes, _mandate(), sig)


def test_expired_mandate_fails():
    signer = MandateSigner()
    mandate = Mandate(
        actor="agent",
        max_amount=1,
        currency="usd",
        tools=("pay",),
        destinations=(),
        not_before="2000-01-01T00:00:00+00:00",
        not_after="2000-01-02T00:00:00+00:00",
        nonce="n",
        issuer="issuer",
    )
    sig = signer.sign(mandate)
    assert verify_mandate(signer.public_key_bytes, mandate, sig, require_not_expired=False)
    assert not verify_mandate(signer.public_key_bytes, mandate, sig)
