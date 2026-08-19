import pytest

from mandateguard.engine import PolicyEngine
from mandateguard.model import DecisionStatus, Intent, Policy, Scope


def test_scope_blocks_unknown_tool():
    policy = Policy(scopes={"agent": Scope(tools=("pay",))})
    engine = PolicyEngine(policy)
    decision = engine.authorize(Intent(tool="transfer", destination="wallet", amount=100))
    assert decision.status == DecisionStatus.DENIED
    assert decision.results[0].rule == "scope"


def test_allowlist_blocks_unknown_destination():
    policy = Policy(
        scopes={"agent": Scope(tools=("pay",))},
        allowlist=("0xaaa",),
    )
    engine = PolicyEngine(policy)
    decision = engine.authorize(Intent(tool="pay", destination="0xbbb", amount=100))
    assert decision.status == DecisionStatus.DENIED
    assert decision.results[1].rule == "allowlist"


def test_denylist_blocks():
    policy = Policy(scopes={"agent": Scope(tools=("pay",))}, denylist=("0xdead",))
    engine = PolicyEngine(policy)
    decision = engine.authorize(Intent(tool="pay", destination="0xdead", amount=1))
    assert decision.status == DecisionStatus.DENIED
    assert decision.results[2].rule == "denylist"


def test_global_budget_enforced_and_tracked():
    policy = Policy(scopes={"agent": Scope(tools=("pay",))}, global_max_amount=100)
    engine = PolicyEngine(policy)
    first = engine.authorize(Intent(tool="pay", destination="0xaaa", amount=60))
    assert first.status == DecisionStatus.APPROVED
    second = engine.authorize(Intent(tool="pay", destination="0xaaa", amount=60))
    assert second.status == DecisionStatus.DENIED
    assert second.results[3].rule == "budget"
    assert engine.state("agent")["spent"] == 60


def test_per_call_max_amount_in_scope():
    policy = Policy(scopes={"agent": Scope(tools=("pay",), max_amount=50)})
    engine = PolicyEngine(policy)
    assert engine.authorize(Intent(tool="pay", destination="x", amount=50)).status == DecisionStatus.APPROVED
    assert engine.authorize(Intent(tool="pay", destination="x", amount=51)).status == DecisionStatus.DENIED


def test_rate_limit():
    policy = Policy(scopes={"agent": Scope(tools=("pay",), max_calls_per_window=2)})
    engine = PolicyEngine(policy)
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1)).status == DecisionStatus.APPROVED
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1)).status == DecisionStatus.APPROVED
    third = engine.authorize(Intent(tool="pay", destination="x", amount=1))
    assert third.status == DecisionStatus.DENIED
    assert third.results[4].rule == "rate_limit"


def test_requires_approval_when_mandate_missing():
    policy = Policy(scopes={"agent": Scope(tools=("pay",))}, require_mandate=True)
    engine = PolicyEngine(policy)
    decision = engine.authorize(Intent(tool="pay", destination="x", amount=1), mandate_ok=False)
    assert decision.status == DecisionStatus.REQUIRES_APPROVAL


def test_deterministic_same_inputs_same_verdict():
    policy = Policy(scopes={"agent": Scope(tools=("pay",), max_amount=100)})
    d1 = PolicyEngine(policy).authorize(Intent(tool="pay", destination="x", amount=80))
    d2 = PolicyEngine(policy).authorize(Intent(tool="pay", destination="x", amount=80))
    assert d1.status == d2.status
    assert d1.to_dict()["results"] == d2.to_dict()["results"]
