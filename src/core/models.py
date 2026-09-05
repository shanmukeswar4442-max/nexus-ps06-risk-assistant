"""
Pydantic Data Models & Schemas (NexusTiq24 PS06).
Provides strong type safety for backend APIs, rule engine, and LLM narrative pipeline.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    transaction_id: str
    customer_id: Optional[str] = "UNKNOWN"
    timestamp: str
    description: Optional[str] = "Transaction"
    payee: Optional[str] = "Unknown Payee"
    amount: float
    channel: Optional[str] = "Standard"
    category: Optional[str] = "General"
    status: Optional[str] = "Completed"

    @field_validator("amount", mode="before")

    def parse_amount_str(cls, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            clean = value.replace("₹", "").replace("INR", "").replace("$", "").replace(",", "").strip()
            try:
                return float(clean)
            except ValueError:
                return 0.0
        return 0.0


class RuleFinding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    description: str
    flagged_transaction_ids: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if item in self:
            return self[item]
        return default


class CustomerSummaryStats(BaseModel):
    total_transactions: int = 0
    avg_amount: float = 0.0
    median_amount: float = 0.0
    p90_amount: float = 0.0
    max_amount: float = 0.0
    known_payees_count: int = 0
    established_channels: List[str] = Field(default_factory=list)
    currency: str = "INR"

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if item in self:
            return self[item]
        return default


class RiskAnalysisResult(BaseModel):
    customer_id: str
    attention_needed: bool
    confidence_level: str  # HIGH, MEDIUM, LOW, NONE
    overall_risk_score: int
    summary_stats: CustomerSummaryStats
    triggered_rules: List[RuleFinding] = Field(default_factory=list)
    flagged_transaction_ids: List[str] = Field(default_factory=list)
    narrative_report: Optional[str] = None
    report_source: str = "deterministic_fallback"  # gemini_llm or deterministic_fallback
    fallback_reason: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        if item == "source":
            return self.report_source
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        if item == "source":
            return True
        return hasattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if item in self:
            return self[item]
        return default


class AnalysisRequest(BaseModel):
    customer_id: Optional[str] = "CUSTOM"
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    api_key_override: Optional[str] = None


class APIKeySettingRequest(BaseModel):
    api_key: str


class APIKeyStatusResponse(BaseModel):
    active: bool
    source: str  # env, session, or none


class ExportReportRequest(BaseModel):
    customer_id: str
    report_content: str
    format: str = "markdown"  # markdown or html
