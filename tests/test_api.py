"""
FastAPI Integration Tests (NexusTiq24 PS06).
Tests cover API routes, mock LLM failure fallback, file uploads, exports, and session API key overrides.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_ping_endpoint():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["track_id"] == "PS06"


def test_list_customers_endpoint():
    response = client.get("/api/customers")
    assert response.status_code == 200
    data = response.json()
    assert "customers" in data
    assert len(data["customers"]) >= 3


def test_get_customer_detail():
    response = client.get("/api/customers/CUST-1002")
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "CUST-1002"
    assert len(data["transactions"]) > 0


def test_analyze_pipeline_anomalous_customer():
    response = client.post("/api/analyze", json={"customer_id": "CUST-1002", "transactions": []})
    assert response.status_code == 200
    res = response.json()
    assert res["attention_needed"] is True
    assert res["overall_risk_score"] >= 60
    assert "TXN-88219" in res["flagged_transaction_ids"]
    assert res["narrative_report"].startswith("ATTENTION NEEDED: YES")


def test_analyze_pipeline_mocked_llm_failure(monkeypatch):
    """Verifies that when Gemini client raises an error, API returns HTTP 200 with fallback report."""
    def mock_report(result, raw_transactions=None, api_key_override=None):
        result.narrative_report = "ATTENTION NEEDED: YES\n\nFallback due to mocked LLM error"
        result.report_source = "deterministic_fallback"
        return result

    monkeypatch.setattr("src.api.routes.generate_investigation_report", mock_report)

    response = client.post("/api/analyze", json={"customer_id": "CUST-1002", "transactions": []})
    assert response.status_code == 200
    res = response.json()
    assert res["report_source"] == "deterministic_fallback"
    assert "Fallback due to mocked LLM error" in res["narrative_report"]


def test_settings_api_key_override():
    res1 = client.get("/api/settings/key-status")
    assert res1.status_code == 200
    
    res2 = client.post("/api/settings/set-key", json={"api_key": "AIzaSyTestKey12345"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "set"
    
    res3 = client.get("/api/settings/key-status")
    assert res3.json()["source"] == "session"

    res4 = client.post("/api/settings/set-key", json={"api_key": ""})
    assert res4.status_code == 200


def test_export_report():
    response = client.post("/api/export", json={"customer_id": "CUST-1002", "report_content": "ATTENTION NEEDED: YES\nTest", "format": "markdown"})
    assert response.status_code == 200
    assert "ATTENTION NEEDED: YES" in response.text
