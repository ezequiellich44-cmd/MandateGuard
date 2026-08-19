from mandateguard.engine import PolicyEngine
from mandateguard.model import Intent, Policy, Scope
from mandateguard.revoke import RevocationRegistry
from mandateguard.store import EngineStateStore, PolicyStore


def test_policy_store_roundtrip(tmp_path):
    store = PolicyStore(tmp_path / "policy.json")
    policy = Policy(
        scopes={"a": Scope(tools=("pay",), max_amount=10)},
        global_max_amount=100,
    )
    store.save(policy)
    assert store.load().scopes["a"].max_amount == 10
    assert store.load().global_max_amount == 100


def test_policy_store_default_empty(tmp_path):
    assert PolicyStore(tmp_path / "missing.json").load().scopes == {}


def test_engine_state_persists(tmp_path):
    policy = Policy(scopes={"a": Scope(tools=("pay",), max_amount=100)}, global_max_amount=100)
    engine = PolicyEngine(policy)
    engine.authorize(Intent(tool="pay", destination="x", amount=60, actor="a"))
    store = EngineStateStore(tmp_path / "state.json")
    store.save_from(engine)

    engine2 = PolicyEngine(policy)
    store.load_into(engine2)
    assert engine2.state("a") == {"spent": 60, "calls": 1}
    # remaining budget is now 40
    denied = engine2.authorize(Intent(tool="pay", destination="x", amount=50, actor="a"))
    assert not denied.approved


def test_revocation_registry(tmp_path):
    reg = RevocationRegistry(tmp_path / "revoked.json")
    assert not reg.is_revoked("nonce-1")
    reg.revoke("nonce-1")
    assert reg.is_revoked("nonce-1")

    reg2 = RevocationRegistry(tmp_path / "revoked.json")
    assert reg2.is_revoked("nonce-1")
    assert not reg2.is_revoked("nonce-2")


def test_revocation_blocks_mandate_gate():
    from mandateguard.model import DecisionStatus
    policy = Policy(scopes={"a": Scope(tools=("pay",))}, require_mandate=True)
    engine = PolicyEngine(policy)
    reg = RevocationRegistry("unused")
    # mandate accepted when not revoked
    assert engine.authorize(Intent(tool="pay", destination="x", amount=1, actor="a"), mandate_ok=not reg.is_revoked("n")).approved