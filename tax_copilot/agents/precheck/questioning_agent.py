"""Questioning Agent - High-level orchestrator for tax interviews."""

import json
from typing import Any
from datetime import datetime

from tax_copilot.core.conversation import Session, ConversationState
from tax_copilot.core.models import TaxProfile
from tax_copilot.agents.providers.base import LLMProvider, Message
from tax_copilot.agents.storage.session_store import SessionStore
from tax_copilot.agents.storage.profile_builder import ProfileBuilder
from .conversation_manager import ConversationManager
from .prompts import get_opening_question_prompt, EXTRACTION_SCHEMA
from .data_organizer import DataOrganizer


class QuestioningAgent:
    """
    High-level orchestrator for dynamic tax questioning.

    This agent manages the entire interview process:
    - Starting new interviews
    - Resuming existing sessions
    - Coordinating with ConversationManager
    - Building and saving final profiles
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        storage: SessionStore | None = None,
        profile_builder: ProfileBuilder | None = None,
    ):
        """
        Initialize the questioning agent.

        Args:
            llm_provider: LLM provider for generating questions
            storage: Session storage (creates default if None)
            profile_builder: Profile builder (creates default if None)
        """
        self.llm = llm_provider
        self.storage = storage or SessionStore()
        self.profile_builder = profile_builder or ProfileBuilder()
        self.data_organizer = DataOrganizer(llm_provider)

    async def start_interview(
        self,
        user_id: str,
        tax_year: int,
    ) -> dict[str, Any]:
        """
        Start a new tax interview.

        Args:
            user_id: User identifier
            tax_year: Tax year for this interview

        Returns:
            Dict with:
                - session_id: ID of created session
                - first_question: Opening question
        """
        # Create new session
        session = self.storage.create_session(user_id=user_id, tax_year=tax_year)

        # Transition to basic info collection
        session.transition_state(ConversationState.COLLECTING_BASIC_INFO)

        # Generate opening question
        first_question = await self._generate_opening_question(tax_year)

        # Add opening question to session
        session.add_message("agent", first_question)

        # Save session
        self.storage.save_session(session)

        return {
            "session_id": session.session_id,
            "first_question": first_question,
        }

    async def continue_interview(
        self,
        session_id: str,
        user_response: str,
    ) -> dict[str, Any]:
        """
        Continue an existing interview with user's response.

        Args:
            session_id: ID of session to continue
            user_response: User's response to previous question

        Returns:
            Dict with:
                - agent_response: Agent's next question or response
                - is_complete: Whether interview is finished
                - profile: TaxProfile if complete, None otherwise
                - session_state: Current conversation state
        """
        # Load session
        try:
            session = self.storage.load_session(session_id)
        except FileNotFoundError:
            return {
                "agent_response": "I couldn't find that interview session. Would you like to start a new one?",
                "is_complete": False,
                "profile": None,
                "session_state": "error",
                "error": "Session not found",
            }

        # Create conversation manager
        manager = ConversationManager(
            session=session,
            llm_provider=self.llm,
            storage=self.storage,
            profile_builder=self.profile_builder,
        )

        # Process user input
        agent_response = await manager.process_user_input(user_response)

        # Check if interview is complete
        is_complete = session.state == ConversationState.COMPLETED

        profile = None
        if is_complete:
            # Build final profile
            try:
                # Step 1: Reorganize extracted data into proper structure
                organized_data = await self.data_organizer.organize(session)

                # Update session with organized data
                session.extracted_data = organized_data
                self.storage.save_session(session)

                # Step 2: Build profile from organized data
                profile = self.profile_builder.build_from_session(session)

                # Step 3: Save profile to disk
                self.profile_builder.save_profile(profile, user_id=session.user_id)

            except Exception as e:
                # If profile building fails, mark as error but don't crash
                return {
                    "agent_response": f"I collected your information, but had trouble saving it: {str(e)}",
                    "is_complete": True,
                    "profile": None,
                    "session_state": session.state.value,
                    "error": str(e),
                }

        return {
            "agent_response": agent_response,
            "is_complete": is_complete,
            "profile": profile,
            "session_state": session.state.value,
        }

    async def resume_interview(self, session_id: str) -> dict[str, Any]:
        """
        Resume a paused interview.

        Args:
            session_id: ID of session to resume

        Returns:
            Dict with:
                - session_id: Session ID
                - last_question: Last question asked
                - session_state: Current state
                - messages_count: Number of messages in conversation
        """
        try:
            session = self.storage.load_session(session_id)
        except FileNotFoundError:
            return {
                "error": "Session not found",
                "session_id": session_id,
            }

        # Get last agent message
        last_question = "Let's continue where we left off."
        for msg in reversed(session.messages):
            if msg.role == "agent":
                last_question = msg.content
                break

        return {
            "session_id": session.session_id,
            "last_question": last_question,
            "session_state": session.state.value,
            "messages_count": len(session.messages),
            "tax_year": session.tax_year,
        }

    def list_sessions(
        self,
        user_id: str | None = None,
        tax_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List available sessions.

        Args:
            user_id: Filter by user ID (optional)
            tax_year: Filter by tax year (optional)

        Returns:
            List of session summaries
        """
        sessions = self.storage.list_sessions(user_id=user_id, tax_year=tax_year)

        summaries = []
        for session in sessions:
            summaries.append({
                "session_id": session.session_id,
                "user_id": session.user_id,
                "tax_year": session.tax_year,
                "state": session.state.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "messages_count": len(session.messages),
            })

        return summaries

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """
        Get detailed summary of a session.

        Args:
            session_id: Session ID

        Returns:
            Session summary with extracted data and completeness
        """
        try:
            session = self.storage.load_session(session_id)
        except FileNotFoundError:
            return {"error": "Session not found"}

        completeness = self.profile_builder.calculate_completeness(session)
        missing_fields = self.profile_builder.get_missing_fields(session)

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "tax_year": session.tax_year,
            "state": session.state.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages_count": len(session.messages),
            "topics_covered": session.topics_covered,
            "topics_remaining": session.topics_remaining,
            "completeness": completeness,
            "missing_fields": missing_fields,
            "extracted_data": session.extracted_data,
        }

    async def _generate_opening_question(self, tax_year: int) -> str:
        """
        Generate the opening question for a new interview.

        Args:
            tax_year: Tax year

        Returns:
            Opening question string
        """
        prompt = get_opening_question_prompt(tax_year)

        messages = [
            Message(
                role="user",
                content="Generate the opening question.",
            )
        ]

        try:
            response = await self.llm.generate(
                messages=messages,
                system_prompt=prompt,
                response_schema=EXTRACTION_SCHEMA,
                temperature=0.7,
            )

            response_data = json.loads(response.content)
            return response_data.get(
                "next_question",
                f"Hi! Let's get started on your {tax_year} tax information. "
                "What's your filing status?",
            )

        except Exception:
            # Fallback opening question
            return (
                f"Hi! I'm here to help collect your {tax_year} tax information. "
                "Let's start with the basics - what's your filing status? "
                "Are you filing as single, married filing jointly, married filing separately, "
                "or head of household?"
            )
