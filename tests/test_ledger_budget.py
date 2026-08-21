from mandateguard.ledger_budget import Ledger, LedgerBudgetStore

def test_ledger_budget_rebuild():
    ledger = Ledger("/tmp/test_audit.jsonl")
    # Simulate some approved entries
    ledger.append({"actor": "agent-001", "verdict": "approved", "amount": 50.0})
    ledger.append({"actor": "agent-001", "verdict": "approved", "amount": 30.0})
    ledger.append({"actor": "agent-002", "verdict": "denied", "amount": 0})
    
    store = LedgerBudgetStore(ledger)
    assert store.get_spent("agent-001") == 80.0
    assert store.get_calls("agent-001") == 2
    assert store.get_spent("agent-002") == 0
    assert store.get_calls("agent-002") == 0
    print("All tests passed!")

if __name__ == "__main__":
    test_ledger_budget_rebuild()