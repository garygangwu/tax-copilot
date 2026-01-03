"""Deduction Finder Agent - identifies potentially missed deductions."""

from typing import Any

from tax_copilot.core.models import TaxProfile, Money
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.utils import parse_json_response
from .models import MissedDeduction, DeductionFinderReport
from .prompts import get_deduction_finder_prompt


class DeductionFinder:
    """
    LLM-driven agent that identifies potentially missed deductions and credits.

    Analyzes what the user provided and suggests common deductions
    they may have overlooked.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the deduction finder.

        Args:
            llm_provider: LLM provider for deduction discovery
        """
        self.llm = llm_provider

    async def analyze(self, profile: TaxProfile) -> DeductionFinderReport:
        """
        Identify potentially missed deductions.

        Args:
            profile: User's TaxProfile

        Returns:
            DeductionFinderReport with missed deductions
        """
        try:
            prompt = get_deduction_finder_prompt(profile)

            response = await self.llm.generate(
                messages=[
                    Message(
                        role="user",
                        content="Identify deductions and credits this taxpayer may have missed.",
                    )
                ],
                system_prompt=prompt,
                temperature=0.5,  # Balanced creativity and accuracy
                max_tokens=3000,
            )

            # Parse JSON response
            data = parse_json_response(response.content)

            # Build missed deduction objects
            missed_deductions = []
            for deduction_data in data.get("missed_deductions", []):
                deduction = MissedDeduction(
                    deduction_name=deduction_data.get("deduction_name", ""),
                    category=deduction_data.get("category", ""),
                    estimated_value=Money(dollars=deduction_data.get("estimated_value", 0)),
                    likelihood=deduction_data.get("likelihood", "medium"),
                    why_suggested=deduction_data.get("why_suggested", ""),
                    follow_up_question=deduction_data.get("follow_up_question"),
                    requirements=deduction_data.get("requirements", []),
                )

                missed_deductions.append(deduction)

            # Sort by estimated_value * likelihood score
            def priority_score(d: MissedDeduction) -> float:
                likelihood_scores = {"high": 1.0, "medium": 0.6, "low": 0.3}
                likelihood_mult = likelihood_scores.get(d.likelihood, 0.5)
                return d.estimated_value.dollars * likelihood_mult

            missed_deductions.sort(key=priority_score, reverse=True)

            # Calculate total potential savings
            total_savings_dollars = sum(d.estimated_value.dollars for d in missed_deductions)

            # Extract follow-up questions
            follow_up_questions = [
                d.follow_up_question
                for d in missed_deductions
                if d.follow_up_question
            ]

            return DeductionFinderReport(
                missed_deductions=missed_deductions,
                total_potential_savings=Money(dollars=total_savings_dollars),
                follow_up_questions=follow_up_questions,
            )

        except Exception as e:
            print(f"Deduction finder analysis failed: {e}")
            # Return empty report on failure
            return DeductionFinderReport(
                missed_deductions=[],
                total_potential_savings=Money(cents=0),
                follow_up_questions=[],
            )
