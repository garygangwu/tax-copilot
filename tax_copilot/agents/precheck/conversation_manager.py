"""Conversation manager - orchestrates dialog flow and state transitions."""

from typing import Any
import json
from tax_copilot.core.conversation import Session, ConversationState
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.storage.session_store import SessionStore
from tax_copilot.agents.storage.profile_builder import ProfileBuilder
from tax_copilot.agents.utils import parse_json_response
from .prompts import (
    get_system_prompt,
    get_topic_transition_prompt,
    get_review_prompt,
    EXTRACTION_SCHEMA,
)
from .completion_evaluator import CompletionEvaluator, CompletionEvaluation


class ConversationManager:
    """
    Manages the conversation flow for tax interviews.

    Handles:
    - Processing user input through LLM
    - Extracting structured data
    - Managing state transitions
    - Determining when to move between topics
    """

    # Mapping of states to topics
    STATE_TO_TOPIC = {
        ConversationState.STARTED: "getting_started",
        ConversationState.COLLECTING_BASIC_INFO: "basic_info",
        ConversationState.COLLECTING_INCOME: "income",
        ConversationState.COLLECTING_DEDUCTIONS: "deductions",
        ConversationState.COLLECTING_DEPENDENTS: "dependents",
        ConversationState.COLLECTING_INVESTMENTS: "investments",
        ConversationState.COMPLETED: "completed",
    }

    # State transition order
    STATE_SEQUENCE = [
        ConversationState.STARTED,
        ConversationState.COLLECTING_BASIC_INFO,
        ConversationState.COLLECTING_INCOME,
        ConversationState.COLLECTING_DEDUCTIONS,
        ConversationState.COLLECTING_DEPENDENTS,
        ConversationState.COMPLETED,
    ]

    # Reverse mapping: topic to state
    TOPIC_TO_STATE = {
        "basic_info": ConversationState.COLLECTING_BASIC_INFO,
        "income": ConversationState.COLLECTING_INCOME,
        "deductions": ConversationState.COLLECTING_DEDUCTIONS,
        "dependents": ConversationState.COLLECTING_DEPENDENTS,
        "investments": ConversationState.COLLECTING_INVESTMENTS
    }

    def __init__(
        self,
        session: Session,
        llm_provider: LLMProvider,
        storage: SessionStore,
        profile_builder: ProfileBuilder | None = None,
    ):
        """
        Initialize the conversation manager.

        Args:
            session: Current session
            llm_provider: LLM provider for generating responses
            storage: Session storage for persistence
            profile_builder: Optional profile builder for completeness checks
        """
        self.session = session
        self.llm = llm_provider
        self.storage = storage
        self.profile_builder = profile_builder or ProfileBuilder()
        self.completion_evaluator = CompletionEvaluator(llm_provider)

    async def process_user_input(self, user_message: str) -> str:
        """
        Process user input and return agent's response.

        Steps:
        1. Add user message to session
        2. Check if state transition needed (BEFORE generating next question)
        3. Generate LLM response based on (possibly updated) topic
        4. Parse LLM response (extract data + next question)
        5. Update session with extracted data
        6. Save session to disk
        7. Return agent's next question

        Args:
            user_message: User's message

        Returns:
            Agent's next question or response
        """
        # Step 1: Add user message to session
        self.session.add_message("user", user_message)

        # Step 2: Check state transition BEFORE generating next question
        # This ensures the next question is based on the correct (updated) topic
        await self._check_state_transition()

        # Step 3: Generate response from LLM (based on updated state)
        try:
            llm_response = await self._generate_llm_response()

            # Parse structured response
            response_data = parse_json_response(llm_response.content)

            next_question = response_data.get("next_question", "")
            extracted_data = response_data.get("extracted_data")
            confidence = response_data.get("confidence", "medium")

            # Step 4: Update session with extracted data
            if extracted_data:
                current_topic = self.STATE_TO_TOPIC.get(
                    self.session.state, "unknown"
                )
                # Nest data under topic
                self.session.update_extracted_data({current_topic: extracted_data})

            # Step 5: Add agent message to session
            self.session.add_message(
                "agent",
                next_question,
                metadata={"confidence": confidence},
            )

            # Step 6: Save session
            self.storage.save_session(self.session)

            return next_question

        except json.JSONDecodeError as e:
            # Fallback if LLM doesn't return valid JSON
            fallback_response = (
                "I apologize, I had trouble processing that. "
                "Could you please rephrase your response?"
            )
            self.session.add_message("agent", fallback_response)
            self.storage.save_session(self.session)
            return fallback_response

        except Exception as e:
            # Generic error handling
            error_response = (
                f"I encountered an error: {str(e)}. "
                "Let's continue - could you tell me more?"
            )
            self.session.add_message("agent", error_response)
            self.storage.save_session(self.session)
            return error_response

    async def _generate_llm_response(self) -> Any:
        """
        Generate LLM response based on current conversation state.

        Returns:
            LLMResponse object
        """
        # Build conversation history for LLM
        messages = []

        # Get recent messages (last 20 for context window management)
        recent_messages = self.session.get_recent_messages(count=100)

        for msg in recent_messages:
            if msg.role in ["user", "assistant", "agent"]:
                messages.append(
                    Message(
                        role=msg.role if msg.role == "user" else "assistant",
                        content=msg.content,
                    )
                )

        # Build system prompt based on current state
        current_topic = self.STATE_TO_TOPIC.get(self.session.state, "general")
        system_prompt = get_system_prompt(
            tax_year=self.session.tax_year,
            current_topic=current_topic,
            topics_covered=self.session.topics_covered,
        )

        # Generate response with structured output
        response = await self.llm.generate(
            messages=messages,
            system_prompt=system_prompt,
            response_schema=EXTRACTION_SCHEMA,
            temperature=0.7,
        )

        return response

    async def _check_state_transition(self) -> None:
        """
        Check if enough information collected to transition to next state.

        Uses LLM-based CompletionEvaluator for intelligent assessment.
        Updates session state if transition should occur.
        """
        current_state = self.session.state
        current_topic = self.STATE_TO_TOPIC.get(current_state)

        # Don't transition if already in COMPLETED or just STARTED
        if current_state in [ConversationState.COMPLETED, ConversationState.STARTED]:
            return

        # Use CompletionEvaluator to assess if topic is complete
        try:
            evaluation = await self.completion_evaluator.evaluate(
                session=self.session,
                current_topic=current_topic,
            )

            # Handle evaluation result
            await self._handle_evaluation(evaluation)

            if len(self.session.topics_remaining) == 0 and evaluation.topic_complete:
                # Ready to complete the interview
                self.session.transition_state(ConversationState.COMPLETED)

        except Exception as e:
            # If evaluator fails, don't transition (safe fallback)
            print(f"Completion evaluation failed: {e}")
            return

    async def _handle_evaluation(self, evaluation: CompletionEvaluation) -> None:
        """
        Handle the completion evaluation result.

        Args:
            evaluation: CompletionEvaluation from the evaluator
        """
        current_state = self.session.state
        current_topic = self.STATE_TO_TOPIC.get(current_state)

        if evaluation.next_action == "complete_interview":
            # Ready to complete the interview
            if current_topic and current_topic not in self.session.topics_covered:
                self.session.mark_topic_covered(current_topic)

        elif evaluation.next_action == "advance_to_next_topic":
            # Mark current topic as covered
            if current_topic and current_topic not in self.session.topics_covered:
                self.session.mark_topic_covered(current_topic)

            # Determine next state based on evaluation suggestion
            if evaluation.next_topic:
                next_state = self.TOPIC_TO_STATE.get(evaluation.next_topic)
                if next_state:
                    self.session.transition_state(next_state)
                else:
                    # Fallback: use sequential transition
                    next_state = self._get_next_state(current_state)
                    if next_state:
                        self.session.transition_state(next_state)
            else:
                # No specific next topic suggested, use sequential
                next_state = self._get_next_state(current_state)
                if next_state:
                    self.session.transition_state(next_state)

        # If next_action is "continue_topic", don't transition (keep current state)

    def _get_next_state(
        self, current_state: ConversationState
    ) -> ConversationState | None:
        """
        Get the next state in the sequence.

        Args:
            current_state: Current conversation state

        Returns:
            Next state, or None if already at end
        """
        try:
            current_index = self.STATE_SEQUENCE.index(current_state)
            if current_index < len(self.STATE_SEQUENCE) - 1:
                return self.STATE_SEQUENCE[current_index + 1]
        except ValueError:
            pass

        return None

    def _is_confirmation(self, message: str) -> bool:
        """
        Check if user message is a confirmation.

        Args:
            message: User's message

        Returns:
            True if message indicates confirmation
        """
        message_lower = message.lower().strip()

        confirmations = [
            "yes",
            "yeah",
            "yep",
            "correct",
            "right",
            "accurate",
            "looks good",
            "that's right",
            "that's correct",
            "confirmed",
            "confirm",
        ]

        return any(conf in message_lower for conf in confirmations)
