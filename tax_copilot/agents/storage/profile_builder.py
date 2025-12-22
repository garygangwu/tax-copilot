"""Profile builder - converts session data to TaxProfile."""

import re
from pathlib import Path
from datetime import datetime
from typing import Any

from tax_copilot.core.conversation import Session
from tax_copilot.core.models import (
    TaxProfile,
    Income,
    Deductions,
    Dependents,
    Money,
)


class ProfileBuilder:
    """
    Builds TaxProfile objects from interview session data.

    Handles mapping from conversational extracted_data to structured TaxProfile fields.
    """

    def __init__(self, profiles_dir: str | None = None):
        """
        Initialize the profile builder.

        Args:
            profiles_dir: Directory to save completed profiles.
                         If None, uses ~/.tax_copilot/profiles
        """
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        else:
            self.profiles_dir = Path.home() / ".tax_copilot" / "profiles"

        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def build_from_session(self, session: Session) -> TaxProfile:
        """
        Convert session's extracted_data to validated TaxProfile.

        Args:
            session: Session containing extracted data

        Returns:
            TaxProfile object

        Raises:
            ValueError: If required fields are missing
        """
        data = session.extracted_data

        # Build Income object
        income = self._build_income(data.get("income", {}))

        # Build Deductions object
        deductions = self._build_deductions(data.get("deductions", {}))

        # Build Dependents object
        dependents = self._build_dependents(data.get("dependents", {}))

        # Get basic info
        basic_info = data.get("basic_info", {})
        filing_status = basic_info.get("filing_status", "unknown")
        state = basic_info.get("state")

        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(data)

        # Build TaxProfile
        profile = TaxProfile(
            tax_year=session.tax_year,
            filing_status=filing_status,
            state=state,
            income=income,
            deductions=deductions,
            dependents=dependents,
            collected_via="dynamic_questioning",
            session_id=session.session_id,
            confidence_scores=confidence_scores,
            created_at=session.created_at,
            updated_at=datetime.now(),
        )

        return profile

    def _build_income(self, income_data: dict[str, Any]) -> Income:
        """Build Income object from extracted data."""
        total_income = self._parse_money(income_data.get("total_income", 0))
        w2_count = int(income_data.get("w2_count", 0))
        ira_contribution = self._parse_money(income_data.get("ira_contribution", 0))

        return Income(
            total_income=total_income,
            w2_count=w2_count,
            ira_contribution=ira_contribution,
        )

    def _build_deductions(self, deductions_data: dict[str, Any]) -> Deductions:
        """Build Deductions object from extracted data."""
        student_loan_interest = self._parse_money(
            deductions_data.get("student_loan_interest", 0)
        )
        itemized = bool(deductions_data.get("itemized", False))
        itemized_total = self._parse_money(deductions_data.get("itemized_total", 0))

        return Deductions(
            student_loan_interest=student_loan_interest,
            itemized=itemized,
            itemized_total=itemized_total,
        )

    def _build_dependents(self, dependents_data: dict[str, Any]) -> Dependents:
        """Build Dependents object from extracted data."""
        count = int(dependents_data.get("count", 0))
        ages = dependents_data.get("ages", [])
        claiming_child_tax_credit = bool(
            dependents_data.get("claiming_child_tax_credit", False)
        )

        return Dependents(
            count=count,
            ages=ages,
            claiming_child_tax_credit=claiming_child_tax_credit,
        )

    def _parse_money(self, value: Any) -> Money:
        """
        Parse money value from various formats.

        Handles:
        - integers (as cents)
        - floats (as dollars)
        - strings like "$85,000" or "85000" or "around $2,000"
        - Money objects (passthrough)
        - None (returns $0)

        Args:
            value: Value to parse

        Returns:
            Money object
        """
        if value is None:
            return Money(cents=0)

        if isinstance(value, Money):
            return value

        if isinstance(value, int):
            # If value is very large, likely already in cents
            # If small (< 10000), might be dollars
            if value >= 10000:
                return Money(cents=value)
            else:
                # Ambiguous - default to cents for safety
                return Money(cents=value)

        if isinstance(value, float):
            # Treat as dollars
            return Money.from_dollars(value)

        if isinstance(value, str):
            # Extract numeric value from string
            # Remove common text like "around", "about", "$", ",", etc.
            cleaned = re.sub(r"[^\d.]", "", value)

            if not cleaned:
                return Money(cents=0)

            try:
                amount = float(cleaned)
                # If amount has decimal point or is < 10000, treat as dollars
                if "." in value or amount < 10000:
                    return Money.from_dollars(amount)
                else:
                    return Money(cents=int(amount))
            except ValueError:
                return Money(cents=0)

        # Fallback
        return Money(cents=0)

    def _calculate_confidence_scores(
        self, extracted_data: dict[str, Any]
    ) -> dict[str, float]:
        """
        Calculate confidence scores for extracted data.

        Higher confidence for:
        - Explicit numeric values
        - Boolean True/False
        - Enumerated choices

        Lower confidence for:
        - Vague language ("around", "about")
        - Inferred values
        - Missing data

        Returns:
            Dictionary mapping field paths to confidence scores (0.0-1.0)
        """
        scores: dict[str, float] = {}

        # Basic info confidence
        basic_info = extracted_data.get("basic_info", {})
        if basic_info.get("filing_status"):
            scores["filing_status"] = 0.9
        if basic_info.get("state"):
            scores["state"] = 0.9

        # Income confidence
        income = extracted_data.get("income", {})
        if income.get("total_income"):
            # Check if value is vague
            total_str = str(income["total_income"])
            if any(word in total_str.lower() for word in ["around", "about", "~"]):
                scores["income.total_income"] = 0.7
            else:
                scores["income.total_income"] = 0.95

        if "w2_count" in income:
            scores["income.w2_count"] = 0.95

        # Deductions confidence
        deductions = extracted_data.get("deductions", {})
        if deductions.get("student_loan_interest"):
            scores["deductions.student_loan_interest"] = 0.85

        # Dependents confidence
        dependents = extracted_data.get("dependents", {})
        if "count" in dependents:
            scores["dependents.count"] = 0.9
        if dependents.get("ages"):
            scores["dependents.ages"] = 0.85

        return scores

    def calculate_completeness(self, session: Session) -> float:
        """
        Calculate how complete the session data is.

        Returns:
            Completeness score from 0.0 (empty) to 1.0 (fully complete)
        """
        data = session.extracted_data

        required_fields = [
            ("basic_info", "filing_status"),
            ("income", "total_income"),
            ("income", "w2_count"),
        ]

        optional_fields = [
            ("basic_info", "state"),
            ("income", "ira_contribution"),
            ("deductions", "student_loan_interest"),
            ("deductions", "itemized"),
            ("dependents", "count"),
        ]

        # Count required fields present
        required_present = 0
        for category, field in required_fields:
            if data.get(category, {}).get(field) is not None:
                required_present += 1

        # Count optional fields present
        optional_present = 0
        for category, field in optional_fields:
            if data.get(category, {}).get(field) is not None:
                optional_present += 1

        # Weight: 70% required, 30% optional
        required_score = required_present / len(required_fields) if required_fields else 0
        optional_score = optional_present / len(optional_fields) if optional_fields else 0

        return (required_score * 0.7) + (optional_score * 0.3)

    def get_missing_fields(self, session: Session) -> list[str]:
        """
        Get list of required fields that are missing.

        Args:
            session: Session to check

        Returns:
            List of missing field names
        """
        data = session.extracted_data
        missing = []

        required_fields = [
            ("basic_info.filing_status", ["basic_info", "filing_status"]),
            ("income.total_income", ["income", "total_income"]),
            ("income.w2_count", ["income", "w2_count"]),
        ]

        for field_name, path in required_fields:
            value = data
            for key in path:
                value = value.get(key, {}) if isinstance(value, dict) else None
                if value is None:
                    break

            if value is None:
                missing.append(field_name)

        return missing

    def save_profile(self, profile: TaxProfile, user_id: str) -> Path:
        """
        Save completed profile to disk.

        Args:
            profile: TaxProfile to save
            user_id: User ID for filename

        Returns:
            Path to saved profile file
        """
        filename = f"{user_id}_{profile.tax_year}.json"
        file_path = self.profiles_dir / filename

        # Save with pretty formatting
        profile_json = profile.model_dump_json(indent=2)
        file_path.write_text(profile_json)

        return file_path

    def load_profile(self, user_id: str, tax_year: int) -> TaxProfile:
        """
        Load a saved profile.

        Args:
            user_id: User ID
            tax_year: Tax year

        Returns:
            TaxProfile object

        Raises:
            FileNotFoundError: If profile doesn't exist
        """
        filename = f"{user_id}_{tax_year}.json"
        file_path = self.profiles_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Profile not found: {user_id} for year {tax_year}"
            )

        profile_json = file_path.read_text()
        return TaxProfile.model_validate_json(profile_json)
