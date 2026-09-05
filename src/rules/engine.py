"""
Deterministic Risk Rule Engine for Transaction Risk Investigation Assistant (NexusTiq24 PS06).
Pure Python module — contains NO LLM calls or external network dependencies.
"""

from datetime import datetime, timedelta
import math
from typing import Any, Dict, List, Tuple


class RiskRuleEngine:
    def __init__(self, transactions: List[Dict[str, Any]], customer_id: str = "UNKNOWN"):
        self.raw_transactions = transactions or []
        self.customer_id = customer_id
        # Sort transactions chronologically
        self.transactions = sorted(
            [t for t in self.raw_transactions if isinstance(t, dict) and "timestamp" in t],
            key=lambda x: self._parse_iso(x.get("timestamp", ""))
        )

    def _parse_iso(self, ts_str: Any) -> datetime:
        if not isinstance(ts_str, str) or not ts_str:
            return datetime.min
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    def _parse_amount(self, amt: Any) -> float:
        if amt is None:
            return 0.0
        if isinstance(amt, (int, float)):
            return float(amt) if amt > 0 else 0.0
        if isinstance(amt, str):
            try:
                val = float(amt.replace("$", "").replace(",", ""))
                return val if val > 0 else 0.0
            except ValueError:
                return 0.0
        return 0.0

    def compute_summary_stats(self) -> Dict[str, Any]:
        if not self.transactions:
            return {
                "total_transactions": 0,
                "avg_amount": 0.0,
                "median_amount": 0.0,
                "p90_amount": 0.0,
                "max_amount": 0.0,
                "known_payees_count": 0,
                "established_channels": []
            }

        # Exclude income/deposits for spending statistics
        outgoing = [
            self._parse_amount(t.get("amount")) for t in self.transactions
            if t.get("category") != "Income" and self._parse_amount(t.get("amount")) > 0
        ]
        
        if not outgoing:
            outgoing = [self._parse_amount(t.get("amount")) for t in self.transactions if self._parse_amount(t.get("amount")) > 0]

        amounts_sorted = sorted(outgoing) if outgoing else [0.0]
        n = len(amounts_sorted)

        avg_val = sum(amounts_sorted) / n if n > 0 else 0.0
        max_val = max(amounts_sorted) if n > 0 else 0.0
        median_val = amounts_sorted[n // 2] if n > 0 else 0.0
        
        # 90th percentile
        p90_idx = int(0.90 * n)
        p90_idx = min(p90_idx, n - 1) if n > 0 else 0
        p90_val = amounts_sorted[p90_idx] if n > 0 else 0.0

        payees = set(t.get("payee") for t in self.transactions if t.get("payee"))
        channels = list(set(t.get("channel") for t in self.transactions if t.get("channel")))

        return {
            "total_transactions": len(self.transactions),
            "avg_amount": round(avg_val, 2),
            "median_amount": round(median_val, 2),
            "p90_amount": round(p90_val, 2),
            "max_amount": round(max_val, 2),
            "known_payees_count": len(payees),
            "established_channels": channels
        }

    def evaluate_rules(self) -> Dict[str, Any]:
        if not self.transactions:
            return {
                "customer_id": self.customer_id,
                "attention_needed": False,
                "confidence_level": "NONE",
                "overall_risk_score": 0,
                "summary_stats": self.compute_summary_stats(),
                "triggered_rules": [],
                "flagged_transaction_ids": []
            }

        triggered_rules = []
        flagged_tx_ids = set()
        stats = self.compute_summary_stats()

        # Split history into baseline (first 75%) and evaluation window (last 25%) if history > 10 txns
        # Otherwise compute baseline across full history excluding individual outlier checks
        tx_count = len(self.transactions)
        
        # Rule 1: Unusually Large Transfer
        rule_large = self._check_unusually_large_transfer(stats)
        if rule_large:
            triggered_rules.append(rule_large)
            flagged_tx_ids.update(rule_large["flagged_transaction_ids"])

        # Rule 2: Unfamiliar Payee Burst
        rule_burst = self._check_payee_burst()
        if rule_burst:
            triggered_rules.append(rule_burst)
            flagged_tx_ids.update(rule_burst["flagged_transaction_ids"])

        # Rule 3: Odd-Hours Activity
        rule_odd = self._check_odd_hours()
        if rule_odd:
            triggered_rules.append(rule_odd)
            flagged_tx_ids.update(rule_odd["flagged_transaction_ids"])

        # Rule 4: Established Pattern Break
        rule_pattern = self._check_pattern_break(stats)
        if rule_pattern:
            triggered_rules.append(rule_pattern)
            flagged_tx_ids.update(rule_pattern["flagged_transaction_ids"])

        # Compute overall risk score
        score = 0
        for r in triggered_rules:
            sev = r.get("severity", "LOW")
            if sev == "HIGH":
                score += 35
            elif sev == "MEDIUM":
                score += 20
            elif sev == "LOW":
                score += 10

        overall_risk_score = min(score, 100)

        # High or Medium severity rule triggers attention_needed
        has_high_or_med = any(r.get("severity") in ["HIGH", "MEDIUM"] for r in triggered_rules)
        attention_needed = has_high_or_med and (overall_risk_score >= 30)

        if overall_risk_score >= 60:
            confidence = "HIGH"
        elif overall_risk_score >= 30:
            confidence = "MEDIUM"
        elif overall_risk_score > 0:
            confidence = "LOW"
        else:
            confidence = "NONE"

        return {
            "customer_id": self.customer_id,
            "attention_needed": attention_needed,
            "confidence_level": confidence,
            "overall_risk_score": overall_risk_score,
            "summary_stats": stats,
            "triggered_rules": triggered_rules,
            "flagged_transaction_ids": sorted(list(flagged_tx_ids))
        }

    def _check_unusually_large_transfer(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        p90 = stats.get("p90_amount", 0.0)
        avg = stats.get("avg_amount", 0.0)

        # Find historical baseline excluding the top 10% highest transactions to avoid baseline pollution
        outgoing_amounts = [
            t.get("amount", 0.0) for t in self.transactions
            if t.get("category") != "Income" and isinstance(t.get("amount"), (int, float))
        ]
        
        if len(outgoing_amounts) < 4:
            return None

        # Exclude extreme top values to establish clean historical baseline
        sorted_amounts = sorted(outgoing_amounts)
        baseline_cutoff = int(len(sorted_amounts) * 0.85)
        baseline_amounts = sorted_amounts[:max(baseline_cutoff, 3)]
        
        baseline_max = max(baseline_amounts)
        baseline_p90 = baseline_amounts[min(int(len(baseline_amounts) * 0.90), len(baseline_amounts) - 1)]

        flagged_txs = []
        max_ratio = 0.0

        for t in self.transactions:
            if t.get("category") == "Income":
                continue
            amt = t.get("amount", 0.0)
            if not isinstance(amt, (int, float)):
                continue

            # Flag if transaction is > 3.0x baseline p90 AND > 2.5x baseline max AND > $1500
            ratio = amt / (baseline_p90 + 1e-5)
            if amt > 2.5 * baseline_max and ratio >= 3.0 and amt >= 1500.0:
                flagged_txs.append(t)
                if ratio > max_ratio:
                    max_ratio = ratio

        if not flagged_txs:
            return None

        flagged_ids = [t["transaction_id"] for t in flagged_txs]
        largest_amt = max(t["amount"] for t in flagged_txs)

        return {
            "rule_id": "RULE_LARGE_TRANSFER",
            "rule_name": "Unusually Large Transfer",
            "severity": "HIGH",
            "description": f"Transfer of ${largest_amt:,.2f} is {max_ratio:.1f}x higher than customer's baseline 90th percentile (${baseline_p90:,.2f}).",
            "flagged_transaction_ids": flagged_ids,
            "evidence": {
                "flagged_amount": largest_amt,
                "baseline_p90": baseline_p90,
                "baseline_max": baseline_max,
                "ratio_vs_baseline": round(max_ratio, 2)
            }
        }

    def _check_payee_burst(self) -> Dict[str, Any]:
        # Track first appearance of each payee
        payee_first_seen = {}
        payee_txs = {}

        for t in self.transactions:
            payee = t.get("payee")
            if not payee or t.get("category") == "Income":
                continue
            
            dt = self._parse_iso(t.get("timestamp", ""))
            if payee not in payee_first_seen:
                payee_first_seen[payee] = dt
                payee_txs[payee] = []
            payee_txs[payee].append((dt, t))

        if not self.transactions:
            return None

        latest_time = self._parse_iso(self.transactions[-1].get("timestamp", ""))
        flagged_txs = []
        burst_payee = None
        burst_total = 0.0

        for payee, tx_list in payee_txs.items():
            first_dt = payee_first_seen[payee]
            # Check if payee was first seen within the last 14 days of history
            days_since_first = (latest_time - first_dt).total_seconds() / 86400.0
            is_new_payee = days_since_first <= 14.0 or len(tx_list) <= 3

            # Check rolling windows for rapid burst to new/unfamiliar payee
            if is_new_payee and len(tx_list) >= 2:
                for i in range(len(tx_list)):
                    for j in range(i + 1, len(tx_list)):
                        w_hours = (tx_list[j][0] - tx_list[i][0]).total_seconds() / 3600.0
                        burst_sub = tx_list[i:j+1]
                        burst_sum = sum(t[1].get("amount", 0.0) for t in burst_sub)
                        
                        # Trigger if 2+ transactions in 48 hours OR total sum > $2000 to new payee in 72 hours
                        if w_hours <= 48.0 or (w_hours <= 72.0 and burst_sum >= 2000.0):
                            for _, t in burst_sub:
                                flagged_txs.append(t)
                            burst_payee = payee
                            burst_total = burst_sum
                            break
                    if flagged_txs:
                        break
            if flagged_txs:
                break

        if not flagged_txs:
            return None

        flagged_ids = [t["transaction_id"] for t in flagged_txs]
        return {
            "rule_id": "RULE_PAYEE_BURST",
            "rule_name": "Unfamiliar Payee Burst",
            "severity": "HIGH",
            "description": f"Burst of {len(flagged_txs)} rapid payments totaling ${burst_total:,.2f} sent to unfamiliar payee '{burst_payee}'.",
            "flagged_transaction_ids": flagged_ids,
            "evidence": {
                "payee": burst_payee,
                "transaction_count": len(flagged_txs),
                "total_burst_amount": burst_total
            }
        }

    def _check_odd_hours(self) -> Dict[str, Any]:
        flagged_txs = []
        for t in self.transactions:
            dt = self._parse_iso(t.get("timestamp", ""))
            # Odd hours defined as 01:00 AM to 04:59 AM (hours 1, 2, 3, 4)
            if dt.hour in [1, 2, 3, 4]:
                amt = t.get("amount", 0.0)
                chan = t.get("channel", "")
                # Flag if amount is substantial (> $500) or high risk channel (Crypto, P2P, Wire)
                if amt >= 500.0 or chan in ["Wire Transfer", "P2P Payment", "Crypto", "Crypto/Investments"]:
                    flagged_txs.append(t)

        if not flagged_txs:
            return None

        flagged_ids = [t["transaction_id"] for t in flagged_txs]
        total_odd_amt = sum(t.get("amount", 0.0) for t in flagged_txs)
        hours_list = [self._parse_iso(t.get("timestamp", "")).strftime("%H:%M") for t in flagged_txs]

        return {
            "rule_id": "RULE_ODD_HOURS",
            "rule_name": "Odd-Hours Activity",
            "severity": "MEDIUM",
            "description": f"Executed {len(flagged_txs)} high-value/risk transactions during odd hours (01:00-05:00 AM) at times: {', '.join(hours_list)}.",
            "flagged_transaction_ids": flagged_ids,
            "evidence": {
                "transaction_count": len(flagged_txs),
                "total_amount": total_odd_amt,
                "times": hours_list
            }
        }

    def _check_pattern_break(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        flagged_txs = []
        reason = ""

        # Check for rapid velocity burst: >= 3 transactions in 30 minutes
        for i in range(len(self.transactions) - 2):
            t1 = self.transactions[i]
            t3 = self.transactions[i + 2]
            dt1 = self._parse_iso(t1.get("timestamp", ""))
            dt3 = self._parse_iso(t3.get("timestamp", ""))
            
            if (dt3 - dt1).total_seconds() <= 1800.0 and t1.get("category") != "Income":
                # Check if total in burst is significant
                burst_txs = self.transactions[i:i+3]
                burst_sum = sum(t.get("amount", 0.0) for t in burst_txs)
                if burst_sum >= 1500.0:
                    flagged_txs.extend(burst_txs)
                    reason = f"High velocity burst of 3 transactions within 30 minutes totaling ${burst_sum:,.2f}"
                    break

        if not flagged_txs:
            # Check for sudden uncharacteristic channel usage (e.g. Wire Transfer for customer with no wire history)
            # Find channels used in first 80% of history
            n_hist = max(int(len(self.transactions) * 0.8), 5)
            historical_channels = set(t.get("channel") for t in self.transactions[:n_hist] if t.get("channel"))
            
            recent_txs = self.transactions[n_hist:]
            for t in recent_txs:
                chan = t.get("channel")
                amt = t.get("amount", 0.0)
                if chan in ["Wire Transfer", "Crypto", "P2P Payment"] and chan not in historical_channels and amt >= 2000.0:
                    flagged_txs.append(t)
                    reason = f"Sudden use of high-risk channel '{chan}' for ${amt:,.2f} with no historical precedent"
                    break

        if not flagged_txs:
            return None

        # Deduplicate transaction IDs
        unique_flagged = []
        seen_ids = set()
        for t in flagged_txs:
            tid = t.get("transaction_id")
            if tid and tid not in seen_ids:
                seen_ids.add(tid)
                unique_flagged.append(t)

        flagged_ids = [t["transaction_id"] for t in unique_flagged]

        return {
            "rule_id": "RULE_PATTERN_BREAK",
            "rule_name": "Established Pattern Break",
            "severity": "MEDIUM",
            "description": f"Customer pattern break detected: {reason}.",
            "flagged_transaction_ids": flagged_ids,
            "evidence": {
                "reason": reason,
                "transaction_ids": flagged_ids
            }
        }


def evaluate_customer_risk(transactions: List[Dict[str, Any]], customer_id: str = "UNKNOWN") -> Dict[str, Any]:
    engine = RiskRuleEngine(transactions, customer_id)
    return engine.evaluate_rules()
