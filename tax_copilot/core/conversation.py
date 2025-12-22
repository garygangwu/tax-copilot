"""Conversation and session data models."""

from datetime import datetime
from typing import Any, Literal
from enum import Enum
from pydantic import BaseModel, Field


class ConversationState(str, Enum):
    """States in the tax interview conversation flow."""

    STARTED = "STARTED"
    COLLECTING_BASIC_INFO = "COLLECTING_BASIC_INFO"
    COLLECTING_INCOME = "COLLECTING_INCOME"
    COLLECTING_DEDUCTIONS = "COLLECTING_DEDUCTIONS"
    COLLECTING_DEPENDENTS = "COLLECTING_DEPENDENTS"
    COLLECTING_INVESTMENTS = "COLLECTING_INVESTMENTS"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"


class ConversationMessage(BaseModel):
    """Represents a single message in a conversation."""

    role: Literal["agent", "user", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] | None = None


class Session(BaseModel):
    """
    Represents a tax interview session.

    A session tracks the entire conversation between the agent and user,
    along with extracted structured data and progress through the interview.
    """

    session_id: str
    user_id: str
    tax_year: int
    state: ConversationState
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[ConversationMessage] = Field(default_factory=list)
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    topics_covered: list[str] = Field(default_factory=list)
    topics_remaining: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None

    def add_message(
        self,
        role: Literal["agent", "user", "system"],
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation."""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata,
        )
        self.messages.append(message)
        self.updated_at = datetime.now()

    def update_extracted_data(self, new_data: dict[str, Any]) -> None:
        """
        Update extracted data with new information.

        Performs a deep merge of dictionaries.
        """
        self._deep_merge(self.extracted_data, new_data)
        self.updated_at = datetime.now()

    def _deep_merge(self, base: dict, update: dict) -> None:
        """Deep merge update dict into base dict."""
        for key, value in update.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def transition_state(self, new_state: ConversationState) -> None:
        """Transition to a new conversation state."""
        self.state = new_state
        self.updated_at = datetime.now()

    def mark_topic_covered(self, topic: str) -> None:
        """Mark a topic as covered and remove from remaining."""
        if topic not in self.topics_covered:
            self.topics_covered.append(topic)
        if topic in self.topics_remaining:
            self.topics_remaining.remove(topic)
        self.updated_at = datetime.now()

    def get_recent_messages(self, count: int = 10) -> list[ConversationMessage]:
        """Get the most recent N messages."""
        return self.messages[-count:] if self.messages else []
