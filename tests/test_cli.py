import json
import subprocess
import sys

from mandateguard.licensing import (
    License,
    LicenseIssuer,
    generate_private_key_hex,
    verify_license,
)


def run_cli(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "mandateguard.cli", *args],
        capture_output=True, text=True, cwd=cwd,
    )


def test_cli_authorize_flow(tmp_path):
    state = tmp_path / "state"
    r = run_cli("--state-dir", str(state), "set-scope", "--actor", "bot", "--tools", "pay",
                "--max-amount", "100", cwd=tmp_path)
    assert r.returncode == 0
    r = run_cli("--state-dir", str(state), "authorize", "--tool", "pay", "--destination", "0xX",
                "--amount", "10", "--actor", "bot", cwd=tmp_path)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["status"] == "approved"


def test_cli_denies_overspend_and_persists(tmp_path):
    state = tmp_path / "state"
    run_cli("--state-dir", str(state), "set-scope", "--actor", "bot", "--tools", "pay", cwd=tmp_path)
    run_cli("--state-dir", str(state), "set-global", "--global-max", "100", cwd=tmp_path)
    run_cli("--state-dir", str(state), "authorize", "--tool", "pay", "--destination", "0xX",
            "--amount", "60", "--actor", "bot", cwd=tmp_path)
    r = run_cli("--state-dir", str(state), "authorize", "--tool", "pay", "--destination", "0xX",
                "--amount", "60", "--actor", "bot", cwd=tmp_path)
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["status"] == "denied"
    assert out["results"][3]["rule"] == "budget"


def test_cli_ledger_integrity(tmp_path):
    state = tmp_path / "state"
    run_cli("--state-dir", str(state), "set-scope", "--actor", "bot", "--tools", "pay", cwd=tmp_path)
    run_cli("--state-dir", str(state), "authorize", "--tool", "pay", "--destination", "0xX",
            "--amount", "1", "--actor", "bot", cwd=tmp_path)
    r = run_cli("--state-dir", str(state), "ledger-verify", cwd=tmp_path)
    assert r.returncode == 0
    assert "verified=True" in r.stdout


def test_cli_license_issue_verify(tmp_path):
    priv = generate_private_key_hex()
    issuer = LicenseIssuer(bytes.fromhex(priv))
    pub = issuer.public_key_bytes.hex()
    r = run_cli("license-issue", "--private-key", priv, "--customer", "Acme", "--plan", "pro",
                "--not-after", "2099-01-01T00:00:00+00:00", cwd=tmp_path)
    assert r.returncode == 0
    token = r.stdout.strip()
    r = run_cli("license-verify", "--public-key", pub, "--license", token, cwd=tmp_path)
    assert r.returncode == 0
    assert "pro" in r.stdout
    # expired license is rejected
    r = run_cli("license-issue", "--private-key", priv, "--customer", "Acme", "--plan", "pro",
                "--not-after", "2000-01-01T00:00:00+00:00", cwd=tmp_path)
    token = r.stdout.strip()
    r = run_cli("license-verify", "--public-key", pub, "--license", token, cwd=tmp_path)
    assert r.returncode == 3
    assert "expired" in r.stderr