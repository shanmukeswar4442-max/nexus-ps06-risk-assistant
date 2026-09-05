"""
Pure-Python Deterministic Risk Rule Engine (NexusTiq24 PS06).
Contains NO LLM calls or external network dependencies.
Evaluates 4 core risk rules:
1. RULE_LARGE_TRANSFER: Unusually large transfer relative to baseline 90th percentile & max.
2. RULE_PAYEE_BURST: Bursts of rapid payments to newly added / unfamiliar payees.
3. RULE_ODD_HOURS: High-value or high-risk channel transactions between 01:00 AM - 05:00 AM.
4. RULE_PATTERN_BREAK: Velocity bursts or unprecedented high-risk channel usage.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from src.core.config import settings
from src.core.logging_config import logger
from src.core.models import CustomerSummaryStats, RiskAnalysisResult, RuleFinding, Transaction


class RiskRuleEngine:
    def __init__(self, raw_transactions: List[Dict[str, Any]], customer_id: str = "UNKNOWN"):
        self.customer_id = customer_id
        
        # Parse into typed Transaction objects, skipping unparseable rows
        parsed = []
        for t in raw_transactions:
            if isinstance(t, dict) and "timestamp" in t:
                try:
                    parsed.append(Transaction(**t))
                except Exception as e:
                    logger.warning(f"Skipping malformed row for customer {customer_id}: {e}")

        # Sort transactions chronologically
        self.transactions = sorted(parsed, key=lambda x: self._parse_iso(x.timestamp))

    def _parse_iso(self, ts_str: Any) -> datetime:
        if not isinstance(ts_str, str) or not ts_str:
            return datetime.min
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    def compute_summary_stats(self) -> CustomerSummaryStats:
        if not self.transactions:
            return CustomerSummaryStats(currency=settings.DEFAULT_CURRENCY)

        outgoing = [
            t.amount for t in self.transactions
            if t.category != "Income" and t.amount > 0
        ]
        if not outgoing:
            outgoing = [t.amount for t in self.transactions if t.amount > 0]

        sorted_amt = sorted(outgoing) if outgoing else [0.0]
        n = len(sorted_amt)

        avg_val = sum(sorted_amt) / n if n > 0 else 0.0
        max_val = max(sorted_amt) if n > 0 else 0.0
        median_val = sorted_amt[n // 2] if n > 0 else 0.0
        
        p90_idx = int(0.90 * n)
        p90_idx = min(p90_idx, n - 1) if n > 0 else 0
        p90_val = sorted_amt[p90_idx] if n > 0 else 0.0

        payees = set(t.payee for t in self.transactions if t.payee)
        channels = list(set(t.channel for t in self.transactions if t.channel))

        return CustomerSummaryStats(
            total_transactions=len(self.transactions),
            avg_amount=round(avg_val, 2),
            median_amount=round(median_val, 2),
            p90_amount=round(p90_val, 2),
            max_amount=round(max_val, 2),
            known_payees_count=len(payees),
            established_channels=channels,
            currency=settings.DEFAULT_CURRENCY
        )

    def evaluate_rules(self) -> RiskAnalysisResult:
        stats = self.compute_summary_stats()

        if not self.transactions:
            return RiskAnalysisResult(
                customer_id=self.customer_id,
                attention_needed=False,
                confidence_level="NONE",
                overall_risk_score=0,
                summary_stats=stats,
                triggered_rules=[],
                flagged_transaction_ids=[],
                report_source="deterministic_fallback"
            )

        triggered: List[RuleFinding] = []
        flagged_ids: Set[str] = set()

        # Rule 1: Large Transfer
        r1 = self._check_large_transfer(stats)
        if r1:
            triggered.append(r1)
            flagged_ids.update(r1.flagged_transaction_ids)

        # Rule 2: Payee Burst
        r2 = self._check_payee_burst()
        if r2:
            triggered.append(r2)
            flagged_ids.update(r2.flagged_transaction_ids)

        # Rule 3: Odd Hours
        r3 = self._check_odd_hours()
        if r3:
            triggered.append(r3)
            flagged_ids.update(r3.flagged_transaction_ids)

        # Rule 4: Pattern Break
        r4 = self._check_pattern_break(stats)
        if r4:
            triggered.append(r4)
            flagged_ids.update(r4.flagged_transaction_ids)

        # Compute Score
        score = 0
        for r in triggered:
            if r.severity == "HIGH":
                score += 35
            elif r.severity == "MEDIUM":
                score += 20
            elif r.severity == "LOW":
                score += 10

        overall_score = min(score, 100)
        has_high_or_med = any(r.severity in ["HIGH", "MEDIUM"] for r in triggered)
        attention_needed = has_high_or_med and (overall_score >= 30)

        if overall_score >= 60:
            confidence = "HIGH"
        elif overall_score >= 30:
            confidence = "MEDIUM"
        elif overall_score > 0:
            confidence = "LOW"
        else:
            confidence = "NONE"

        return RiskAnalysisResult(
            customer_id=self.customer_id,
            attention_needed=attention_needed,
            confidence_level=confidence,
            overall_risk_score=overall_score,
            summary_stats=stats,
            triggered_rules=triggered,
            flagged_transaction_ids=sorted(list(flagged_ids)),
            report_source="deterministic_fallback"
        )

    def _check_large_transfer(self, stats: CustomerSummaryStats) -> Optional[RuleFinding]:
        outgoing = [t.amount for t in self.transactions if t.category != "Income" and t.amount > 0]
        if len(outgoing) < 4:
            return None

        sorted_amt = sorted(outgoing)
        baseline_cutoff = int(len(sorted_amt) * 0.85)
        baseline_amounts = sorted_amt[:max(baseline_cutoff, 3)]
        
        baseline_max = max(baseline_amounts)
        baseline_p90 = baseline_amounts[min(int(len(baseline_amounts) * 0.90), len(baseline_amounts) - 1)]

        flagged = []
        max_ratio = 0.0

        for t in self.transactions:
            if t.category == "Income":
                continue
            amt = t.amount
            ratio = amt / (baseline_p90 + 1e-5)
            if amt > 2.5 * baseline_max and ratio >= settings.LARGE_TRANSFER_P90_MULTIPLIER and amt >= settings.LARGE_TRANSFER_MIN_AMOUNT:
                flagged.append(t)
                if ratio > max_ratio:
                    max_ratio = ratio

        if not flagged:
            return None

        flagged_ids = [t.transaction_id for t in flagged]
        largest_amt = max(t.amount for t in flagged)

        return RuleFinding(
            rule_id="RULE_LARGE_TRANSFER",
            rule_name="Unusually Large Transfer",
            severity="HIGH",
            description=f"Transfer of ₹{largest_amt:,.2f} is {max_ratio:.1f}x higher than customer's baseline 90th percentile (₹{baseline_p90:,.2f}).",
            flagged_transaction_ids=flagged_ids,
            evidence={
                "flagged_amount": largest_amt,
                "baseline_p90": baseline_p90,
                "baseline_max": baseline_max,
                "ratio_vs_baseline": round(max_ratio, 2)
            }
        )

    def _check_payee_burst(self) -> Optional[RuleFinding]:
        payee_first_seen: Dict[str, datetime] = {}
        payee_txs: Dict[str, List[Tuple[datetime, Transaction]]] = {}

        for t in self.transactions:
            payee = t.payee
            if not payee or t.category == "Income":
                continue
            
            dt = self._parse_iso(t.timestamp)
            if payee not in payee_first_seen:
                payee_first_seen[payee] = dt
                payee_txs[payee] = []
            payee_txs[payee].append((dt, t))

        if not self.transactions:
            return None

        latest_time = self._parse_iso(self.transactions[-1].timestamp)
        flagged: List[Transaction] = []
        burst_payee = None
        burst_total = 0.0

        for payee, tx_list in payee_txs.items():
            first_dt = payee_first_seen[payee]
            days_since_first = (latest_time - first_dt).total_seconds() / 86400.0
            is_new_payee = days_since_first <= 14.0 or len(tx_list) <= 3

            if is_new_payee and len(tx_list) >= 2:
                for i in range(len(tx_list)):
                    for j in range(i + 1, len(tx_list)):
                        w_hours = (tx_list[j][0] - tx_list[i][0]).total_seconds() / 3600.0
                        burst_sub = tx_list[i:j+1]
                        burst_sum = sum(t[1].amount for t in burst_sub)
                        
                        if w_hours <= settings.PAYEE_BURST_WINDOW_HOURS or (w_hours <= 72.0 and burst_sum >= settings.PAYEE_BURST_MIN_TOTAL):
                            for _, t in burst_sub:
                                flagged.append(t)
                            burst_payee = payee
                            burst_total = burst_sum
                            break
                    if flagged:
                        break
            if flagged:
                break

        if not flagged:
            return None

        flagged_ids = [t.transaction_id for t in flagged]
        return RuleFinding(
            rule_id="RULE_PAYEE_BURST",
            rule_name="Unfamiliar Payee Burst",
            severity="HIGH",
            description=f"Burst of {len(flagged)} rapid payments totaling ₹{burst_total:,.2f} sent to unfamiliar payee '{burst_payee}'.",
            flagged_transaction_ids=flagged_ids,
            evidence={
                "payee": burst_payee,
                "transaction_count": len(flagged),
                "total_burst_amount": burst_total
            }
        )

    def _check_odd_hours(self) -> Optional[RuleFinding]:
        flagged = []
        for t in self.transactions:
            dt = self._parse_iso(t.timestamp)
            if dt.hour in [settings.ODD_HOURS_START, 2, 3, settings.ODD_HOURS_END]:
                amt = t.amount
                chan = t.channel or ""
                if amt >= settings.ODD_HOURS_MIN_AMOUNT or chan in ["Wire Transfer", "IMPS", "RTGS", "UPI", "Crypto", "P2P Payment"]:
                    flagged.append(t)

        if not flagged:
            return None

        flagged_ids = [t.transaction_id for t in flagged]
        total_odd_amt = sum(t.amount for t in flagged)
        hours_list = [self._parse_iso(t.timestamp).strftime("%H:%M") for t in flagged]

        return RuleFinding(
            rule_id="RULE_ODD_HOURS",
            rule_name="Odd-Hours Activity",
            severity="MEDIUM",
            description=f"Executed {len(flagged)} high-value/risk transactions during odd hours (01:00-05:00 AM) at times: {', '.join(hours_list)}.",
            flagged_transaction_ids=flagged_ids,
            evidence={
                "transaction_count": len(flagged),
                "total_amount": total_odd_amt,
                "times": hours_list
            }
        )

    def _check_pattern_break(self, stats: CustomerSummaryStats) -> Optional[RuleFinding]:
        flagged = []
        reason = ""

        for i in range(len(self.transactions) - 2):
            t1 = self.transactions[i]
            t3 = self.transactions[i + 2]
            dt1 = self._parse_iso(t1.timestamp)
            dt3 = self._parse_iso(t3.timestamp)
            
            if (dt3 - dt1).total_seconds() <= 1800.0 and t1.category != "Income":
                burst_txs = self.transactions[i:i+3]
                burst_sum = sum(t.amount for t in burst_txs)
                if burst_sum >= settings.VELOCITY_BURST_MIN_AMOUNT:
                    flagged.extend(burst_txs)
                    reason = f"High velocity burst of 3 transactions within 30 minutes totaling ₹{burst_sum:,.2f}"
                    break

        if not flagged:
            n_hist = max(int(len(self.transactions) * 0.8), 5)
            historical_channels = set(t.channel for t in self.transactions[:n_hist] if t.channel)
            
            recent_txs = self.transactions[n_hist:]
            for t in recent_txs:
                chan = t.channel or ""
                amt = t.amount
                if chan in ["Wire Transfer", "Crypto", "IMPS", "RTGS"] and chan not in historical_channels and amt >= settings.PAYEE_BURST_MIN_TOTAL:
                    flagged.append(t)
                    reason = f"Sudden use of high-risk channel '{chan}' for ₹{amt:,.2f} with no historical precedent"
                    break

        if not flagged:
            return None

        unique_flagged = []
        seen_ids = set()
        for t in flagged:
            tid = t.transaction_id
            if tid and tid not in seen_ids:
                seen_ids.add(tid)
                unique_flagged.append(t)

        flagged_ids = [t.transaction_id for t in unique_flagged]

        return RuleFinding(
            rule_id="RULE_PATTERN_BREAK",
            rule_name="Established Pattern Break",
            severity="MEDIUM",
            description=f"Customer pattern break detected: {reason}.",
            flagged_transaction_ids=flagged_ids,
            evidence={
                "reason": reason,
                "transaction_ids": flagged_ids
            }
        )


def evaluate_customer_risk(raw_transactions: List[Dict[str, Any]], customer_id: str = "UNKNOWN") -> RiskAnalysisResult:
    engine = RiskRuleEngine(raw_transactions, customer_id)
    return engine.evaluate_rules()
