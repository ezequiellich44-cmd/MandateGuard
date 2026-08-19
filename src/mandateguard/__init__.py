"""MandateGuard - deterministic, auditable payment policy for AI agents.

The decision path is pure Python: budgets, allowlists, rate limits, and
mandates are evaluated with no LLM in the loop. That property is what makes
every decision verifiable and every ledger entry reproducible.
"""

from mandateguard.model import (
    Decision,
    DecisionStatus,
    Intent,
    Policy,
    RuleResult,
    Scope,
)
from mandateguard.engine import PolicyEngine
from mandateguard.mandate import Mandate, MandateSigner, verify_mandate
from mandateguard.ledger.chain import (
    Ledger,
    LedgerEntry,
    LedgerIntegrityError,
    verify_chain,
)

__all__ = [
    "Decision",
    "DecisionStatus",
    "Intent",
    "Policy",
    "RuleResult",
    "Scope",
    "PolicyEngine",
    "Mandate",
    "MandateSigner",
    "verify_mandate",
    "Ledger",
    "LedgerEntry",
    "LedgerIntegrityError",
    "verify_chain",
    "__version__",
]

__version__ = "0.1.0"
