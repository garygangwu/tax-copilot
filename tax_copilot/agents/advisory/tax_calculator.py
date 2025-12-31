"""Tax Calculator Agent - calculates federal and state tax liability."""

import asyncio
from typing import Any

from tax_copilot.core.models import TaxProfile, Money
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.utils import parse_json_response
from .models import TaxCalculation
from .prompts import get_federal_tax_prompt, get_state_tax_prompt


class TaxCalculator:
    """
    LLM-driven tax calculator for federal and state taxes.

    Uses LLM's knowledge of current tax code to estimate tax liability.
    No hardcoded tax brackets or rates - fully agentic approach.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the tax calculator.

        Args:
            llm_provider: LLM provider for tax calculations
        """
        self.llm = llm_provider

    async def calculate(self, profile: TaxProfile) -> TaxCalculation:
        """
        Calculate federal and state tax liability.

        Args:
            profile: User's TaxProfile

        Returns:
            TaxCalculation with federal, state, and total tax
        """
        # Run federal and state calculations in parallel
        federal_task = self._calculate_federal(profile)
        state_task = self._calculate_state(profile)

        federal_result, state_result = await asyncio.gather(
            federal_task, state_task, return_exceptions=True
        )

        # Handle errors gracefully
        if isinstance(federal_result, Exception):
            print(f"Federal tax calculation failed: {federal_result}")
            federal_data = self._fallback_federal_calculation(profile)
        else:
            federal_data = federal_result

        if isinstance(state_result, Exception):
            print(f"State tax calculation failed: {state_result}")
            state_data = self._fallback_state_calculation(profile)
        else:
            state_data = state_result

        # Build final calculation
        federal_tax = Money(cents=federal_data.get("federal_tax", 0))
        state_tax = Money(cents=state_data.get("state_tax", 0))
        total_tax = Money(cents=federal_tax.cents + state_tax.cents)

        # Calculate refund/owed (simplified - assumes no withholding info)
        # Negative means owed, positive means refund
        refund_or_owed = Money(cents=-total_tax.cents)

        # Merge breakdown data
        breakdown = {
            "federal": federal_data.get("breakdown", {}),
            "state": state_data.get("breakdown", {}),
        }

        # Merge assumptions
        assumptions = federal_data.get("assumptions", []) + state_data.get("assumptions", [])

        # Determine overall confidence
        fed_conf = federal_data.get("confidence", "medium")
        state_conf = state_data.get("confidence", "medium")
        confidence = self._merge_confidence(fed_conf, state_conf)

        return TaxCalculation(
            federal_tax=federal_tax,
            state_tax=state_tax,
            total_tax=total_tax,
            effective_tax_rate=federal_data.get("breakdown", {}).get("effective_tax_rate", 0.0),
            marginal_tax_rate=federal_data.get("breakdown", {}).get("marginal_tax_rate", 0.0),
            refund_or_owed=refund_or_owed,
            breakdown=breakdown,
            confidence=confidence,
            assumptions=assumptions,
        )

    async def _calculate_federal(self, profile: TaxProfile) -> dict[str, Any]:
        """
        Calculate federal tax using LLM.

        Args:
            profile: User's TaxProfile

        Returns:
            Dictionary with federal tax data
        """
        prompt = get_federal_tax_prompt(profile)

        response = await self.llm.generate(
            messages=[
                Message(
                    role="user",
                    content="Calculate the federal income tax based on the profile provided.",
                )
            ],
            system_prompt=prompt,
            temperature=0.2,  # Low temperature for consistent calculations
            max_tokens=2000,
        )

        # Parse JSON response
        try:
            data = parse_json_response(response.content)

            # Validate data
            if "federal_tax" not in data:
                raise ValueError("Missing federal_tax in response")

            # Ensure federal_tax is non-negative
            if data["federal_tax"] < 0:
                data["federal_tax"] = 0
                data.setdefault("assumptions", []).append("Federal tax set to $0 (was negative)")

            return data

        except json.JSONDecodeError as e:
            print(f"Failed to parse federal tax JSON: {e}")
            print(f"Response: {response.content}")
            raise

    async def _calculate_state(self, profile: TaxProfile) -> dict[str, Any]:
        """
        Calculate state tax using LLM.

        Args:
            profile: User's TaxProfile

        Returns:
            Dictionary with state tax data
        """
        prompt = get_state_tax_prompt(profile)

        response = await self.llm.generate(
            messages=[
                Message(
                    role="user",
                    content="Calculate the state income tax based on the profile provided.",
                )
            ],
            system_prompt=prompt,
            temperature=0.2,  # Low temperature for consistent calculations
            max_tokens=1500,
        )

        # Parse JSON response
        try:
            data = parse_json_response(response.content)

            # Validate data
            if "state_tax" not in data:
                raise ValueError("Missing state_tax in response")

            # Ensure state_tax is non-negative
            if data["state_tax"] < 0:
                data["state_tax"] = 0
                data.setdefault("assumptions", []).append("State tax set to $0 (was negative)")

            return data

        except json.JSONDecodeError as e:
            print(f"Failed to parse state tax JSON: {e}")
            print(f"Response: {response.content}")
            raise

    def _fallback_federal_calculation(self, profile: TaxProfile) -> dict[str, Any]:
        """
        Fallback federal tax calculation when LLM fails.

        Uses rough estimate: 15% effective rate for planning purposes.

        Args:
            profile: User's TaxProfile

        Returns:
            Dictionary with estimated federal tax data
        """
        income_cents = profile.income.total_income.cents
        estimated_tax_cents = int(income_cents * 0.15)  # 15% rough estimate

        return {
            "federal_tax": estimated_tax_cents,
            "breakdown": {
                "total_income": income_cents,
                "effective_tax_rate": 15.0,
                "marginal_tax_rate": 22.0,  # Common bracket
            },
            "assumptions": [
                "Fallback calculation used (LLM unavailable)",
                "Used 15% effective tax rate estimate",
            ],
            "confidence": "low",
        }

    def _fallback_state_calculation(self, profile: TaxProfile) -> dict[str, Any]:
        """
        Fallback state tax calculation when LLM fails.

        Returns $0 state tax if state unknown or LLM fails.

        Args:
            profile: User's TaxProfile

        Returns:
            Dictionary with state tax data
        """
        return {
            "state_tax": 0,
            "has_income_tax": False,
            "breakdown": {},
            "assumptions": [
                "Fallback calculation used (LLM unavailable)",
                "State tax set to $0",
            ],
            "confidence": "low",
        }

    def _merge_confidence(
        self,
        confidence1: str,
        confidence2: str,
    ) -> str:
        """
        Merge two confidence levels (return the lower one).

        Args:
            confidence1: First confidence level
            confidence2: Second confidence level

        Returns:
            Merged confidence level
        """
        levels = {"high": 3, "medium": 2, "low": 1}

        level1 = levels.get(confidence1, 2)
        level2 = levels.get(confidence2, 2)

        min_level = min(level1, level2)

        for name, value in levels.items():
            if value == min_level:
                return name

        return "medium"
