#!/usr/bin/env python
"""Autonomous sales processor for MandateGuard.

Runs inside GitHub Actions on purchase/trial issues. Verifies USDT payments
on-chain (keyless public RPCs) and emits a signed license for automatic
delivery as an issue comment.

Issue contract:
  Title starts with [TRIAL]    -> immediate 14-day Pro trial license.
  Title starts with [PURCHASE] -> verify payment, then issue license.

Body fields (markdown bold labels):
  **Order ID:** ...
  **Plan:** pro-monthly | pro-annual
  **Chain:** solana | ethereum
  **Amount sent (USDT):** ...
  **TX hash / signature:** ...
  **Customer / company name for license:** ...

Outputs (for the calling workflow):
  Writes license text to $LICENSE_FILE when successful.
  Prints a JSON verdict to stdout: {"result": "PAID|TRIAL|NOT_FOUND|ERROR", ...}

Exit codes: 0 = license issued, 1 = payment not found yet, 2 = error.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SOLANA_WALLET = "3fZSMAyCEMhZwWiynbJDjoYNUT97aiV9BLzoUNroEMAz"
ETH_WALLET = "0x4Ed4D0750453C027FA8398067d5af980Bcc9B6eD"

USDT_SOLANA_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
USDT_ETH_CONTRACT = "0xdac17f958d2ee523a2206206994597c13d831ec7"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
ETH_RPC_CANDIDATES = [
    "https://ethereum-rpc.publicnode.com",
    "https://eth.llamarpc.com",
    "https://cloudflare-eth.com",
]

PLAN_DURATIONS = {
    "pro-monthly": (99.0, 31),
    "pro-annual": (1430.0, 366),
}
PLAN_SEATS = {"pro-monthly": 5, "pro-annual": 25}


def _post_json(url: str, payload: dict, timeout: int = 45) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "mandateguard-sales/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get_json(url: str, timeout: int = 45) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "mandateguard-sales/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ---------------- Solana ----------------

def solana_verify_tx(tx_sig: str, expected_usdt: float) -> dict:
    result = _post_json(SOLANA_RPC, {
        "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
        "params": [tx_sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
    })
    tx = result.get("result")
    if not tx:
        return {"ok": False, "error": "transaction not found (not yet confirmed or wrong network)"}
    meta = tx.get("meta") or {}
    if meta.get("err"):
        return {"ok": False, "error": f"transaction failed on-chain: {meta['err']}"}
    delta = 0.0
    touched = False
    for b in meta.get("postTokenBalances") or []:
        if b.get("mint") == USDT_SOLANA_MINT and b.get("owner") == SOLANA_WALLET:
            touched = True
            delta += float(b["uiTokenAmount"]["uiAmount"] or 0)
    for b in meta.get("preTokenBalances") or []:
        if b.get("mint") == USDT_SOLANA_MINT and b.get("owner") == SOLANA_WALLET:
            delta -= float(b["uiTokenAmount"]["uiAmount"] or 0)
    if not touched:
        return {"ok": False, "error": "tx does not move USDT-SPL into the vendor wallet"}
    ok = delta >= expected_usdt * 0.999
    return {"ok": ok, "amount_usdt": round(delta, 6),
            "error": None if ok else f"amount {delta} < expected {expected_usdt}"}


REPLAY_SEARCH_URL = (
    "https://api.github.com/search/issues?q={query}"
)


def tx_already_claimed(repo: str, tx_hash: str, current_issue: int, token: str) -> bool:
    """True if this exact tx hash appears in any other sales issue (replay guard)."""
    try:
        q = urllib.parse.quote(f'repo:{repo} "{tx_hash}"')
        req = urllib.request.Request(
            REPLAY_SEARCH_URL.format(query=q),
            headers={
                "User-Agent": "mandateguard-sales/1.0",
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        for item in data.get("items", []):
            if item.get("number") != current_issue:
                return True
    except Exception:
        pass
    return False


# ---------------- Ethereum ----------------

def _eth_rpc(method: str, params: list) -> dict:
    last_err = None
    for rpc in ETH_RPC_CANDIDATES:
        try:
            out = _post_json(rpc, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            if "error" in out:
                last_err = out["error"]
                continue
            return out["result"]
        except Exception as exc:
            last_err = str(exc)
    raise RuntimeError(f"all ETH RPCs failed: {last_err}")


def eth_verify_tx(tx_hash: str, expected_usdt: float) -> dict:
    receipt = _eth_rpc("eth_getTransactionReceipt", [tx_hash.lower()])
    if not receipt:
        return {"ok": False, "error": "tx not found or not confirmed yet"}
    if receipt.get("status") != "0x1":
        return {"ok": False, "error": "transaction reverted"}
    total = 0.0
    wallet_topic = "0x" + "0" * 24 + ETH_WALLET[2:].lower()
    for log in receipt.get("logs", []):
        if (log.get("address", "").lower() != USDT_ETH_CONTRACT
                or (log.get("topics") or [""])[0].lower() != TRANSFER_TOPIC):
            continue
        topics = log["topics"]
        if len(topics) >= 3 and topics[2].lower() == wallet_topic:
            total += int(log["data"], 16) / 1e6
    ok = total >= expected_usdt * 0.999
    return {"ok": ok, "amount_usdt": round(total, 6), "tx_hash": tx_hash,
            "error": None if ok else f"tx moves {total} USDT to vendor wallet, expected {expected_usdt}"}


# ---------------- Issue parsing ----------------

FIELD_PATTERNS = {
    "order_id": r"\*\*Order ID:\*\*\s*(.+)",
    "plan": r"\*\*Plan:\*\*\s*(\S+)",
    "chain": r"\*\*Chain:\*\*\s*(\S+)",
    "amount": r"\*\*Amount sent \(USDT\):\*\*\s*([\d.,]+)",
    "tx_hash": r"\*\*TX hash / signature:\*\*\s*(\S+)",
    "customer": r"\*\*Customer / company name for license:\*\*\s*(.+)",
}


def parse_body(body: str) -> dict:
    fields = {}
    for key, pat in FIELD_PATTERNS.items():
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            fields[key] = m.group(1).strip().strip("*_`").strip()
    return fields


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    license_file = os.environ.get("LICENSE_FILE", "license.txt")
    with open(event_path, encoding="utf-8") as fh:
        event = json.load(fh)
    issue = event.get("issue") or {}
    title = (issue.get("title") or "").strip()
    body = issue.get("body") or ""
    author = (issue.get("user") or {}).get("login") or "customer"
    number = issue.get("number")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from mandateguard.licensing import License, LicenseIssuer

    private_key = os.environ.get("LICENSE_PRIVATE_KEY", "")
    issuer = LicenseIssuer(bytes.fromhex(private_key))

    def emit(result: dict, license_text: str | None = None, code: int = 0) -> int:
        if license_text:
            with open(license_file, "w", encoding="utf-8") as fh:
                fh.write(license_text)
        print(json.dumps({"issue": number, **result}))
        return code

    upper = title.upper()

    if upper.startswith("[TRIAL]"):
        lic = License(
            customer=f"trial-{author}",
            plan="pro", seats=1,
            not_after=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        )
        return emit({"result": "TRIAL"}, issuer.issue(lic), 0)

    if not upper.startswith("[PURCHASE]"):
        return emit({"result": "IGNORED", "reason": "not a sales issue"}, None, 0)

    fields = parse_body(body)
    plan = (fields.get("plan") or "").lower()
    chain = (fields.get("chain") or "").lower()
    order_id = fields.get("order_id") or f"MG-ISSUE-{number}"
    customer = fields.get("customer") or author

    if plan not in PLAN_DURATIONS:
        return emit({"result": "ERROR", "reason": f"unknown plan '{plan}'"}, None, 2)
    expected_usdt, days = PLAN_DURATIONS[plan]

    tx_hash = re.sub(r"^<|>$", "", (fields.get("tx_hash") or "").strip()).strip()
    if not tx_hash or tx_hash.startswith("PASTE_"):
        return emit({"result": "NOT_FOUND",
                     "reason": "no transaction hash provided — edit the issue and paste your TX hash"},
                    None, 1)

    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if repo_full and gh_token and tx_already_claimed(repo_full, tx_hash, number, gh_token):
        return emit({"result": "ERROR", "reason": "this transaction hash was already claimed on another order"}, None, 2)

    try:
        if chain == "solana":
            verdict = solana_verify_tx(tx_hash, expected_usdt)
        elif chain == "ethereum":
            verdict = eth_verify_tx(tx_hash, expected_usdt)
        else:
            return emit({"result": "ERROR", "reason": f"unknown chain '{chain}'"}, None, 2)
    except Exception as exc:
        return emit({"result": "ERROR", "reason": f"{type(exc).__name__}: {exc}"}, None, 2)

    if not verdict.get("ok"):
        return emit({"result": "NOT_FOUND", "reason": verdict.get("error"), "order_id": order_id}, None, 1)

    not_after = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    lic = License(customer=customer, plan="pro", seats=PLAN_SEATS[plan],
                  not_after=not_after)
    return emit({
        "result": "PAID", "order_id": order_id, "plan": plan, "chain": chain,
        "amount_usdt": verdict.get("amount_usdt"), "tx_hash": verdict.get("tx_hash"),
        "seats": PLAN_SEATS[plan], "expires": not_after,
    }, issuer.issue(lic), 0)


if __name__ == "__main__":
    sys.exit(main())
