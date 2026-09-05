"""
Unit tests for Gemini LLM Narrative Layer & Fallback Engine (NexusTiq24 PS06).
"""

import json
from pathlib import Path
import pytest

from src.rules.engine import evaluate_customer_risk
from src.llm.narrator import generate_investigation_report, generate_template_fallback


DATA_DIR = Path(__file__).parent.parent / "data"


def test_narrative_fallback_clean_customer():
    with open(DATA_DIR / "clean_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    txs = data.get("transactions", [])
    result = evaluate_customer_risk(txs, data.get("customer_id"))
    report = generate_template_fallback(result, txs)

    assert report.startswith("ATTENTION NEEDED: NO")
    assert "Routine banking activity" in report or "no suspicious patterns" in report


def test_narrative_fallback_anomalous_customer():
    with open(DATA_DIR / "anomalous_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    txs = data.get("transactions", [])
    result = evaluate_customer_risk(txs, data.get("customer_id"))
    report = generate_template_fallback(result, txs)

    assert report.startswith("ATTENTION NEEDED: YES")
    assert "TXN-88219" in report
    assert "Unusually Large Transfer" in report


def test_generate_report_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    with open(DATA_DIR / "anomalous_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    txs = data.get("transactions", [])
    result = evaluate_customer_risk(txs, data.get("customer_id"))
    res = generate_investigation_report(result, txs, api_key_override=None)

    assert res.report_source == "deterministic_fallback"
    assert res.narrative_report.startswith("ATTENTION NEEDED: YES")


def test_generate_report_runtime_key_override(monkeypatch):
    # Pass an invalid override key to force failover and check key precedence log
    with open(DATA_DIR / "anomalous_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    txs = data.get("transactions", [])
    result = evaluate_customer_risk(txs, data.get("customer_id"))
    res = generate_investigation_report(result, txs, api_key_override="invalid_session_key_for_test")

    assert res.report_source == "deterministic_fallback"
    assert res.narrative_report.startswith("ATTENTION NEEDED: YES")
