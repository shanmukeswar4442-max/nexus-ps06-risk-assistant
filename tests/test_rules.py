"""
Unit Test Suite for Deterministic Risk Rule Engine (NexusTiq24 PS06).
"""

import json
from pathlib import Path
import pytest

from src.rules.engine import evaluate_customer_risk


DATA_DIR = Path(__file__).parent.parent / "data"


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

    assert result.attention_needed is False
    assert len(result.triggered_rules) == 0
    assert result.overall_risk_score < 30
    assert len(result.flagged_transaction_ids) == 0


def test_anomalous_customer(anomalous_customer_data):
    txs = anomalous_customer_data.get("transactions", [])
    result = evaluate_customer_risk(txs, anomalous_customer_data.get("customer_id"))

    assert result.attention_needed is True
    assert len(result.triggered_rules) >= 2
    assert result.overall_risk_score >= 60

    rule_ids = [r.rule_id for r in result.triggered_rules]
    assert "RULE_LARGE_TRANSFER" in rule_ids
    assert "RULE_PAYEE_BURST" in rule_ids
    assert "TXN-88219" in result.flagged_transaction_ids


def test_borderline_customer(borderline_customer_data):
    txs = borderline_customer_data.get("transactions", [])
    result = evaluate_customer_risk(txs, borderline_customer_data.get("customer_id"))

    assert result.attention_needed is False or result.confidence_level == "LOW"
    assert result.overall_risk_score < 40


def test_empty_transactions():
    result = evaluate_customer_risk([], "CUST-EMPTY")
    assert result.attention_needed is False
    assert result.overall_risk_score == 0
    assert result.confidence_level == "NONE"
    assert result.triggered_rules == []
    assert result.flagged_transaction_ids == []
