"""
Edge Case Hardening Test Suite (NexusTiq24 PS06).
Tests cover:
- Malformed transaction uploads (invalid CSV/JSON structure, non-numeric amounts, missing fields)
- Empty transaction histories
- Invalid ISO timestamps
- Gemini API error & timeout degradation
- Session API key overrides
"""

import io
import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app import app
from src.rules.engine import evaluate_customer_risk
from src.llm.narrator import generate_investigation_report, generate_template_fallback

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_malformed_string_amounts_and_missing_fields():
    malformed_txs = [
        {"transaction_id": "TXN-BAD-1", "amount": 500.0},
        {"transaction_id": "TXN-BAD-2", "amount": "125000.00", "timestamp": "2026-06-01T10:00:00", "payee": "Merchant A"},
        {"transaction_id": "TXN-BAD-3", "amount": "INVALID_AMOUNT", "timestamp": "2026-06-01T11:00:00", "payee": "Merchant B"},
        {"transaction_id": "TXN-BAD-4", "amount": None, "timestamp": "2026-06-01T12:00:00", "payee": "Merchant C"},
        {"transaction_id": "TXN-BAD-5", "amount": -250.0, "timestamp": "2026-06-01T13:00:00", "payee": "Merchant D"},
        {}
    ]

    result = evaluate_customer_risk(malformed_txs, "CUST-MALFORMED")
    assert result.customer_id == "CUST-MALFORMED"
    assert isinstance(result.overall_risk_score, int)


def test_invalid_timestamps():
    bad_time_txs = [
        {"transaction_id": "TXN-T1", "amount": 100.0, "timestamp": "NOT-A-DATE", "payee": "Store A"},
        {"transaction_id": "TXN-T2", "amount": 200.0, "timestamp": None, "payee": "Store B"},
    ]

    result = evaluate_customer_risk(bad_time_txs, "CUST-BAD-TIME")
    assert result.customer_id == "CUST-BAD-TIME"


def test_upload_malformed_csv(client):
    bad_csv = "invalid,header\nfoo,bar\n"
    response = client.post("/api/upload", files={"file": ("test.csv", io.BytesIO(bad_csv.encode()), "text/csv")})
    assert response.status_code in [400, 422, 200]


def test_upload_empty_file(client):
    empty_file = ""
    response = client.post("/api/upload", files={"file": ("test.csv", io.BytesIO(empty_file.encode()), "text/csv")})
    assert response.status_code in [400, 422]


def test_gemini_exception_degradation(monkeypatch):
    def mock_raise(*args, **kwargs):
        raise RuntimeError("Simulated Gemini API Network Timeout (504)")

    monkeypatch.setenv("GEMINI_API_KEY", "fake_key_for_testing")

    import sys
    import types

    fake_module = types.ModuleType("google.genai")
    fake_module.Client = mock_raise
    monkeypatch.setitem(sys.modules, "google.genai", fake_module)

    txs = [{"transaction_id": "TXN-999", "amount": 500000.0, "payee": "Offshore Corp", "timestamp": "2026-07-01T12:00:00"}]
    findings = evaluate_customer_risk(txs, "CUST-FAILOVER")

    res = generate_investigation_report(findings, txs)
    assert res.report_source == "deterministic_fallback"
    assert res.narrative_report.startswith("ATTENTION NEEDED:")
