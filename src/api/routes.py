"""
API Routes for Transaction Risk Investigation Assistant (NexusTiq24 PS06).
Exposes endpoints for customer dataset listing, transaction history retrieval, and risk analysis.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from src.rules.engine import evaluate_customer_risk
from src.llm.narrator import generate_investigation_report

router = APIRouter(prefix="/api", tags=["Investigation API"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class AnalysisRequest(BaseModel):
    customer_id: Optional[str] = "CUSTOM"
    transactions: List[Dict[str, Any]] = Field(default_factory=list)


def load_all_customers_data() -> Dict[str, Any]:
    all_path = DATA_DIR / "all_customers.json"
    if all_path.exists():
        with open(all_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Transaction Risk Investigation Assistant",
        "track_id": "PS06"
    }


@router.get("/customers")
def list_customers():
    data = load_all_customers_data()
    customers = []
    for cid, cinfo in data.items():
        customers.append({
            "customer_id": cid,
            "customer_name": cinfo.get("customer_name", "Unknown"),
            "account_type": cinfo.get("account_type", "Standard"),
            "risk_profile": cinfo.get("risk_profile", "Unknown"),
            "total_transactions": len(cinfo.get("transactions", []))
        })
    return {"customers": customers}


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    data = load_all_customers_data()
    if customer_id not in data:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return data[customer_id]


@router.post("/analyze")
def analyze_transactions(payload: AnalysisRequest):
    txs = payload.transactions
    cid = payload.customer_id or "UNKNOWN"

    # If transactions list is empty but valid customer_id passed, attempt auto-load from sample data
    if not txs and cid in ["CUST-1001", "CUST-1002", "CUST-1003"]:
        all_data = load_all_customers_data()
        if cid in all_data:
            txs = all_data[cid].get("transactions", [])

    # Step 1: Pure-Python Deterministic Risk Engine evaluation
    findings = evaluate_customer_risk(txs, customer_id=cid)

    # Step 2: Grounded LLM Narrative synthesis (with template fallback)
    investigation_result = generate_investigation_report(findings, raw_transactions=txs)

    return {
        "customer_id": cid,
        "attention_needed": findings["attention_needed"],
        "confidence_level": findings["confidence_level"],
        "overall_risk_score": findings["overall_risk_score"],
        "summary_stats": findings["summary_stats"],
        "triggered_rules": findings["triggered_rules"],
        "flagged_transaction_ids": findings["flagged_transaction_ids"],
        "narrative_report": investigation_result["narrative_report"],
        "report_source": investigation_result["source"]
    }
