"""Data models for Tax Analysis & Advisory Mode."""

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from tax_copilot.core.models import Money, TaxProfile


class TaxCalculation(BaseModel):
    """Result of tax calculation."""

    federal_tax: Money = Field(default_factory=Money)
    state_tax: Money = Field(default_factory=Money)
    total_tax: Money = Field(default_factory=Money)
    effective_tax_rate: float = 0.0  # percentage (e.g., 15.5 for 15.5%)
    marginal_tax_rate: float = 0.0  # percentage
    refund_or_owed: Money = Field(default_factory=Money)  # positive = refund, negative = owed
    breakdown: dict[str, Any] = Field(default_factory=dict)  # detailed calculation steps
    confidence: Literal["high", "medium", "low"] = "medium"
    assumptions: list[str] = Field(default_factory=list)  # what was assumed in calculation


class OptimizationStrategy(BaseModel):
    """A tax optimization strategy suggestion."""

    strategy_id: str
    title: str  # e.g., "Maximize IRA Contribution"
    description: str  # Detailed explanation
    potential_savings: Money = Field(default_factory=Money)  # Estimated tax savings
    effort_level: Literal["low", "medium", "high"] = "medium"
    deadline: Optional[str] = None  # e.g., "Before Dec 31" or "Before Apr 15"
    action_steps: list[str] = Field(default_factory=list)  # Concrete steps to implement
    risks_considerations: list[str] = Field(default_factory=list)  # Things to watch out for
    confidence: Literal["high", "medium", "low"] = "medium"


class OptimizationReport(BaseModel):
    """Collection of optimization strategies."""

    strategies: list[OptimizationStrategy] = Field(default_factory=list)
    total_potential_savings: Money = Field(default_factory=Money)
    reasoning: str = ""  # Why these strategies were chosen


class MissedDeduction(BaseModel):
    """A potentially missed deduction or credit."""

    deduction_name: str  # e.g., "Charitable Contributions"
    category: str  # e.g., "itemized_deduction" or "tax_credit"
    estimated_value: Money = Field(default_factory=Money)  # Potential savings
    likelihood: Literal["high", "medium", "low"] = "medium"
    why_suggested: str = ""  # Reasoning
    follow_up_question: Optional[str] = None  # Question to ask user
    requirements: list[str] = Field(default_factory=list)  # What's needed to claim it


class DeductionFinderReport(BaseModel):
    """Collection of missed deductions."""

    missed_deductions: list[MissedDeduction] = Field(default_factory=list)
    total_potential_savings: Money = Field(default_factory=Money)
    follow_up_questions: list[str] = Field(default_factory=list)  # All questions to ask user


class AdvisoryReport(BaseModel):
    """Complete tax advisory report."""

    report_id: str
    profile_id: Optional[str] = None
    user_id: str
    tax_year: int
    generated_at: datetime = Field(default_factory=datetime.now)

    # Core analysis results
    tax_calculation: TaxCalculation
    optimization_report: OptimizationReport
    deduction_finder_report: DeductionFinderReport

    # Summary fields
    executive_summary: str = ""
    top_recommendations: list[str] = Field(default_factory=list)

    # Metadata
    llm_provider: str = "unknown"
    total_analysis_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return self.model_dump(mode="json")
