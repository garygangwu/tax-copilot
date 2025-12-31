"""Optimization Agent - identifies tax-saving strategies."""

import json
from typing import Any

from tax_copilot.core.models import TaxProfile, Money
from tax_copilot.agents.providers.base import LLMProvider, Message
from .models import OptimizationStrategy, OptimizationReport, TaxCalculation
from .prompts import get_optimization_prompt


class OptimizationAgent:
    """
    LLM-driven agent that identifies tax optimization strategies.

    Analyzes user's tax profile and calculated taxes to suggest
    actionable strategies for reducing tax liability.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the optimization agent.

        Args:
            llm_provider: LLM provider for strategy generation
        """
        self.llm = llm_provider

    async def analyze(
        self,
        profile: TaxProfile,
        calculation: TaxCalculation,
    ) -> OptimizationReport:
        """
        Identify tax optimization strategies.

        Args:
            profile: User's TaxProfile
            calculation: Calculated tax liability

        Returns:
            OptimizationReport with suggested strategies
        """
        try:
            prompt = get_optimization_prompt(profile, calculation)

            response = await self.llm.generate(
                messages=[
                    Message(
                        role="user",
                        content="Identify tax optimization strategies for this taxpayer.",
                    )
                ],
                system_prompt=prompt,
                temperature=0.7,  # Higher temp for creative strategies
                max_tokens=3000,
            )

            # Parse JSON response
            data = json.loads(response.content)

            # Build strategy objects
            strategies = []
            for strat_data in data.get("strategies", []):
                strategy = OptimizationStrategy(
                    strategy_id=strat_data.get("strategy_id", "unknown"),
                    title=strat_data.get("title", ""),
                    description=strat_data.get("description", ""),
                    potential_savings=Money(cents=strat_data.get("potential_savings", 0)),
                    effort_level=strat_data.get("effort_level", "medium"),
                    deadline=strat_data.get("deadline"),
                    action_steps=strat_data.get("action_steps", []),
                    risks_considerations=strat_data.get("risks_considerations", []),
                    confidence=strat_data.get("confidence", "medium"),
                )

                # Filter out low-value strategies (< $100 savings)
                if strategy.potential_savings.cents >= 10000:  # $100 in cents
                    strategies.append(strategy)

            # Sort by potential savings (descending)
            strategies.sort(key=lambda s: s.potential_savings.cents, reverse=True)

            # Calculate total potential savings
            total_savings_cents = sum(s.potential_savings.cents for s in strategies)

            return OptimizationReport(
                strategies=strategies,
                total_potential_savings=Money(cents=total_savings_cents),
                reasoning=data.get("reasoning", ""),
            )

        except Exception as e:
            print(f"Optimization analysis failed: {e}")
            # Return empty report on failure
            return OptimizationReport(
                strategies=[],
                total_potential_savings=Money(cents=0),
                reasoning=f"Analysis failed: {str(e)}",
            )
