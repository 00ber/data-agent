"""Conversation memory for the agent core."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.response import FinalResponse, response_to_conversation_text
from agent.validation import require_text


@dataclass
class Memory:
    """Conversation-only memory for one agent runtime."""

    _conversation_history: list[dict[str, str]] = field(default_factory=list)

    def record_user_turn(self, message: str) -> None:
        """Record one user turn in the conversation history."""

        normalized_message = require_text(message, "User message")
        self._conversation_history.append(
            {"role": "user", "content": normalized_message}
        )

    def record_assistant_response(
        self,
        response: FinalResponse,
        *,
        artifact_titles: dict[str, str] | None = None,
    ) -> None:
        """Record one final response as an assistant conversation turn."""

        self._conversation_history.append(
            {
                "role": "assistant",
                "content": response_to_conversation_text(
                    response,
                    artifact_titles=artifact_titles,
                ),
            }
        )

    def conversation_messages(self) -> list[dict[str, str]]:
        """Return a copy of the stored conversation turns."""

        return [message.copy() for message in self._conversation_history]
