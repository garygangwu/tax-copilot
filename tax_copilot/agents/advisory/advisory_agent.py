"""Advisory Agent - orchestrates tax analysis and report generation."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from tax_copilot.core.models import TaxProfile
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.storage.profile_builder import ProfileBuilder
from .models import AdvisoryReport
from .tax_calculator import TaxCalculator
from .optimization_agent import OptimizationAgent
from .deduction_finder import DeductionFinder
from .report_generator import ReportGenerator
from .prompts import get_executive_summary_prompt


class AdvisoryAgent:
    """
    High-level orchestrator for tax analysis and advisory.

    Coordinates all sub-agents:
    - TaxCalculator: Calculates federal and state taxes
    - OptimizationAgent: Suggests tax-saving strategies
    - DeductionFinder: Identifies missed deductions
    - ReportGenerator: Creates advisory reports
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the advisory agent.

        Args:
            llm_provider: LLM provider for all agents
        """
        self.llm = llm_provider
        self.tax_calculator = TaxCalculator(llm_provider)
        self.optimization_agent = OptimizationAgent(llm_provider)
        self.deduction_finder = DeductionFinder(llm_provider)
        self.report_generator = ReportGenerator()
        self.profile_builder = ProfileBuilder()

    async def analyze_profile(
        self,
        profile: TaxProfile,
        interactive: bool = False,
    ) -> AdvisoryReport:
        """
        Run full tax analysis and return advisory report.

        Args:
            profile: User's TaxProfile
            interactive: If True, ask follow-up questions about missed deductions

        Returns:
            AdvisoryReport with all findings
        """
        start_time = time.time()

        # Step 1: Calculate taxes (parallel federal + state)
        print(f"Calculating {profile.tax_year} taxes...")
        calculation = await self.tax_calculator.calculate(profile)
        print(f"  Federal tax: ${calculation.federal_tax.to_dollars():,.2f}")
        print(f"  State tax: ${calculation.state_tax.to_dollars():,.2f}")
        print(f"  Total tax: ${calculation.total_tax.to_dollars():,.2f}")
        print(f"  Effective rate: {calculation.effective_tax_rate:.1f}%")
        print()

        # Step 2: Find optimizations and missed deductions (parallel)
        print("Analyzing optimization strategies and potential deductions...")
        optimization_task = self.optimization_agent.analyze(profile, calculation)
        deduction_task = self.deduction_finder.analyze(profile)

        optimization_report, deduction_report = await asyncio.gather(
            optimization_task, deduction_task, return_exceptions=True
        )

        # Handle errors
        if isinstance(optimization_report, Exception):
            print(f"  Warning: Optimization analysis failed: {optimization_report}")
            from .models import OptimizationReport
            from tax_copilot.core.models import Money
            optimization_report = OptimizationReport(
                strategies=[],
                total_potential_savings=Money(cents=0),
                reasoning="Analysis failed",
            )

        if isinstance(deduction_report, Exception):
            print(f"  Warning: Deduction finder failed: {deduction_report}")
            from .models import DeductionFinderReport
            from tax_copilot.core.models import Money
            deduction_report = DeductionFinderReport(
                missed_deductions=[],
                total_potential_savings=Money(cents=0),
                follow_up_questions=[],
            )

        print(f"  Found {len(optimization_report.strategies)} optimization strategies")
        print(f"  Found {len(deduction_report.missed_deductions)} potential missed deductions")
        print()

        # Step 3: Generate executive summary using LLM
        print("Generating executive summary...")
        executive_summary, top_recommendations = await self._generate_executive_summary(
            profile, calculation, optimization_report, deduction_report
        )
        print()

        # Step 4: Generate final report
        print("Generating advisory report...")
        report = self.report_generator.generate(
            profile=profile,
            calculation=calculation,
            optimizations=optimization_report,
            missed_deductions=deduction_report,
            executive_summary=executive_summary,
            top_recommendations=top_recommendations,
        )

        # Add metadata
        report.llm_provider = self.llm.__class__.__name__
        report.total_analysis_time_seconds = time.time() - start_time

        print(f"Analysis complete in {report.total_analysis_time_seconds:.1f}s")
        print()

        # Step 5: Interactive mode (optional)
        if interactive and deduction_report.follow_up_questions:
            print("\n=== Interactive Mode ===\n")
            print("We have some questions to better assess your deductions:")
            print()
            # Note: Interactive implementation would go here
            # For now, just list the questions
            for i, question in enumerate(deduction_report.follow_up_questions[:3], 1):
                print(f"{i}. {question}")
            print()
            print("(Interactive mode would allow you to answer these questions)")
            print()

        return report

    async def _generate_executive_summary(
        self,
        profile: TaxProfile,
        calculation,
        optimization_report,
        deduction_report,
    ) -> tuple[str, list[str]]:
        """
        Generate executive summary using LLM.

        Args:
            profile: TaxProfile
            calculation: TaxCalculation
            optimization_report: OptimizationReport
            deduction_report: DeductionFinderReport

        Returns:
            Tuple of (executive_summary, top_recommendations)
        """
        try:
            prompt = get_executive_summary_prompt(
                profile, calculation, optimization_report, deduction_report
            )

            response = await self.llm.generate(
                messages=[
                    Message(
                        role="user",
                        content="Generate the executive summary for this tax analysis.",
                    )
                ],
                system_prompt=prompt,
                temperature=0.7,
                max_tokens=1500,
            )

            data = json.loads(response.content)
            return data.get("executive_summary", ""), data.get("top_recommendations", [])

        except Exception as e:
            print(f"  Warning: Executive summary generation failed: {e}")
            # Use fallback from report generator
            summary = self.report_generator._build_executive_summary(
                profile, calculation, optimization_report, deduction_report
            )
            recommendations = self.report_generator._build_top_recommendations(
                optimization_report, deduction_report
            )
            return summary, recommendations

    def save_report(self, report: AdvisoryReport, user_id: str) -> str:
        """
        Save advisory report to disk.

        Args:
            report: AdvisoryReport to save
            user_id: User ID

        Returns:
            Path to saved report file
        """
        # Create reports directory
        reports_dir = Path.home() / ".tax_copilot" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        report_path = reports_dir / f"{report.report_id}.json"

        with open(report_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)

        return str(report_path)

    def load_report(self, report_id: str) -> AdvisoryReport:
        """
        Load advisory report from disk.

        Args:
            report_id: Report ID

        Returns:
            AdvisoryReport

        Raises:
            FileNotFoundError: If report not found
        """
        reports_dir = Path.home() / ".tax_copilot" / "reports"
        report_path = reports_dir / f"{report_id}.json"

        if not report_path.exists():
            raise FileNotFoundError(f"Report not found: {report_id}")

        with open(report_path, "r") as f:
            data = json.load(f)

        return AdvisoryReport(**data)

    def list_reports(self, user_id: str | None = None) -> list[dict]:
        """
        List available advisory reports.

        Args:
            user_id: Optional user ID filter

        Returns:
            List of report summaries
        """
        reports_dir = Path.home() / ".tax_copilot" / "reports"

        if not reports_dir.exists():
            return []

        summaries = []
        for report_file in reports_dir.glob("rpt_*.json"):
            try:
                with open(report_file, "r") as f:
                    data = json.load(f)

                # Filter by user_id if provided
                if user_id and data.get("user_id") != user_id:
                    continue

                summaries.append({
                    "report_id": data.get("report_id"),
                    "user_id": data.get("user_id"),
                    "tax_year": data.get("tax_year"),
                    "generated_at": data.get("generated_at"),
                    "total_tax": data.get("tax_calculation", {}).get("total_tax", 0),
                    "potential_savings": (
                        data.get("optimization_report", {}).get("total_potential_savings", 0)
                        + data.get("deduction_finder_report", {}).get("total_potential_savings", 0)
                    ),
                })
            except Exception as e:
                print(f"Error loading report {report_file}: {e}")
                continue

        # Sort by generated_at (newest first)
        summaries.sort(key=lambda x: x.get("generated_at", ""), reverse=True)

        return summaries

    def list_profiles(self, user_id: str | None = None) -> list[TaxProfile]:
        """
        List available TaxProfiles for analysis.

        Args:
            user_id: Optional user ID filter

        Returns:
            List of TaxProfile objects
        """
        return self.profile_builder.list_profiles(user_id=user_id)

    def get_latest_profile(self, user_id: str) -> TaxProfile | None:
        """
        Get the most recent profile for a user.

        Args:
            user_id: User ID

        Returns:
            TaxProfile or None if no profiles found
        """
        profiles = self.list_profiles(user_id=user_id)
        if profiles:
            return profiles[0]  # ProfileBuilder sorts by updated_at desc
        return None
