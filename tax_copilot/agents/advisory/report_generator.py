"""Report Generator - creates human-readable tax advisory reports."""

import json
from datetime import datetime
from typing import Literal

from tax_copilot.core.models import TaxProfile
from .models import (
    TaxCalculation,
    OptimizationReport,
    DeductionFinderReport,
    AdvisoryReport,
)


class ReportGenerator:
    """
    Generates human-readable advisory reports in multiple formats.

    Supports:
    - Markdown (for terminal display)
    - JSON (for programmatic access)
    """

    def generate(
        self,
        profile: TaxProfile,
        calculation: TaxCalculation,
        optimizations: OptimizationReport,
        missed_deductions: DeductionFinderReport,
        executive_summary: str = "",
        top_recommendations: list[str] | None = None,
    ) -> AdvisoryReport:
        """
        Generate complete advisory report.

        Args:
            profile: User's TaxProfile
            calculation: Tax calculation results
            optimizations: Optimization strategies
            missed_deductions: Missed deductions/credits
            executive_summary: Executive summary text
            top_recommendations: Top 3 recommendations

        Returns:
            AdvisoryReport object
        """
        # Generate report ID
        report_id = f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(profile) % 100000:05d}"

        # Build executive summary if not provided
        if not executive_summary:
            executive_summary = self._build_executive_summary(
                profile, calculation, optimizations, missed_deductions
            )

        # Build top recommendations if not provided
        if not top_recommendations:
            top_recommendations = self._build_top_recommendations(
                optimizations, missed_deductions
            )

        return AdvisoryReport(
            report_id=report_id,
            profile_id=profile.session_id if hasattr(profile, "session_id") else None,
            user_id=getattr(profile, "user_id", "unknown"),
            tax_year=profile.tax_year,
            tax_calculation=calculation,
            optimization_report=optimizations,
            deduction_finder_report=missed_deductions,
            executive_summary=executive_summary,
            top_recommendations=top_recommendations,
        )

    def to_markdown(self, report: AdvisoryReport, profile: TaxProfile) -> str:
        """
        Convert report to markdown format.

        Args:
            report: AdvisoryReport
            profile: TaxProfile

        Returns:
            Markdown string
        """
        lines = []

        # Header
        lines.append(f"# Tax Analysis Report - {report.tax_year}")
        lines.append("")
        lines.append(f"**Generated**: {report.generated_at.strftime('%B %d, %Y at %I:%M %p')}")
        lines.append(f"**Report ID**: {report.report_id}")
        lines.append(f"**Filing Status**: {profile.filing_status.upper()}")
        if profile.state:
            lines.append(f"**State**: {profile.state.upper()}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(report.executive_summary)
        lines.append("")
        lines.append("---")
        lines.append("")

        # Tax Liability Breakdown
        lines.append("## Tax Liability Breakdown")
        lines.append("")
        calc = report.tax_calculation

        # Create table
        lines.append("| Category              | Amount      |")
        lines.append("|-----------------------|-------------|")
        lines.append(f"| Total Income          | {self._format_money(profile.income.total_income)} |")

        # Show breakdown if available
        if "federal" in calc.breakdown and "agi" in calc.breakdown["federal"]:
            agi_cents = calc.breakdown["federal"].get("agi", 0)
            lines.append(f"| Adjusted Gross Income | {self._format_money_cents(agi_cents)} |")

        if "federal" in calc.breakdown and "taxable_income" in calc.breakdown["federal"]:
            taxable_cents = calc.breakdown["federal"].get("taxable_income", 0)
            lines.append(f"| Taxable Income        | {self._format_money_cents(taxable_cents)} |")

        lines.append(f"| Federal Tax           | {self._format_money(calc.federal_tax)} |")
        lines.append(f"| State Tax             | {self._format_money(calc.state_tax)} |")
        lines.append(f"| **Total Tax**         | **{self._format_money(calc.total_tax)}** |")
        lines.append(f"| **Effective Rate**    | **{calc.effective_tax_rate:.1f}%** |")
        lines.append(f"| **Marginal Rate**     | **{calc.marginal_tax_rate:.1f}%** |")
        lines.append("")

        # Confidence indicator
        lines.append(f"*Confidence Level: {calc.confidence.upper()}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Top Optimization Strategies
        if report.optimization_report.strategies:
            lines.append("## Top Optimization Strategies")
            lines.append("")
            lines.append(
                f"*Potential Total Savings: {self._format_money(report.optimization_report.total_potential_savings)}*"
            )
            lines.append("")

            for i, strategy in enumerate(report.optimization_report.strategies[:5], 1):
                emoji = "💰" if strategy.potential_savings.dollars >= 1000 else "💵"
                lines.append(
                    f"### {i}. {strategy.title} {emoji} Est. Savings: {self._format_money(strategy.potential_savings)}"
                )
                lines.append("")
                lines.append(strategy.description)
                lines.append("")

                if strategy.action_steps:
                    lines.append("**Action Steps**:")
                    for step in strategy.action_steps:
                        lines.append(f"- {step}")
                    lines.append("")

                if strategy.deadline:
                    lines.append(f"**Deadline**: {strategy.deadline}")
                    lines.append("")

                effort_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                    strategy.effort_level, "⚪"
                )
                lines.append(f"**Effort**: {effort_emoji} {strategy.effort_level.title()}")
                lines.append("")

                if strategy.risks_considerations:
                    lines.append("**Considerations**:")
                    for risk in strategy.risks_considerations:
                        lines.append(f"- {risk}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Missed Deductions
        if report.deduction_finder_report.missed_deductions:
            lines.append("## Potentially Missed Deductions")
            lines.append("")
            lines.append(
                f"*Potential Total Savings: {self._format_money(report.deduction_finder_report.total_potential_savings)}*"
            )
            lines.append("")

            for deduction in report.deduction_finder_report.missed_deductions[:5]:
                likelihood_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(
                    deduction.likelihood, "⚪"
                )

                lines.append(
                    f"### {deduction.deduction_name} {likelihood_emoji} (Est. {self._format_money(deduction.estimated_value)})"
                )
                lines.append("")
                lines.append(deduction.why_suggested)
                lines.append("")

                if deduction.follow_up_question:
                    lines.append(f"**Question**: {deduction.follow_up_question}")
                    lines.append("")

                if deduction.requirements:
                    lines.append("**Requirements**:")
                    for req in deduction.requirements:
                        lines.append(f"- {req}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Action Plan
        if report.top_recommendations:
            lines.append("## Action Plan")
            lines.append("")
            for i, rec in enumerate(report.top_recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Assumptions (if any)
        if calc.assumptions:
            lines.append("## Assumptions")
            lines.append("")
            for assumption in calc.assumptions:
                lines.append(f"- {assumption}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Disclaimer
        lines.append("## Disclaimer")
        lines.append("")
        lines.append(
            "This analysis is for planning purposes only and does not constitute "
            "professional tax advice. Tax laws are complex and subject to change. "
            "Consult a licensed tax professional or CPA before making tax decisions."
        )
        lines.append("")

        return "\n".join(lines)

    def to_json(self, report: AdvisoryReport) -> str:
        """
        Convert report to JSON format.

        Args:
            report: AdvisoryReport

        Returns:
            JSON string
        """
        return json.dumps(report.to_dict(), indent=2)

    def _build_executive_summary(
        self,
        profile: TaxProfile,
        calculation: TaxCalculation,
        optimizations: OptimizationReport,
        missed_deductions: DeductionFinderReport,
    ) -> str:
        """Build default executive summary."""
        total_potential = (
            optimizations.total_potential_savings.dollars
            + missed_deductions.total_potential_savings.dollars
        )

        summary = (
            f"Based on your {profile.tax_year} tax profile with an income of "
            f"{self._format_money(profile.income.total_income)}, your estimated federal "
            f"tax liability is {self._format_money(calculation.federal_tax)} "
            f"({calculation.effective_tax_rate:.1f}% effective rate). "
        )

        if profile.state:
            summary += (
                f"Your estimated state tax for {profile.state.upper()} is "
                f"{self._format_money(calculation.state_tax)}. "
            )

        if total_potential > 0:
            summary += (
                f"\n\nWe've identified optimization strategies and potential deductions "
                f"that could save you approximately {self._format_money_cents(total_potential)} "
                f"in taxes. The recommendations below are prioritized by potential impact "
                f"and ease of implementation."
            )
        else:
            summary += (
                f"\n\nYour tax situation appears well-optimized. We haven't identified "
                f"significant additional tax-saving opportunities at this time."
            )

        return summary

    def _build_top_recommendations(
        self,
        optimizations: OptimizationReport,
        missed_deductions: DeductionFinderReport,
    ) -> list[str]:
        """Build top 3 recommendations."""
        recommendations = []

        # Add top optimization strategies
        for strategy in optimizations.strategies[:2]:
            recommendations.append(f"{strategy.title} (save ~{self._format_money(strategy.potential_savings)})")

        # Add top missed deduction
        if missed_deductions.missed_deductions:
            top_deduction = missed_deductions.missed_deductions[0]
            recommendations.append(
                f"Verify eligibility for {top_deduction.deduction_name} "
                f"(save ~{self._format_money(top_deduction.estimated_value)})"
            )

        return recommendations[:3]

    def _format_money(self, money) -> str:
        """Format Money object as string."""
        return f"${money.to_dollars():,.2f}"

    def _format_money_cents(self, cents: int) -> str:
        """Format cents as money string."""
        return f"${cents / 100:,.2f}"
