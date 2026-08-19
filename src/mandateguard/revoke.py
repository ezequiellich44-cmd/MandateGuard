"""Mandate revocation registry.

A signed mandate is valid until it expires or until its nonce is revoked.
Revocation is tracked locally (append-only) so an issued mandate can be
withdrawn before expiry - essential for key-compromise or misuse response.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class RevocationRegistry:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._revoked: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._revoked = set(data.get("nonces", []))

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"nonces": sorted(self._revoked)}, fh, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            os.unlink(tmp)
            raise

    def revoke(self, nonce: str) -> None:
        self._revoked.add(nonce)
        self._flush()

    def is_revoked(self, nonce: str) -> bool:
        return nonce in self._revoked

    @property
    def revoked(self) -> set[str]:
        return set(self._revoked)
