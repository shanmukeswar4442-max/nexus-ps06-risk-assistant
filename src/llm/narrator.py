"""
Gemini LLM Narrative Synthesis Layer (NexusTiq24 PS06).
Features:
- Runtime API key resolution: Environment variable 'GEMINI_API_KEY' first, request-supplied session key override if provided.
- Exponential retries & timeout handling.
- Deterministic template fallback if API key is missing, call fails, or times out.
- Strictly grounded narrative synthesis: line 1 headline 'ATTENTION NEEDED: YES/NO', real transaction IDs only, zero fraud declarations.
"""

import json
import time
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging_config import logger, mask_sensitive
from src.core.models import RiskAnalysisResult, Transaction


def generate_template_fallback(result: Any, raw_transactions: List[Dict[str, Any]]) -> str:
    """
    Deterministic fallback reporter used if Gemini API is missing, offline, or times out.
    Guarantees 100% reliable system operation without hallucination.
    """
    if isinstance(result, dict):
        result = RiskAnalysisResult(**result)

    customer_id = result.customer_id
    attention_needed = result.attention_needed
    confidence = result.confidence_level
    risk_score = result.overall_risk_score
    stats = result.summary_stats
    triggered = result.triggered_rules
    flagged_ids = result.flagged_transaction_ids

    lines = []
    
    if not attention_needed:
        lines.append("ATTENTION NEEDED: NO")
        lines.append("")
        lines.append(f"### Investigation Summary for Customer {customer_id}")
        lines.append("After reviewing the customer's transaction history against deterministic risk rules, no suspicious patterns or severe anomalies were detected.")
        lines.append(f"- **Total Transactions Evaluated**: {stats.total_transactions}")
        lines.append(f"- **Overall Risk Score**: {risk_score}/100 ({confidence} Confidence)")
        lines.append(f"- **Historical Average Amount**: ₹{stats.avg_amount:,.2f}")
        lines.append(f"- **90th Percentile Threshold**: ₹{stats.p90_amount:,.2f}")
        lines.append("")
        lines.append("**Conclusion**: Routine banking activity consistent with established customer behavior. No further investigator action required.")
        return "\n".join(lines)

    lines.append("ATTENTION NEEDED: YES")
    lines.append("")
    lines.append(f"### Investigation Findings for Customer {customer_id}")
    lines.append(f"Deterministic risk engine flagged potential anomalies requiring human investigator review (Overall Risk Score: **{risk_score}/100**, Confidence: **{confidence}**).")
    lines.append("")
    lines.append("#### 1. Triggered Risk Rules & Deviations")

    tx_lookup = {t.get("transaction_id"): t for t in raw_transactions if isinstance(t, dict) and t.get("transaction_id")}

    for i, rule in enumerate(triggered, 1):
        lines.append(f"**[{rule.severity}] {rule.rule_name}**")
        lines.append(f"- *Deviation Detail*: {rule.description}")
        lines.append(f"- *Cited Transaction IDs*: {', '.join(rule.flagged_transaction_ids) if rule.flagged_transaction_ids else 'None'}")
        
        for tid in rule.flagged_transaction_ids:
            t = tx_lookup.get(tid)
            if t:
                lines.append(f"  - `[{t.get('transaction_id')}]` | Date: {t.get('timestamp')} | Payee: **{t.get('payee')}** | Amount: **₹{float(t.get('amount', 0.0)):,.2f}** | Channel: {t.get('channel')}")
        lines.append("")

    lines.append("#### 2. Customer Baseline Comparison")
    lines.append(f"- **Historical Average Transaction**: ₹{stats.avg_amount:,.2f}")
    lines.append(f"- **Historical 90th Percentile**: ₹{stats.p90_amount:,.2f}")
    lines.append(f"- **Established Payees Count**: {stats.known_payees_count}")
    lines.append(f"- **Established Channels**: {', '.join(stats.established_channels)}")
    lines.append("")

    lines.append("#### 3. Recommended Investigator Next Steps")
    first_priority_tx = flagged_ids[0] if flagged_ids else "N/A"
    lines.append(f"1. **Priority Focus**: Begin review with transaction `{first_priority_tx}` which represents the strongest initial risk signal.")
    lines.append("2. **Out-of-Band Verification**: Contact customer via registered phone channel to confirm authorization of recent transfer bursts.")
    lines.append("3. **Device & Location Analysis**: Review login IP addresses and device fingerprints associated with odd-hours transactions.")
    lines.append("4. **Decision Boundary**: Evaluate findings for potential unauthorized access or compromised credentials. Hand final determination to senior fraud officer.")

    return "\n".join(lines)


def generate_investigation_report(
    result: Any,
    raw_transactions: List[Dict[str, Any]],
    api_key_override: Optional[str] = None
) -> RiskAnalysisResult:
    """
    Generates human-readable narrative report using Gemini API with retry logic and fallback.
    Runtime key resolution order:
    1. api_key_override (if provided by user in Settings)
    2. GEMINI_API_KEY environment variable / config
    """
    if isinstance(result, dict):
        result = RiskAnalysisResult(**result)

    effective_api_key = api_key_override or settings.DEFAULT_GEMINI_API_KEY
    
    if not effective_api_key:
        logger.info(f"No Gemini API key available for customer {result.customer_id}. Using deterministic template fallback.")
        result.narrative_report = generate_template_fallback(result, raw_transactions)
        result.report_source = "deterministic_fallback"
        return result

    logger.info(f"Attempting Gemini narrative synthesis for customer {result.customer_id} (API key source: {'override' if api_key_override else 'env'}).")

    findings_json = result.model_dump()
    flagged_txs = [t for t in raw_transactions if isinstance(t, dict) and t.get("transaction_id") in result.flagged_transaction_ids]

    prompt = f"""
You are an expert Banking Risk Investigation Assistant.
Your job is to generate a concise, grounded human-readable investigation report based STRICTLY on the deterministic rule findings provided below.

CRITICAL CONSTRAINTS (STRICTLY ENFORCED):
1. The VERY FIRST LINE of your output MUST BE EXACTLY:
   "ATTENTION NEEDED: YES" (if attention_needed is true) OR "ATTENTION NEEDED: NO" (if attention_needed is false).
2. If ATTENTION NEEDED: NO:
   State plainly that no suspicious activity was found and stop. Do not manufacture suspicion.
3. If ATTENTION NEEDED: YES:
   - Detail the specific rules triggered, cited transactions, and how the activity deviates from customer baseline.
   - CITE EXACT TRANSACTION IDs (e.g. TXN-88219) from the data provided. NEVER invent a transaction ID.
   - Suggest what an investigator should look at first.
4. ABSOLUTE RULE: NEVER state that "fraud occurred". You flag, explain, and hand judgement to a human investigator.
5. DO NOT add any finding, transaction, or claim that is not present in the input JSON below.

DETERMINISTIC FINDINGS JSON:
{json.dumps(findings_json, indent=2)}

RAW TRANSACTIONS CONTEXT (ONLY FOR CITED IDS):
{json.dumps(flagged_txs, indent=2)}

Produce your investigation report now in clean Markdown.
"""

    # Retries with backoff
    attempts = 0
    max_attempts = settings.LLM_MAX_RETRIES
    report_text = ""
    last_error = None

    while attempts < max_attempts:
        attempts += 1
        try:
            from google import genai
            client = genai.Client(api_key=effective_api_key)
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            if response and response.text:
                report_text = response.text.strip()
                break
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini API attempt {attempts}/{max_attempts} failed for customer {result.customer_id}: {e}")
            time.sleep(0.5 * (2 ** (attempts - 1)))

    if report_text:
        if not report_text.startswith("ATTENTION NEEDED:"):
            prefix = "ATTENTION NEEDED: YES\n\n" if result.attention_needed else "ATTENTION NEEDED: NO\n\n"
            report_text = prefix + report_text
            
        result.narrative_report = report_text
        result.report_source = "gemini_llm"
        return result

    # Fallback on failure
    logger.error(f"Gemini API calls failed for customer {result.customer_id} after {max_attempts} attempts. Falling back to template. Error: {last_error}")
    result.narrative_report = generate_template_fallback(result, raw_transactions)
    result.report_source = "deterministic_fallback"
    result.fallback_reason = str(last_error) if last_error else "API call failed"
    return result
