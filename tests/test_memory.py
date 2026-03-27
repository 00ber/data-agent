import pytest

from agent.memory import Memory
from agent.response import FinalResponse, ResponseSection


class TestMemory:
    def test_starts_empty(self):
        memory = Memory()

        assert memory.conversation_messages() == []

    def test_records_user_turn_as_conversation_message(self):
        memory = Memory()

        memory.record_user_turn("What drives revenue?")

        assert memory.conversation_messages() == [
            {"role": "user", "content": "What drives revenue?"},
        ]

    def test_rejects_blank_user_turn(self):
        memory = Memory()

        with pytest.raises(ValueError, match="User message must be a non-empty string."):
            memory.record_user_turn("   ")

    def test_records_assistant_response_as_assistant_message(self):
        memory = Memory()

        memory.record_user_turn("What drives revenue?")
        memory.record_assistant_response(
            FinalResponse(
                sections=[
                    ResponseSection(
                        kind="markdown",
                        markdown="West region leads revenue.",
                        artifact_id=None,
                    ),
                    ResponseSection(
                        kind="artifact",
                        markdown=None,
                        artifact_id="artifact_1",
                    ),
                ]
            ),
            artifact_titles={"artifact_1": "Revenue by region"},
        )

        assert memory.conversation_messages() == [
            {"role": "user", "content": "What drives revenue?"},
            {
                "role": "assistant",
                "content": "West region leads revenue.\n\n[Artifact: Revenue by region]",
            },
        ]

    def test_conversation_messages_returns_a_copy(self):
        memory = Memory()

        memory.record_user_turn("Hello")
        messages = memory.conversation_messages()
        messages[0]["content"] = "Mutated"

        assert memory.conversation_messages() == [
            {"role": "user", "content": "Hello"},
        ]
