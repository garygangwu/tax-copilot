"""Completion Evaluator Agent - LLM-driven topic completion assessment."""

from typing import Literal, Optional
from pydantic import BaseModel

from tax_copilot.core.conversation import Session, ConversationState
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.utils import parse_json_response


class CompletionEvaluation(BaseModel):
    """Result of topic completion evaluation."""

    topic_complete: bool
    reasoning: str
    next_action: Literal["continue_topic", "advance_to_next_topic", "complete_interview"]
    next_topic: Optional[str] = None
    confidence: Literal["high", "medium", "low"]


# JSON Schema for structured output
COMPLETION_EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "topic_complete": {
            "type": "boolean",
            "description": "Whether the current topic has sufficient information",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of the decision",
        },
        "next_action": {
            "type": "string",
            "enum": ["continue_topic", "advance_to_next_topic", "complete_interview"],
            "description": "What should happen next",
        },
        "next_topic": {
            "type": ["string", "null"],
            "description": "If advancing, which topic to move to next",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Confidence in this assessment",
        },
    },
    "required": ["topic_complete", "reasoning", "next_action", "confidence"],
}


def get_completion_evaluator_prompt(
    tax_year: int,
    current_topic: str,
    topics_covered: list[str],
    topics_remaining: list[str],
    recent_conversation: str,
    extracted_data_summary: str,
) -> str:
    """
    Generate prompt for completion evaluator.

    Args:
        tax_year: Tax year being discussed
        current_topic: Current topic being evaluated
        topics_covered: List of topics already covered
        topics_remaining: List of topics still to cover
        recent_conversation: Recent messages as formatted string
        extracted_data_summary: Summary of data extracted so far

    Returns:
        System prompt string
    """
    topics_covered_str = ", ".join(topics_covered) if topics_covered else "None yet"
    topics_remaining_str = ", ".join(topics_remaining) if topics_remaining else "None"

    return f"""You are a tax interview supervisor evaluating conversation progress.

**Current Interview State:**
- Tax Year: {tax_year}
- Current Topic: {current_topic}
- Topics Covered: {topics_covered_str}
- Topics Remaining: {topics_remaining_str}

**Recent Conversation:**
{recent_conversation}

**Data Extracted So Far:**
{extracted_data_summary}

**Your Task:**
Evaluate whether we have collected SUFFICIENT information for the current topic ({current_topic}).

**Decision Guidelines:**

For **basic_info** topic, sufficient if we know:
- Filing status (single, married filing jointly, etc.)
- State of residence (optional)

For **income** topic, sufficient if we know:
- Primary income source(s) and amounts
- Whether W-2 employee, self-employed, or investor
- User has indicated "no other income" or similar
- (Don't need exact W-2 counts if user provided employment details)

For **deductions** topic, sufficient if:
- User mentioned major deductions (charitable, mortgage, student loans)
- OR explicitly stated "no deductions" or "not aware of any"
- OR asked about common deductions and user declined

For **dependents** topic, sufficient if:
- Know if user has dependents (yes/no)
- If yes, know count and ages
- If no, topic is complete

For **investments** topic, sufficient if:
- Already covered in income discussion (stocks, bonds, etc.)
- OR user explicitly has no investments
- OR user mentioned rental income

**Consider:**
1. Has the user provided the essential information for this topic?
2. Are there obvious gaps that need filling?
3. Is the user indicating they're done with this topic (e.g., "no more", "that's all", "no")?
4. Would a reasonable tax preparer have enough data to proceed?
5. Has the conversation already moved to discussing other topics?

**Recognize Completion Signals:**
- "No other income", "That's all", "No more"
- "I don't have any", "Not applicable", "N/A"
- User answering "no" to follow-up questions
- Natural conversation flow moving to next topic

**Response Format (JSON):**
{{
  "topic_complete": true/false,
  "reasoning": "Brief explanation of your decision (1-2 sentences)",
  "next_action": "continue_topic" | "advance_to_next_topic" | "complete_interview",
  "next_topic": "income" | "deductions" | "dependents" | "reviewing" | null,
  "confidence": "high" | "medium" | "low"
}}

**Examples:**

Example 1 - Topic Complete:
Topic: income
User provided: employment income ($700k), investment income ($2M from stocks), rental income ($5k)
User said: "no others" when asked about other income
→ {{"topic_complete": true, "next_action": "advance_to_next_topic", "next_topic": "deductions", "reasoning": "User provided comprehensive income information and confirmed no other sources", "confidence": "high"}}

Example 2 - Need More Info:
Topic: income
User said: "I have a job"
No amount mentioned yet
→ {{"topic_complete": false, "next_action": "continue_topic", "reasoning": "Need income amount and more details about employment", "confidence": "high"}}

Example 3 - Ready to Complete Interview:
All required topics covered, user said "no more", data looks complete
→ {{"topic_complete": true, "next_action": "complete_interview", "reasoning": "All essential information collected across all topics", "confidence": "high"}}

Example 4 - Deductions Already Discussed:
Topic: income (but user mentioned charitable donations)
Data shows: charitable_donations in extracted data
→ {{"topic_complete": true, "next_action": "advance_to_next_topic", "next_topic": "dependents", "reasoning": "Income covered and user already discussed deductions naturally in conversation", "confidence": "high"}}

Respond with JSON only.
"""


class CompletionEvaluator:
    """
    LLM-driven agent that evaluates topic completion.

    Replaces hardcoded field name checks with intelligent reasoning
    about whether sufficient information has been collected.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the completion evaluator.

        Args:
            llm_provider: LLM provider for making decisions
        """
        self.llm = llm_provider

    async def evaluate(
        self,
        session: Session,
        current_topic: str,
    ) -> CompletionEvaluation:
        """
        Evaluate if current topic is complete.

        Args:
            session: Current interview session
            current_topic: Topic being evaluated

        Returns:
            CompletionEvaluation with decision and reasoning

        Raises:
            Exception: If LLM call fails or returns invalid JSON
        """
        # Build prompt with current context
        prompt = self._build_evaluation_prompt(session, current_topic)

        # Call LLM with lower temperature for consistent decisions
        try:
            response = await self.llm.generate(
                messages=[
                    Message(
                        role="user",
                        content="Evaluate if the current topic is complete based on the conversation.",
                    )
                ],
                system_prompt=prompt,
                response_schema=COMPLETION_EVALUATION_SCHEMA,
                temperature=0.3,  # Lower temp for more deterministic decisions
                max_tokens=500,
            )

            # Parse response
            evaluation_data = parse_json_response(response.content)
            return CompletionEvaluation(**evaluation_data)

        except Exception as e:
            # Fallback: assume not complete
            return CompletionEvaluation(
                topic_complete=False,
                reasoning=f"Failed to parse LLM response: {str(e)}",
                next_action="continue_topic",
                confidence="low",
            )

        except Exception as e:
            # Fallback: assume not complete
            return CompletionEvaluation(
                topic_complete=False,
                reasoning=f"Error during evaluation: {str(e)}",
                next_action="continue_topic",
                confidence="low",
            )

    def _build_evaluation_prompt(
        self,
        session: Session,
        current_topic: str,
    ) -> str:
        """
        Build the evaluation prompt with session context.

        Args:
            session: Current session
            current_topic: Topic being evaluated

        Returns:
            Formatted prompt string
        """
        # Get recent conversation (last 10 exchanges)
        recent_messages = session.get_recent_messages(count=20)
        conversation_lines = []

        for msg in recent_messages:
            role = "Agent" if msg.role == "agent" else "User"
            conversation_lines.append(f"{role}: {msg.content}")

        recent_conversation = "\n".join(conversation_lines)

        # Summarize extracted data
        extracted_data = session.extracted_data
        extracted_summary_lines = []

        for topic, data in extracted_data.items():
            if data:
                # Summarize key fields (limit to avoid token bloat)
                key_count = len(data)
                sample_keys = list(data.keys())[:5]
                extracted_summary_lines.append(
                    f"{topic}: {key_count} fields ({', '.join(sample_keys)}...)"
                )

        extracted_data_summary = "\n".join(extracted_summary_lines) if extracted_summary_lines else "No data extracted yet"

        # Build full prompt
        return get_completion_evaluator_prompt(
            tax_year=session.tax_year,
            current_topic=current_topic,
            topics_covered=session.topics_covered,
            topics_remaining=session.topics_remaining,
            recent_conversation=recent_conversation,
            extracted_data_summary=extracted_data_summary,
        )
