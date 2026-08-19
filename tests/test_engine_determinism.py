import pytest

from mandateguard.engine import PolicyEngine
from mandateguard.model import Intent, Policy, Scope


def test_deterministic_with_clock_and_rate_window():
    clock = iter([0.0, 0.0, 0.0, 3601.0, 3601.0, 3601.0])
    policy = Policy(scopes={"agent": Scope(tools=("pay",), max_calls_per_window=2, window_seconds=3600)})
    engine = PolicyEngine(policy, clock=lambda: next(clock))
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1)).approved
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1)).approved
    assert not engine.authorize(Intent(tool="pay", destination="x", amount=1)).approved
    # window rolled: clock now 3601 -> counters reset
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1)).approved


def test_state_commits_only_on_approval():
    policy = Policy(scopes={"agent": Scope(tools=("pay",))}, global_max_amount=10)
    engine = PolicyEngine(policy)
    denied = engine.authorize(Intent(tool="pay", destination="x", amount=100))
    assert not denied.approved
    assert engine.state("agent") == {"spent": 0, "calls": 0}


def test_require_mandate_gate():
    policy = Policy(scopes={"agent": Scope(tools=("pay",))}, require_mandate=True)
    engine = PolicyEngine(policy)
    from mandateguard.model import DecisionStatus
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1), mandate_ok=False).status == DecisionStatus.REQUIRES_APPROVAL
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1), mandate_ok=True).approved


def test_policy_roundtrip_dict():
    from mandateguard.model import Policy, Scope
    policy = Policy(
        scopes={"a": Scope(tools=("pay",), destinations=("d1",), max_amount=50, currency="eur")},
        global_max_amount=100,
        allowlist=("d1",),
        denylist=("bad",),
        require_mandate=True,
    )
    restored = Policy.from_dict(policy.to_dict())
    assert restored.scopes["a"].tools == ("pay",)
    assert restored.scopes["a"].currency == "eur"
    assert restored.allowlist == ("d1",)
    assert restored.require_mandate is True