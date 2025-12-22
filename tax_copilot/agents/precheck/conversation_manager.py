"""Conversation manager - orchestrates dialog flow and state transitions."""

import json
from typing import Any

from tax_copilot.core.conversation import Session, ConversationState
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.storage.session_store import SessionStore
from tax_copilot.agents.storage.profile_builder import ProfileBuilder
from .prompts import (
    get_system_prompt,
    get_topic_transition_prompt,
    get_review_prompt,
    EXTRACTION_SCHEMA,
)


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
        ConversationState.REVIEWING: "review",
        ConversationState.COMPLETED: "completed",
    }

    # State transition order
    STATE_SEQUENCE = [
        ConversationState.STARTED,
        ConversationState.COLLECTING_BASIC_INFO,
        ConversationState.COLLECTING_INCOME,
        ConversationState.COLLECTING_DEDUCTIONS,
        ConversationState.COLLECTING_DEPENDENTS,
        ConversationState.REVIEWING,
        ConversationState.COMPLETED,
    ]

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

    async def process_user_input(self, user_message: str) -> str:
        """
        Process user input and return agent's response.

        Steps:
        1. Add user message to session
        2. Call LLM with conversation history + current state
        3. Parse LLM response (extract data + next question)
        4. Update session with extracted data
        5. Determine if state transition needed
        6. Save session to disk
        7. Return agent's next question

        Args:
            user_message: User's message

        Returns:
            Agent's next question or response
        """
        # Add user message to session
        self.session.add_message("user", user_message)

        # Check if this is a confirmation during review
        if self.session.state == ConversationState.REVIEWING:
            if self._is_confirmation(user_message):
                # User confirmed - transition to completed
                self.session.transition_state(ConversationState.COMPLETED)
                self.storage.save_session(self.session)
                return "Perfect! Your tax information has been saved. You can now use this data for your tax review."
            else:
                # User wants to make changes - ask what to change
                response = "No problem! What would you like to change or add?"
                self.session.add_message("agent", response)
                self.storage.save_session(self.session)
                return response

        # Generate response from LLM
        try:
            llm_response = await self._generate_llm_response()

            # Parse structured response
            response_data = json.loads(llm_response.content)

            next_question = response_data.get("next_question", "")
            extracted_data = response_data.get("extracted_data")
            confidence = response_data.get("confidence", "medium")

            # Update session with extracted data
            if extracted_data:
                current_topic = self.STATE_TO_TOPIC.get(
                    self.session.state, "unknown"
                )
                # Nest data under topic
                self.session.update_extracted_data({current_topic: extracted_data})

            # Add agent message to session
            self.session.add_message(
                "agent",
                next_question,
                metadata={"confidence": confidence},
            )

            # Check if should transition state
            await self._check_state_transition()

            # Save session
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
        recent_messages = self.session.get_recent_messages(count=20)

        for msg in recent_messages:
            if msg.role in ["user", "assistant"]:
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

        Updates session state if transition should occur.
        """
        current_state = self.session.state
        current_topic = self.STATE_TO_TOPIC.get(current_state)

        # Don't transition if already in COMPLETED or just STARTED
        if current_state in [ConversationState.COMPLETED, ConversationState.STARTED]:
            return

        # Check if current topic has sufficient data
        if self._is_topic_complete(current_topic):
            # Mark topic as covered
            if current_topic not in self.session.topics_covered:
                self.session.mark_topic_covered(current_topic)

            # Determine next state
            next_state = self._get_next_state(current_state)

            if next_state:
                self.session.transition_state(next_state)

                # If transitioning to REVIEWING, check overall completeness
                if next_state == ConversationState.REVIEWING:
                    completeness = self.profile_builder.calculate_completeness(
                        self.session
                    )
                    # Only review if we have decent completeness
                    if completeness < 0.6:
                        # Skip review, need more data
                        # Go back to collecting (this is a safeguard)
                        pass

    def _is_topic_complete(self, topic: str) -> bool:
        """
        Determine if a topic has enough information.

        Args:
            topic: Topic name

        Returns:
            True if topic is complete, False otherwise
        """
        data = self.session.extracted_data.get(topic, {})

        # Define minimum requirements per topic
        if topic == "basic_info":
            return "filing_status" in data

        elif topic == "income":
            # Need at least total income and w2 count
            return "total_income" in data and "w2_count" in data

        elif topic == "deductions":
            # Deductions are somewhat optional, but we should ask about common ones
            # Consider complete if we've asked about student loans or itemizing
            return (
                "student_loan_interest" in data
                or "itemized" in data
                or len(data) >= 2
            )

        elif topic == "dependents":
            # Need to know count (even if zero)
            return "count" in data

        elif topic == "investments":
            # Investments are optional for many users
            # Consider complete if any investment data present or explicitly declined
            return len(data) > 0 or topic in self.session.topics_covered

        return False

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

    async def get_next_question(self) -> str:
        """
        Generate the next question based on current state.

        Used for initiating conversation or after state transitions.

        Returns:
            Next question to ask
        """
        current_topic = self.STATE_TO_TOPIC.get(self.session.state)

        # If reviewing, generate review summary
        if self.session.state == ConversationState.REVIEWING:
            system_prompt = get_review_prompt(
                extracted_data=self.session.extracted_data,
                tax_year=self.session.tax_year,
            )
        else:
            # Generate question for current topic
            system_prompt = get_system_prompt(
                tax_year=self.session.tax_year,
                current_topic=current_topic,
                topics_covered=self.session.topics_covered,
            )

        # Use minimal message history for initial questions
        messages = [
            Message(
                role="user",
                content="Let's begin.",
            )
        ]

        response = await self.llm.generate(
            messages=messages,
            system_prompt=system_prompt,
            response_schema=EXTRACTION_SCHEMA,
            temperature=0.7,
        )

        try:
            response_data = json.loads(response.content)
            next_question = response_data.get("next_question", "How can I help you?")
            return next_question
        except json.JSONDecodeError:
            return "How can I help you with your tax information today?"
