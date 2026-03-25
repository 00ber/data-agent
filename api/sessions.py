"""In-memory session manager."""
from __future__ import annotations

import uuid

from agent.session import AgentConfig, Session


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, config: AgentConfig | None = None) -> str:
        """Create a new session and return its ID."""
        session_id = uuid.uuid4().hex[:12]
        session = Session(config=config or AgentConfig())
        self._sessions[session_id] = session
        return session_id

    def get(self, session_id: str) -> Session:
        """Retrieve a session by ID. Raises KeyError if not found."""
        if session_id not in self._sessions:
            raise KeyError(session_id)
        return self._sessions[session_id]

    def destroy(self, session_id: str) -> None:
        """Remove a session."""
        self._sessions.pop(session_id, None)
