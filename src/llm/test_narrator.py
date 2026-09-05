"""
Unit tests for Gemini Narrative Layer & Fallback Engine (NexusTiq24 PS06).
"""

import json
from pathlib import Path
import pytest

from src.rules.engine import evaluate_customer_risk
from src.llm.narrator import generate_investigation_report, generate_template_fallback

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def test_narrative_fallback_clean_customer():
    with open(DATA_DIR / "clean_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    txs = data.get("transactions", [])
    findings = evaluate_customer_risk(txs, data.get("customer_id"))
    report = generate_template_fallback(findings, txs)

    assert report.startswith("ATTENTION NEEDED: NO")
    assert "No suspicious patterns" in report or "Routine banking activity" in report


def test_narrative_fallback_anomalous_customer():
    with open(DATA_DIR / "anomalous_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    txs = data.get("transactions", [])
    findings = evaluate_customer_risk(txs, data.get("customer_id"))
    report = generate_template_fallback(findings, txs)

    assert report.startswith("ATTENTION NEEDED: YES")
    assert "TXN-88219" in report
    assert "Unusually Large Transfer" in report
    assert "fraud" not in report.lower() or "never state that fraud" not in report.lower()


def test_generate_report_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    with open(DATA_DIR / "anomalous_customer.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    txs = data.get("transactions", [])
    findings = evaluate_customer_risk(txs, data.get("customer_id"))
    result = generate_investigation_report(findings, txs)

    assert result["source"] == "deterministic_fallback"
    assert result["narrative_report"].startswith("ATTENTION NEEDED: YES")
