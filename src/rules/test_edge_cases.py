"""
Edge case hardening unit tests for Transaction Risk Investigation Assistant (NexusTiq24 PS06).
Tests verify system resilience against:
- Malformed transaction rows (missing fields, invalid types, string amounts)
- Empty transaction histories
- Invalid ISO timestamps
- Gemini API error & timeout degradation
- Extreme value outliers & negative values
"""

import json
from pathlib import Path
import pytest

from src.core.config import settings
from src.core.models import RiskAnalysisResult
from src.rules.engine import evaluate_customer_risk, RiskRuleEngine
from src.llm.narrator import generate_investigation_report, generate_template_fallback


def test_malformed_string_amounts_and_missing_fields():
    malformed_txs = [
        # Missing timestamp & payee
        {"transaction_id": "TXN-BAD-1", "amount": 500.0},
        # String amount that should be parsed or handled gracefully
        {"transaction_id": "TXN-BAD-2", "amount": "1250.00", "timestamp": "2026-06-01T10:00:00", "payee": "Merchant A"},
        # Invalid amount string
        {"transaction_id": "TXN-BAD-3", "amount": "INVALID_AMOUNT", "timestamp": "2026-06-01T11:00:00", "payee": "Merchant B"},
        # None amount
        {"transaction_id": "TXN-BAD-4", "amount": None, "timestamp": "2026-06-01T12:00:00", "payee": "Merchant C"},
        # Negative amount
        {"transaction_id": "TXN-BAD-5", "amount": -250.0, "timestamp": "2026-06-01T13:00:00", "payee": "Merchant D"},
        # Completely empty dict row
        {}
    ]

    # Rule engine must process without throwing an exception
    result = evaluate_customer_risk(malformed_txs, "CUST-MALFORMED")
    assert isinstance(result, (dict, RiskAnalysisResult))
    assert "attention_needed" in result
    assert "overall_risk_score" in result
    assert result["overall_risk_score"] >= 0


def test_invalid_timestamps():
    bad_time_txs = [
        {"transaction_id": "TXN-T1", "amount": 100.0, "timestamp": "NOT-A-DATE", "payee": "Store A"},
        {"transaction_id": "TXN-T2", "amount": 200.0, "timestamp": None, "payee": "Store B"},
        {"transaction_id": "TXN-T3", "amount": 300.0, "timestamp": 123456789, "payee": "Store C"},
    ]

    result = evaluate_customer_risk(bad_time_txs, "CUST-BAD-TIME")
    assert isinstance(result, (dict, RiskAnalysisResult))
    assert result["customer_id"] == "CUST-BAD-TIME"


def test_gemini_exception_degradation(monkeypatch):
    """Verify that when Gemini client raises an exception, narrator degrades gracefully to fallback."""
    def mock_raise(*args, **kwargs):
        raise RuntimeError("Simulated Gemini API Network Timeout (504)")

    monkeypatch.setenv("GEMINI_API_KEY", "fake_key_for_testing")
    monkeypatch.setattr(settings, "DEFAULT_GEMINI_API_KEY", "fake_key_for_testing")
    
    # Force genai client to fail
    import sys
    import types

    fake_module = types.ModuleType("google.genai")
    fake_module.Client = mock_raise
    monkeypatch.setitem(sys.modules, "google.genai", fake_module)

    findings = {
        "customer_id": "CUST-FAILOVER",
        "attention_needed": True,
        "confidence_level": "HIGH",
        "overall_risk_score": 75,
        "summary_stats": {"total_transactions": 10, "avg_amount": 100.0, "p90_amount": 200.0},
        "triggered_rules": [
            {
                "rule_id": "RULE_LARGE_TRANSFER",
                "rule_name": "Unusually Large Transfer",
                "severity": "HIGH",
                "description": "Transfer of $5,000.00 exceeds baseline.",
                "flagged_transaction_ids": ["TXN-999"]
            }
        ],
        "flagged_transaction_ids": ["TXN-999"]
    }
    raw_txs = [{"transaction_id": "TXN-999", "amount": 5000.0, "payee": "Offshore Corp", "timestamp": "2026-07-01T12:00:00"}]

    res = generate_investigation_report(findings, raw_txs)
    
    assert res["source"] == "deterministic_fallback"
    assert "ATTENTION NEEDED: YES" in res["narrative_report"]
    assert "TXN-999" in res["narrative_report"]
    assert "Simulated Gemini API Network Timeout" in res["fallback_reason"]


def test_missing_transaction_id_resilience():
    txs_no_ids = [
        {"amount": 100.0, "timestamp": "2026-05-01T10:00:00", "payee": "Vendor 1"},
        {"amount": 200.0, "timestamp": "2026-05-02T10:00:00", "payee": "Vendor 2"},
    ]

    result = evaluate_customer_risk(txs_no_ids, "CUST-NO-IDS")
    assert result["attention_needed"] is False
    assert result["overall_risk_score"] == 0
