from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Money(BaseModel):
    """Money stored as integer cents.

    For Day 1, this is intentionally simple.

    JSON accepted forms:
      - an integer (treated as cents)
      - an object {"cents": <int>}

    Example:
      "total_income": 18000000   # $180,000.00
    """

    cents: int = 0

    @model_validator(mode="before")
    @classmethod
    def coerce_int_to_money(cls, v: Any) -> Any:
        if isinstance(v, Money):
            return v
        if isinstance(v, int):
            return {"cents": v}
        return v

    @classmethod
    def from_dollars(cls, dollars: float) -> "Money":
        # Day 1: best-effort conversion. Prefer passing cents directly.
        return cls(cents=int(round(dollars * 100)))

    def to_dollars(self) -> float:
        return self.cents / 100.0

    def __str__(self) -> str:
        return f"${self.to_dollars():,.2f}"


class Income(BaseModel):
    total_income: Money = Field(default_factory=Money)
    w2_count: int = 0
    ira_contribution: Money = Field(default_factory=Money)


class Deductions(BaseModel):
    student_loan_interest: Money = Field(default_factory=Money)
    itemized: bool = False
    itemized_total: Money = Field(default_factory=Money)


class Dependents(BaseModel):
    count: int = 0
    ages: List[int] = Field(default_factory=list)
    claiming_child_tax_credit: bool = False

    def max_age(self) -> Optional[int]:
        return max(self.ages) if self.ages else None


class TaxProfile(BaseModel):
    tax_year: int
    filing_status: str = "unknown"  # e.g. single, mfj, mfs, hoh
    state: Optional[str] = None

    income: Income = Field(default_factory=Income)
    deductions: Deductions = Field(default_factory=Deductions)
    dependents: Dependents = Field(default_factory=Dependents)

    # Metadata fields for agentic system
    collected_via: str = "json_import"  # "dynamic_questioning" or "json_import"
    session_id: Optional[str] = None
    confidence_scores: Optional[Dict[str, float]] = None  # Per-field confidence (0.0-1.0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    suggested_action: str
    requires_confirmation: bool = False
    affected_fields: List[str] = Field(default_factory=list)


class Report(BaseModel):
    prior_tax_year: Optional[int] = None
    current_tax_year: Optional[int] = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    findings: List[Finding] = Field(default_factory=list)
    checklist_items: List[str] = Field(default_factory=list)
    summary_counts: Dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_findings(
        cls,
        *,
        prior: Optional[TaxProfile],
        current: TaxProfile,
        findings: List[Finding],
        checklist_items: List[str],
    ) -> "Report":
        counts = {Severity.HIGH.value: 0, Severity.MEDIUM.value: 0, Severity.LOW.value: 0}
        for f in findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return cls(
            prior_tax_year=prior.tax_year if prior else None,
            current_tax_year=current.tax_year,
            findings=findings,
            checklist_items=checklist_items,
            summary_counts=counts,
        )
