"""Session storage with CRUD operations."""

import os
import json
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional

from tax_copilot.core.conversation import Session, ConversationState


class SessionStore:
    """
    Manages persistent storage of interview sessions.

    Sessions are stored as JSON files in ~/.tax_copilot/sessions/
    """

    def __init__(self, data_dir: str | None = None):
        """
        Initialize the session store.

        Args:
            data_dir: Base directory for tax-copilot data.
                     If None, uses ~/.tax_copilot
        """
        if data_dir:
            self.base_dir = Path(data_dir)
        else:
            self.base_dir = Path.home() / ".tax_copilot"

        self.sessions_dir = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        user_id: str,
        tax_year: int,
        initial_topics: list[str] | None = None,
    ) -> Session:
        """
        Create a new interview session.

        Args:
            user_id: Identifier for the user
            tax_year: Tax year for this interview
            initial_topics: List of topics to cover (defaults to standard topics)

        Returns:
            New Session object
        """
        # Generate unique session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        session_id = f"sess_{timestamp}_{random_suffix}"

        # Default topics if not provided
        if initial_topics is None:
            initial_topics = [
                "basic_info",
                "income",
                "deductions",
                "dependents",
                "investments",
            ]

        # Create session
        session = Session(
            session_id=session_id,
            user_id=user_id,
            tax_year=tax_year,
            state=ConversationState.STARTED,
            topics_remaining=initial_topics.copy(),
        )

        # Save to disk
        self.save_session(session)

        return session

    def save_session(self, session: Session) -> None:
        """
        Save session to disk using atomic write.

        Args:
            session: Session to save

        Raises:
            IOError: If save fails
        """
        # Update timestamp
        session.updated_at = datetime.now()

        # Serialize to JSON
        session_json = session.model_dump_json(indent=2)

        # Write to temp file first (atomic write)
        session_path = self.sessions_dir / f"{session.session_id}.json"
        temp_path = session_path.with_suffix(".json.tmp")

        try:
            temp_path.write_text(session_json)
            temp_path.replace(session_path)  # Atomic rename
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to save session {session.session_id}: {e}") from e

    def load_session(self, session_id: str) -> Session:
        """
        Load session from disk.

        Args:
            session_id: ID of session to load

        Returns:
            Session object

        Raises:
            FileNotFoundError: If session doesn't exist
            ValueError: If session file is corrupted
        """
        session_path = self.sessions_dir / f"{session_id}.json"

        if not session_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        try:
            session_json = session_path.read_text()
            session_dict = json.loads(session_json)

            # Parse datetime strings back to datetime objects
            session_dict["created_at"] = datetime.fromisoformat(
                session_dict["created_at"]
            )
            session_dict["updated_at"] = datetime.fromisoformat(
                session_dict["updated_at"]
            )

            # Parse message timestamps
            for msg in session_dict.get("messages", []):
                msg["timestamp"] = datetime.fromisoformat(msg["timestamp"])

            return Session(**session_dict)

        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted session file: {session_id}") from e
        except Exception as e:
            raise ValueError(f"Failed to load session {session_id}: {e}") from e

    def list_sessions(
        self,
        user_id: str | None = None,
        tax_year: int | None = None,
    ) -> list[Session]:
        """
        List all sessions, optionally filtered by user_id and/or tax_year.

        Args:
            user_id: Filter by user ID
            tax_year: Filter by tax year

        Returns:
            List of Session objects, sorted by updated_at (newest first)
        """
        print(f"User ID: {user_id}")
        print(f"Tax year: {tax_year}")
        print(f"Listing sessions in {self.sessions_dir}")
        for session_file in self.sessions_dir.glob("sess_*.json"):
            print(f"Session file: {session_file}")

        sessions = []

        for session_file in self.sessions_dir.glob("sess_*.json"):
            try:
                session = self.load_session(session_file.stem)

                # Apply filters
                if user_id and session.user_id != user_id:
                    continue
                if tax_year and session.tax_year != tax_year:
                    continue

                sessions.append(session)

            except Exception:
                # Skip corrupted sessions
                continue

        # Sort by updated_at, newest first
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        return sessions

    def delete_session(self, session_id: str) -> None:
        """
        Delete a session from disk.

        Args:
            session_id: ID of session to delete

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        session_path = self.sessions_dir / f"{session_id}.json"

        if not session_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        session_path.unlink()

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: ID of session to check

        Returns:
            True if session exists, False otherwise
        """
        session_path = self.sessions_dir / f"{session_id}.json"
        return session_path.exists()
