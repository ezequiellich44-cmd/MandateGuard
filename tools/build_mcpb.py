#!/usr/bin/env python
"""Build the MandateGuard MCPB bundle (for MCP Registry distribution).

Usage: python tools/build_mcpb.py [--version 1.0.0] [--out dist]

Produces dist/mandateguard-<version>.mcpb, a zip (per the MCPB spec) containing
manifest.json, pyproject.toml, and src/ with the MCP server entry point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "mandateguard"


def build(version: str, out_dir: Path) -> Path:
    if not PKG.is_dir():
        raise SystemExit(f"package source not found at {PKG}")
    tmp = Path(tempfile.mkdtemp(prefix="mg-mcpb-"))
    shutil.copytree(PKG, tmp / "src" / "mandateguard")
    (tmp / "src" / "main.py").write_text(
        '"""MCP bundle entry point: starts the MandateGuard MCP server over stdio."""\n'
        "import sys\nfrom pathlib import Path\n\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent))\n\n"
        "from mandateguard.mcp.server import main\n\n"
        'if __name__ == "__main__":\n    main()\n',
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": "0.3",
        "name": "mandateguard",
        "display_name": "MandateGuard",
        "version": version,
        "description": "Deterministic payment policy guardrail for AI agents",
        "long_description": (
            "MandateGuard is the pre-action enforcement layer for AI agents that move money. "
            "Every tool call is evaluated against budgets, allowlists, rate limits, and signed "
            "Ed25519 mandates with NO LLM in the decision path. Ships a tamper-evident SHA-256 "
            "audit ledger and full MCP tool surface. MIT core; Pro license for revocation/persistence."
        ),
        "author": {"name": "Eze Lech", "email": "ezequiellich44@gmail.com",
                   "url": "https://github.com/ezequiellich44-cmd"},
        "repository": {"type": "git", "url": "https://github.com/ezequiellich44-cmd/MandateGuard.git"},
        "homepage": "https://ezequiellich44-cmd.github.io/MandateGuard",
        "support": "https://github.com/ezequiellich44-cmd/MandateGuard/issues",
        "license": "MIT",
        "keywords": ["ai-security", "guardrails", "payments", "policy-engine", "ledger",
                     "budget", "allowlist"],
        "compatibility": {"platforms": ["darwin", "win32", "linux"],
                          "runtimes": {"python": ">=3.10,<4.0"}},
        "server": {"type": "uv", "entry_point": "src/main.py"},
        "tools": [
            {"name": "activate_license", "description": "Activate a MandateGuard Pro license"},
            {"name": "license_status", "description": "Report current license state"},
            {"name": "set_scope", "description": "Define what an actor is allowed to do"},
            {"name": "set_global_policy", "description": "Configure global guards"},
            {"name": "authorize", "description": "Evaluate a tool call against policy"},
            {"name": "init_ledger", "description": "Initialize or load the audit ledger"},
            {"name": "ledger_status", "description": "Report ledger integrity and head hash"},
            {"name": "create_mandate_signer", "description": "Generate an Ed25519 keypair"},
            {"name": "issue_mandate", "description": "Issue a signed, time-boxed mandate"},
            {"name": "check_mandate", "description": "Verify a mandate signature"},
            {"name": "revoke_mandate", "description": "Revoke a mandate by nonce (Pro)"},
            {"name": "persist_state", "description": "Persist policy and state to JSON (Pro)"},
            {"name": "reset_state", "description": "Reset spend and rate counters"},
        ],
        "tools_generated": True,
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (tmp / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[project]\nname = "mandateguard"\nversion = "%s"\n'
        'description = "Deterministic, auditable payment policy engine for AI agents."\n'
        'requires-python = ">=3.10"\nlicense = { text = "MIT" }\n'
        'authors = [{ name = "Eze Lech", email = "ezequiellich44@gmail.com" }]\n'
        'dependencies = ["cryptography>=42", "fastmcp>=2.0"]\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["src/mandateguard"]\n' % version,
        encoding="utf-8",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"mandateguard-{version}.mcpb"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(tmp.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(tmp))
    shutil.rmtree(tmp, ignore_errors=True)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"built {out} ({out.stat().st_size} bytes)")
    print(f"sha256 {digest}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    args = ap.parse_args()
    build(args.version, args.out)
    sys.exit(0)