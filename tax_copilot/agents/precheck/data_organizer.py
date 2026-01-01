"""Data Organizer Agent - Reorganizes extracted data into proper topic buckets."""

from typing import Any

import json
from tax_copilot.core.conversation import Session
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.utils import parse_json_response


# JSON Schema for organized data output
ORGANIZED_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "basic_info": {
            "type": "object",
            "description": "Basic taxpayer information",
        },
        "income": {
            "type": "object",
            "description": "All income-related data",
        },
        "deductions": {
            "type": "object",
            "description": "All deduction-related data",
        },
        "dependents": {
            "type": "object",
            "description": "Dependent information",
        },
    },
    "required": ["basic_info", "income", "deductions", "dependents"],
}


def get_data_organizer_prompt(
    raw_extracted_data: dict[str, Any],
    conversation_summary: str,
) -> str:
    """
    Generate prompt for data organizer.

    Args:
        raw_extracted_data: Raw data that may be misorganized
        conversation_summary: Brief summary of conversation topics

    Returns:
        System prompt string
    """
    # Format raw data for prompt
    raw_data_str = json.dumps(raw_extracted_data, indent=2)

    return f"""You are organizing tax interview data into the correct categories.

**Raw Extracted Data (may have data in wrong topics):**
{raw_data_str}

**Conversation Summary:**
{conversation_summary}

**Your Task:**
Reorganize this data into the standard tax profile structure with these EXACT topic keys:
- basic_info
- income
- deductions
- dependents

**Field Mapping Rules:**

**basic_info** should contain ONLY:
- filing_status (values: "single", "mfj", "mfs", "hoh")
- state (two-letter code like "CA", "NY")

**PRIVACY NOTE:** This is a HIGH-LEVEL tax planning tool. Do NOT include PII like:
- ❌ Names (taxpayer_name, spouse_name)
- ❌ SSNs (taxpayer_ssn, spouse_ssn)
- ❌ Dates of birth
- ❌ Addresses
- ❌ Phone numbers

If PII appears in the raw data, EXCLUDE it from the organized output.

**income** should contain:
- total_income (total of all income sources, in dollars)
- w2_count (number of W-2 jobs, default to 1 if has employment income)
- employment_income (W-2 wages)
- investment_income (from stocks, bonds, crypto, etc.)
  - Can break down into: short_term_capital_gains, long_term_capital_gains
- rental_income (net rental income after expenses)
- self_employment_income (if applicable)
- ira_contribution (if mentioned)
- other_income (catch-all for other sources)

**deductions** should contain:
- student_loan_interest (amount paid)
- charitable_contributions (total donations)
- mortgage_interest (if mentioned)
- state_local_taxes (SALT deductions)
- medical_expenses (if mentioned)
- itemized (true/false - whether user is itemizing)
- itemized_total (total itemized deductions)
- standard_deduction (if mentioned)

**dependents** should contain:
- count (number of dependents, 0 if none)
- ages (array of ages, empty if no dependents)
- claiming_child_tax_credit (true/false)
- dependent_names (optional array)

**Important Reorganization Rules:**
1. **Remove duplicates**: If same data appears with multiple field names (e.g., "salary", "employment_income", "annual_salary"), keep the most standard name ("employment_income") and remove others
2. **Consolidate similar fields**: Multiple donation-related fields → single "charitable_contributions"
3. **Move misplaced data**: If charitable donations are in "income", move to "deductions"
4. **Convert to consistent format**: All monetary amounts should be numbers representing dollars (e.g., 70000 for $70,000)
5. **Calculate totals**: If you see short_term + long_term capital gains, create "investment_income" as the sum
6. **Use null for missing data**: Don't invent values
7. **Remove metadata fields**: Remove fields like "donation_qualified_organization", "donation_method" - these are verification details, not core tax data

**Special Cases:**
- If "charitable_donation" or "donations" or "charitable_contributions" appears anywhere, it belongs in "deductions"
- If "taxes_paid", "tax_withholding", "estimated_tax_payments" appear, they belong in "deductions"
- If "health_expenses", "medical" appear, they belong in "deductions"
- Personal info (names, SSN) belongs in "basic_info"

**Response Format (JSON):**
{{
  "basic_info": {{
    "filing_status": "...",
    "state": "..."
  }},
  "income": {{
    "total_income": 70000,
    "employment_income": 70000,
    "w2_count": 1,
    "investment_income": 20000,
    "rental_income": 5000
  }},
  "deductions": {{
    "charitable_contributions": 13250
  }},
  "dependents": {{
    "count": 0,
    "ages": [],
    "claiming_child_tax_credit": false
  }}
}}

**Important:**
- Return ONLY the JSON object, nothing else
- Ensure all four top-level keys (basic_info, income, deductions, dependents) are present
- Use consistent field names as specified above
- Remove verbose/redundant fields that don't fit the schema

Respond with JSON only.
"""


class DataOrganizer:
    """
    LLM-driven agent that reorganizes extracted data into proper topic buckets.

    Fixes the common problem where LLM extracts all data into a single topic
    or uses inconsistent field names.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the data organizer.

        Args:
            llm_provider: LLM provider for reorganization decisions
        """
        self.llm = llm_provider

    async def organize(
        self,
        session: Session,
    ) -> dict[str, Any]:
        """
        Reorganize session's extracted_data into proper structure.

        Args:
            session: Session with raw extracted_data

        Returns:
            Dictionary with properly organized data under correct topic keys

        Raises:
            Exception: If LLM call fails or returns invalid JSON
        """
        # Build prompt with current data
        prompt = self._build_organizer_prompt(session)

        # Call LLM to reorganize
        try:
            response = await self.llm.generate(
                messages=[
                    Message(
                        role="user",
                        content="Reorganize the extracted tax data into the correct structure.",
                    )
                ],
                system_prompt=prompt,
                response_schema=ORGANIZED_DATA_SCHEMA,
                temperature=0.2,  # Low temp for consistent reorganization
                max_tokens=2000,
            )

            # Parse and return organized data
            organized_data = parse_json_response(response.content)

            # Ensure all required keys exist
            for key in ["basic_info", "income", "deductions", "dependents"]:
                if key not in organized_data:
                    organized_data[key] = {}

            return organized_data

        except json.JSONDecodeError as e:
            # Fallback: return original data structure
            print(f"Failed to parse organized data: {e}")
            return session.extracted_data

        except Exception as e:
            # Fallback: return original data
            print(f"Error during data organization: {e}")
            return session.extracted_data

    def _build_organizer_prompt(self, session: Session) -> str:
        """
        Build the organizer prompt with session data.

        Args:
            session: Current session

        Returns:
            Formatted prompt string
        """
        # Get raw extracted data
        raw_data = session.extracted_data

        # Build conversation summary (just topics discussed)
        topics_covered = session.topics_covered
        conversation_summary = f"Topics discussed: {', '.join(topics_covered)}" if topics_covered else "Interview in progress"

        # Build full prompt
        return get_data_organizer_prompt(
            raw_extracted_data=raw_data,
            conversation_summary=conversation_summary,
        )
