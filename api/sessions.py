"""API-layer in-memory session store."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from agent import Agent, Environment, ExecutionSandbox, Memory, OpenAILLM, Tools

DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.0


@dataclass
class AgentSession:
    """One live API session backed by a reusable agent instance."""

    id: str
    agent: Agent


class InMemoryAgentSessionStore:
    """Store live agent sessions in memory for one API process."""

    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = {}

    def create(
        self,
        *,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """Create one live agent session and return its ID."""

        session_id = uuid.uuid4().hex[:12]
        agent = Agent(
            llm=OpenAILLM(model=model, temperature=temperature),
            memory=Memory(),
            environment=Environment(inputs={}, sandbox=ExecutionSandbox()),
            tools=Tools(),
        )
        self._sessions[session_id] = AgentSession(id=session_id, agent=agent)
        return session_id

    def get(self, session_id: str) -> AgentSession:
        """Retrieve one live session by ID."""

        if session_id not in self._sessions:
            raise KeyError(session_id)

        return self._sessions[session_id]

    def delete(self, session_id: str) -> None:
        """Delete one session if it exists."""

        self._sessions.pop(session_id, None)
