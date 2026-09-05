"""
Production FastAPI Routes for Transaction Risk Investigation Assistant (NexusTiq24 PS06).
"""

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from src.core.config import settings
from src.core.logging_config import logger
from src.core.models import (
    AnalysisRequest,
    APIKeySettingRequest,
    APIKeyStatusResponse,
    ExportReportRequest,
    RiskAnalysisResult,
)
from src.rules.engine import evaluate_customer_risk
from src.llm.narrator import generate_investigation_report
from src.api.dependencies import session_store

router = APIRouter(prefix="/api", tags=["Investigation API"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Cache for analyzed status chips
_analyzed_status_cache: Dict[str, str] = {}


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
        "service": settings.APP_NAME,
        "track_id": settings.TRACK_ID
    }


@router.get("/customers")
def list_customers():
    data = load_all_customers_data()
    customers = []
    for cid, cinfo in data.items():
        txs = cinfo.get("transactions", [])
        
        # Status chip calculation
        status = _analyzed_status_cache.get(cid, "Not Analyzed")
        if status == "Not Analyzed":
            # Initial auto-run to populate chips
            res = evaluate_customer_risk(txs, cid)
            status = "Needs Attention" if res.attention_needed else "Clean"
            _analyzed_status_cache[cid] = status

        customers.append({
            "customer_id": cid,
            "customer_name": cinfo.get("customer_name", "Unknown"),
            "account_type": cinfo.get("account_type", "Standard"),
            "risk_profile": cinfo.get("risk_profile", "Unknown"),
            "total_transactions": len(txs),
            "currency": cinfo.get("currency", "INR"),
            "status_chip": status
        })
    return {"customers": customers}


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    data = load_all_customers_data()
    if customer_id not in data:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return data[customer_id]


@router.post("/analyze", response_model=RiskAnalysisResult)
def analyze_transactions(payload: AnalysisRequest):
    txs = payload.transactions
    cid = payload.customer_id or "CUSTOM"

    if not txs and cid in ["CUST-1001", "CUST-1002", "CUST-1003"]:
        all_data = load_all_customers_data()
        if cid in all_data:
            txs = all_data[cid].get("transactions", [])

    if not txs and cid not in ["CUST-1001", "CUST-1002", "CUST-1003"]:
        logger.warning(f"Analysis requested with empty transaction history for customer {cid}")

    # 1. Deterministic Rule Engine
    findings = evaluate_customer_risk(txs, customer_id=cid)

    # Update status chip
    _analyzed_status_cache[cid] = "Needs Attention" if findings.attention_needed else "Clean"

    # 2. Runtime API key resolution (request override -> session override -> env default)
    effective_key = payload.api_key_override or session_store.get_key() or settings.DEFAULT_GEMINI_API_KEY

    # 3. Grounded LLM Narrative synthesis (or template fallback)
    result = generate_investigation_report(findings, raw_transactions=txs, api_key_override=effective_key)

    return result


@router.post("/upload")
async def upload_transaction_history(file: UploadFile = File(...)):
    filename = file.filename or ""
    content = await file.read()
    
    txs: List[Dict[str, Any]] = []
    customer_id = "UPLOADED-CUST"

    try:
        if filename.endswith(".json") or content.strip().startswith(b"{") or content.strip().startswith(b"["):
            parsed = json.loads(content.decode("utf-8"))
            if isinstance(parsed, list):
                txs = parsed
            elif isinstance(parsed, dict):
                customer_id = parsed.get("customer_id", "UPLOADED-CUST")
                txs = parsed.get("transactions", [])
        elif filename.endswith(".csv") or b"," in content:
            decoded = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
            for row in reader:
                txs.append(dict(row))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload JSON or CSV.")
    except Exception as e:
        logger.error(f"Failed to parse uploaded transaction file: {e}")
        raise HTTPException(status_code=422, detail=f"Malformed file upload: {str(e)}")

    if not txs:
        raise HTTPException(status_code=400, detail="Uploaded file contained no transaction records.")

    # Auto run analysis pipeline
    findings = evaluate_customer_risk(txs, customer_id=customer_id)
    effective_key = session_store.get_key() or settings.DEFAULT_GEMINI_API_KEY
    result = generate_investigation_report(findings, raw_transactions=txs, api_key_override=effective_key)

    return {
        "customer_id": customer_id,
        "total_parsed": len(txs),
        "analysis_result": result.model_dump()
    }


@router.post("/export")
def export_report(payload: ExportReportRequest):
    if not payload.report_content:
        raise HTTPException(status_code=400, detail="Report content is empty")

    if payload.format == "html":
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Investigation Report — {payload.customer_id}</title>
  <style>
    body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; color: #111; }}
    h3 {{ color: #0052cc; border-bottom: 2px solid #0052cc; padding-bottom: 5px; }}
    code {{ background: #f4f5f7; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
  </style>
</head>
<body>
  <pre style="font-family: inherit; whitespace: pre-wrap;">{payload.report_content}</pre>
</body>
</html>"""
        return PlainTextResponse(content=html_content, media_type="text/html")
    
    # Default Markdown export
    return PlainTextResponse(content=payload.report_content, media_type="text/markdown")


@router.get("/settings/key-status", response_model=APIKeyStatusResponse)
def get_api_key_status():
    session_key = session_store.get_key()
    env_key = settings.DEFAULT_GEMINI_API_KEY
    
    if session_key:
        return APIKeyStatusResponse(active=True, source="session")
    elif env_key:
        return APIKeyStatusResponse(active=True, source="env")
    else:
        return APIKeyStatusResponse(active=False, source="none")


@router.post("/settings/set-key")
def set_session_api_key(payload: APIKeySettingRequest):
    key = payload.api_key.strip()
    if not key:
        session_store.clear_key()
        logger.info("Cleared session API key override.")
        return {"status": "cleared", "active": bool(settings.DEFAULT_GEMINI_API_KEY)}

    session_store.set_key(key)
    logger.info("Session API key override set in memory successfully.")
    return {"status": "set", "active": True, "source": "session"}
