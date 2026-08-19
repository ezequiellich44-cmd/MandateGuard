"""Deterministic policy engine. No LLM in the decision path."""

from __future__ import annotations

import time
from typing import Callable

from mandateguard.model import (
    Decision,
    DecisionStatus,
    Intent,
    Policy,
    RuleResult,
)


class PolicyEngine:
    """Evaluates an Intent against a Policy and returns a Decision.

    Every rule is a pure function of the request and current state, so the
    same inputs always produce the same verdict. That determinism is the
    security property: an auditor can replay any decision from the ledger.

    The clock is injectable (``clock``) so rate-limit windows are fully
    deterministic in tests and replay tooling.
    """

    def __init__(self, policy: Policy, clock: Callable[[], float] | None = None):
        self.policy = policy
        self._clock = clock or time.monotonic
        self._spend: dict[str, int] = {}
        self._calls: dict[str, int] = {}
        self._window_start: dict[str, float] = {}

    # -- state tracking -----------------------------------------------------
    def _roll_window(self, actor: str, window_seconds: int) -> None:
        now = self._clock()
        start = self._window_start.get(actor)
        if start is None:
            self._window_start[actor] = now
            self._calls[actor] = 0
            self._spend[actor] = 0
        elif start + window_seconds < now:
            self._window_start[actor] = now
            self._calls[actor] = 0
            self._spend[actor] = 0

    # -- rules ---------------------------------------------------------------
    def _rule_scope(self, intent: Intent) -> RuleResult:
        scope = self.policy.scopes.get(intent.actor)
        if scope is None:
            return RuleResult("scope", False, "actor has no configured scope")
        if intent.tool not in scope.tools:
            return RuleResult("scope", False, f"tool '{intent.tool}' not allowed for actor")
        if scope.destinations and intent.destination not in scope.destinations:
            return RuleResult("scope", False, "destination not in scope allowlist")
        if scope.max_amount and intent.amount > scope.max_amount:
            return RuleResult("scope", False, "amount exceeds per-call scope limit")
        if intent.currency != scope.currency:
            return RuleResult("scope", False, "currency mismatch")
        return RuleResult("scope", True)

    def _rule_allowlist(self, intent: Intent) -> RuleResult:
        if not self.policy.allowlist:
            return RuleResult("allowlist", True, "no global allowlist configured")
        if intent.destination in self.policy.allowlist:
            return RuleResult("allowlist", True)
        return RuleResult("allowlist", False, "destination not allowlisted")

    def _rule_denylist(self, intent: Intent) -> RuleResult:
        if intent.destination in self.policy.denylist:
            return RuleResult("denylist", False, "destination is denylisted")
        return RuleResult("denylist", True)

    def _rule_global_budget(self, intent: Intent) -> RuleResult:
        if not self.policy.global_max_amount:
            return RuleResult("budget", True, "no global budget configured")
        spent = self._spend.get(intent.actor, 0)
        remaining = self.policy.global_max_amount - spent
        if intent.amount > remaining:
            return RuleResult("budget", False, "global budget exhausted", max(0, remaining))
        return RuleResult("budget", True, limit_remaining=remaining - intent.amount)

    def _rule_rate_limit(self, intent: Intent) -> RuleResult:
        scope = self.policy.scopes.get(intent.actor)
        if scope is None or not scope.max_calls_per_window:
            return RuleResult("rate_limit", True, "no rate limit configured")
        self._roll_window(intent.actor, scope.window_seconds)
        used = self._calls.get(intent.actor, 0)
        if used >= scope.max_calls_per_window:
            return RuleResult("rate_limit", False, "rate limit exceeded")
        return RuleResult("rate_limit", True, limit_remaining=scope.max_calls_per_window - used - 1)

    # -- public API -----------------------------------------------------------
    def authorize(self, intent: Intent, mandate_ok: bool = True) -> Decision:
        results: list[RuleResult] = []
        for rule in (
            self._rule_scope,
            self._rule_allowlist,
            self._rule_denylist,
            self._rule_global_budget,
            self._rule_rate_limit,
        ):
            result = rule(intent)
            results.append(result)
            if not result.passed:
                decision = Decision(DecisionStatus.DENIED, intent, intent.actor, results)
                return decision

        if self.policy.require_mandate and not mandate_ok:
            decision = Decision(DecisionStatus.REQUIRES_APPROVAL, intent, intent.actor, results)
            return decision

        # commit state only on approval - keeps replay deterministic
        self._spend[intent.actor] = self._spend.get(intent.actor, 0) + intent.amount
        self._calls[intent.actor] = self._calls.get(intent.actor, 0) + 1
        decision = Decision(DecisionStatus.APPROVED, intent, intent.actor, results)
        return decision

    def state(self, actor: str) -> dict:
        return {
            "spent": self._spend.get(actor, 0),
            "calls": self._calls.get(actor, 0),
        }
