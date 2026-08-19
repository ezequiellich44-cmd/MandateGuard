"""Immutable data models for the MandateGuard policy engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DecisionStatus(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass(frozen=True)
class Scope:
    """What an agent is allowed to do, expressed as plain data."""

    tools: tuple[str, ...] = ()
    destinations: tuple[str, ...] = ()
    max_amount: int = 0
    currency: str = "usd"
    max_calls_per_window: int = 0
    window_seconds: int = 3600


@dataclass
class Policy:
    """Deterministic policy evaluated by the engine."""

    scopes: dict[str, Scope] = field(default_factory=dict)
    global_max_amount: int = 0
    allowlist: tuple[str, ...] = ()
    denylist: tuple[str, ...] = ()
    require_mandate: bool = False


@dataclass(frozen=True)
class Intent:
    """A single tool call the agent wants to execute."""

    tool: str
    destination: str
    amount: int = 0
    currency: str = "usd"
    actor: str = "agent"


@dataclass(frozen=True)
class RuleResult:
    rule: str
    passed: bool
    detail: str = ""
    limit_remaining: int | None = None


@dataclass
class Decision:
    status: DecisionStatus
    intent: Intent
    actor: str
    results: list[RuleResult] = field(default_factory=list)
    decided_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def approved(self) -> bool:
        return self.status == DecisionStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "actor": self.actor,
            "intent": {
                "tool": self.intent.tool,
                "destination": self.intent.destination,
                "amount": self.intent.amount,
                "currency": self.intent.currency,
            },
            "results": [r.__dict__ for r in self.results],
            "decided_at": self.decided_at,
        }
