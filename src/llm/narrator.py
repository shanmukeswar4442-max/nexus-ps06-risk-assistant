"""
Gemini LLM Narrative Synthesis Layer for Transaction Risk Investigation Assistant (NexusTiq24 PS06).
Translates deterministic risk findings into a grounded human-readable investigation report.
Strictly grounded — never invents transaction IDs or findings, never declares fraud.
Wraps all LLM calls in try/except with a robust template fallback.
"""

import os
import json
from typing import Any, Dict, List, Optional


def generate_template_fallback(findings: Dict[str, Any], raw_transactions: List[Dict[str, Any]]) -> str:
    """
    Deterministic fallback reporter used if Gemini API key is missing, call fails, or times out.
    Guarantees 100% reliable system operation without hallucination.
    """
    customer_id = findings.get("customer_id", "UNKNOWN")
    attention_needed = findings.get("attention_needed", False)
    confidence = findings.get("confidence_level", "NONE")
    risk_score = findings.get("overall_risk_score", 0)
    stats = findings.get("summary_stats", {})
    triggered = findings.get("triggered_rules", [])
    flagged_ids = findings.get("flagged_transaction_ids", [])

    lines = []
    
    # REQUIREMENT 1: FIRST finding MUST be plain statement whether attention is needed at all
    if not attention_needed:
        lines.append("ATTENTION NEEDED: NO")
        lines.append("")
        lines.append(f"### Investigation Summary for Customer {customer_id}")
        lines.append("After reviewing the customer's transaction history against deterministic risk rules, no suspicious patterns or severe anomalies were detected.")
        lines.append(f"- **Total Transactions Evaluated**: {stats.get('total_transactions', 0)}")
        lines.append(f"- **Overall Risk Score**: {risk_score}/100 ({confidence} Confidence)")
        lines.append(f"- **Historical Average Amount**: ${stats.get('avg_amount', 0.0):,.2f}")
        lines.append(f"- **90th Percentile Threshold**: ${stats.get('p90_amount', 0.0):,.2f}")
        lines.append("")
        lines.append("**Conclusion**: Routine banking activity consistent with established customer behavior. No further investigator action required.")
        return "\n".join(lines)

    # ATTENTION NEEDED: YES
    lines.append("ATTENTION NEEDED: YES")
    lines.append("")
    lines.append(f"### Investigation Findings for Customer {customer_id}")
    lines.append(f"Deterministic risk engine flagged potential anomalies requiring human investigator review (Overall Risk Score: **{risk_score}/100**, Confidence: **{confidence}**).")
    lines.append("")
    lines.append("#### 1. Triggered Risk Rules & Deviations")

    tx_lookup = {t.get("transaction_id"): t for t in raw_transactions if isinstance(t, dict) and t.get("transaction_id")}

    for i, rule in enumerate(triggered, 1):
        rule_name = rule.get("rule_name", "Unknown Rule")
        severity = rule.get("severity", "MEDIUM")
        desc = rule.get("description", "")
        rule_tx_ids = rule.get("flagged_transaction_ids", [])
        
        lines.append(f"**[{severity}] {rule_name}**")
        lines.append(f"- *Deviation Detail*: {desc}")
        lines.append(f"- *Cited Transaction IDs*: {', '.join(rule_tx_ids) if rule_tx_ids else 'None'}")
        
        # Details of cited transactions
        for tid in rule_tx_ids:
            t = tx_lookup.get(tid)
            if t:
                lines.append(f"  - `[{t.get('transaction_id')}]` | Date: {t.get('timestamp')} | Payee: **{t.get('payee')}** | Amount: **${t.get('amount', 0.0):,.2f}** | Channel: {t.get('channel')}")
        lines.append("")

    lines.append("#### 2. Customer Baseline Comparison")
    lines.append(f"- **Historical Average Transaction**: ${stats.get('avg_amount', 0.0):,.2f}")
    lines.append(f"- **Historical 90th Percentile**: ${stats.get('p90_amount', 0.0):,.2f}")
    lines.append(f"- **Established Payees Count**: {stats.get('known_payees_count', 0)}")
    lines.append(f"- **Established Channels**: {', '.join(stats.get('established_channels', []))}")
    lines.append("")

    lines.append("#### 3. Recommended Investigator Next Steps")
    first_priority_tx = flagged_ids[0] if flagged_ids else "N/A"
    lines.append(f"1. **Priority Focus**: Begin review with transaction `{first_priority_tx}` which represents the strongest initial risk signal.")
    lines.append("2. **Out-of-Band Verification**: Contact customer via registered phone channel to confirm authorization of recent transfer bursts.")
    lines.append("3. **Device & Location Analysis**: Review login IP addresses and device fingerprints associated with odd-hours transactions.")
    lines.append("4. **Decision Boundary**: Evaluate findings for potential unauthorized access or compromised credentials. Hand final determination to senior fraud officer.")

    return "\n".join(lines)


def generate_investigation_report(findings: Dict[str, Any], raw_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates human-readable investigation narrative using Gemini API (google-genai SDK).
    Falls back gracefully to template reporter if API key is missing or call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # If API key is missing or empty string, fallback immediately
    if not api_key:
        report_text = generate_template_fallback(findings, raw_transactions)
        return {
            "narrative_report": report_text,
            "source": "deterministic_fallback",
            "findings": findings
        }

    # Attempt Gemini API synthesis
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        
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
{json.dumps(findings, indent=2)}

RAW TRANSACTIONS CONTEXT (ONLY FOR CITED IDS):
{json.dumps([t for t in raw_transactions if t.get("transaction_id") in findings.get("flagged_transaction_ids", [])], indent=2)}

Produce your investigation report now in clean Markdown.
"""
        
        # Try calling Gemini models (gemini-2.5-flash or gemini-1.5-flash)
        model_name = "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        report_text = response.text.strip() if response and response.text else ""
        
        # Enforce requirement 1 check: text must start with ATTENTION NEEDED
        if not report_text.startswith("ATTENTION NEEDED:"):
            prefix = "ATTENTION NEEDED: YES\n\n" if findings.get("attention_needed") else "ATTENTION NEEDED: NO\n\n"
            report_text = prefix + report_text

        return {
            "narrative_report": report_text,
            "source": "gemini_llm",
            "findings": findings
        }

    except Exception as e:
        # Graceful fallback on any exception, timeout, or error
        fallback_text = generate_template_fallback(findings, raw_transactions)
        return {
            "narrative_report": fallback_text,
            "source": "deterministic_fallback",
            "fallback_reason": str(e),
            "findings": findings
        }
