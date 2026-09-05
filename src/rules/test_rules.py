"""
Unit tests for Pure-Python Risk Rule Engine (NexusTiq24 PS06) — INR Edition.
Tests cover:
- Clean customer (0 rules fired, attention_needed = False)
- Anomalous customer (multiple rules fired, attention_needed = True, exact cited IDs)
- Borderline customer (demonstrates restraint, low score/confidence)
- Individual rule unit tests
- Edge cases (empty history, missing fields)
"""

import json
from pathlib import Path
import pytest

from src.rules.engine import evaluate_customer_risk, RiskRuleEngine


# Load sample datasets for testing
DATA_DIR = Path(__file__).parent.parent.parent / "data"


@pytest.fixture
def clean_customer_data():
    path = DATA_DIR / "clean_customer.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"customer_id": "CUST-1001", "transactions": []}


@pytest.fixture
def anomalous_customer_data():
    path = DATA_DIR / "anomalous_customer.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"customer_id": "CUST-1002", "transactions": []}


@pytest.fixture
def borderline_customer_data():
    path = DATA_DIR / "borderline_customer.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"customer_id": "CUST-1003", "transactions": []}


def test_clean_customer(clean_customer_data):
    txs = clean_customer_data.get("transactions", [])
    result = evaluate_customer_risk(txs, clean_customer_data.get("customer_id"))

    assert result["attention_needed"] is False
    assert len(result["triggered_rules"]) == 0
    assert result["overall_risk_score"] < 30
    assert len(result["flagged_transaction_ids"]) == 0


def test_anomalous_customer(anomalous_customer_data):
    txs = anomalous_customer_data.get("transactions", [])
    result = evaluate_customer_risk(txs, anomalous_customer_data.get("customer_id"))

    assert result["attention_needed"] is True
    assert len(result["triggered_rules"]) >= 2
    assert result["overall_risk_score"] >= 60

    triggered_rule_ids = [r["rule_id"] for r in result["triggered_rules"]]
    assert "RULE_LARGE_TRANSFER" in triggered_rule_ids
    assert "RULE_PAYEE_BURST" in triggered_rule_ids

    flagged_ids = result["flagged_transaction_ids"]
    assert "TXN-88219" in flagged_ids
    assert "TXN-88220" in flagged_ids or "TXN-88221" in flagged_ids


def test_borderline_customer(borderline_customer_data):
    txs = borderline_customer_data.get("transactions", [])
    result = evaluate_customer_risk(txs, borderline_customer_data.get("customer_id"))

    assert result["attention_needed"] is False or result["confidence_level"] == "LOW"
    assert result["overall_risk_score"] < 40


def test_empty_transactions():
    result = evaluate_customer_risk([], "CUST-EMPTY")
    assert result["attention_needed"] is False
    assert result["overall_risk_score"] == 0
    assert result["confidence_level"] == "NONE"
    assert result["triggered_rules"] == []
    assert result["flagged_transaction_ids"] == []


def test_isolated_large_transfer():
    txs = [
        {"transaction_id": f"TXN-{i}", "amount": 5000.0, "timestamp": f"2026-05-01T10:{i:02d}:00", "category": "Retail"}
        for i in range(10)
    ]
    # Add giant outlier transfer in INR
    txs.append({
        "transaction_id": "TXN-LARGE-OUTLIER",
        "amount": 850000.0,
        "timestamp": "2026-05-02T14:00:00",
        "category": "Transfer",
        "payee": "Unknown Offshore Corp"
    })

    result = evaluate_customer_risk(txs, "CUST-TEST-LARGE")
    assert result["attention_needed"] is True
    assert "TXN-LARGE-OUTLIER" in result["flagged_transaction_ids"]
    assert any(r["rule_id"] == "RULE_LARGE_TRANSFER" for r in result["triggered_rules"])


def test_isolated_odd_hours():
    txs = [
        {"transaction_id": "TXN-ODD-1", "amount": 120000.0, "timestamp": "2026-06-01T03:15:00", "channel": "Wire Transfer", "payee": "Offshore Bank"},
        {"transaction_id": "TXN-NORMAL-1", "amount": 250.0, "timestamp": "2026-06-01T12:00:00", "channel": "UPI", "payee": "Chai Point"}
    ]

    result = evaluate_customer_risk(txs, "CUST-TEST-ODD")
    flagged = result["flagged_transaction_ids"]
    assert "TXN-ODD-1" in flagged
    assert "TXN-NORMAL-1" not in flagged
