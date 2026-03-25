from dataclasses import FrozenInstanceError

import pytest

from agent.memory import Memory, StepRecord


class TestStepRecord:
    def test_stores_step_fields(self):
        record = StepRecord(
            plan="Aggregate revenue by region",
            code="grouped = ...",
            output="West leads revenue.",
            is_error=False,
        )

        assert record.plan == "Aggregate revenue by region"
        assert record.code == "grouped = ..."
        assert record.output == "West leads revenue."
        assert record.is_error is False

    def test_is_immutable(self):
        record = StepRecord(
            plan="Inspect data",
            code="print(df.head())",
            output="OK",
            is_error=False,
        )

        with pytest.raises(FrozenInstanceError):
            record.plan = "Mutated"


class TestMemory:
    def test_starts_empty(self):
        memory = Memory()

        assert memory.step_history == []
        assert memory.final_answers == []
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

    def test_records_step_in_step_history(self):
        memory = Memory()

        record = memory.record_step(
            plan="Inspect the sales table",
            code="print(sales.head())",
            output="Printed five rows.",
        )

        assert record == StepRecord(
            plan="Inspect the sales table",
            code="print(sales.head())",
            output="Printed five rows.",
            is_error=False,
        )
        assert memory.step_history == [record]

    def test_records_error_step(self):
        memory = Memory()

        record = memory.record_step(
            plan="Divide by zero",
            code="1 / 0",
            output="ZeroDivisionError: division by zero",
            is_error=True,
        )

        assert record.is_error is True
        assert "ZeroDivisionError" in record.output

    def test_rejects_blank_step_plan(self):
        memory = Memory()

        with pytest.raises(ValueError, match="Step plan must be a non-empty string."):
            memory.record_step(plan=" ", code="print(1)")

    def test_rejects_blank_step_code(self):
        memory = Memory()

        with pytest.raises(ValueError, match="Step code must be a non-empty string."):
            memory.record_step(plan="Inspect", code=" ")

    def test_step_history_does_not_leak_into_conversation_messages(self):
        memory = Memory()

        memory.record_user_turn("What drives revenue?")
        memory.record_step(
            plan="Inspect revenue",
            code="print(revenue.sum())",
            output="42",
        )

        assert memory.conversation_messages() == [
            {"role": "user", "content": "What drives revenue?"},
        ]

    def test_records_final_answer_as_assistant_message(self):
        memory = Memory()

        memory.record_user_turn("What drives revenue?")
        memory.record_final_answer("West region leads revenue.")

        assert memory.conversation_messages() == [
            {"role": "user", "content": "What drives revenue?"},
            {"role": "assistant", "content": "West region leads revenue."},
        ]

    def test_tracks_final_answers_separately(self):
        memory = Memory()

        memory.record_final_answer("West region leads revenue.")

        assert memory.final_answers == ["West region leads revenue."]

    def test_rejects_blank_final_answer(self):
        memory = Memory()

        with pytest.raises(ValueError, match="Final answer must be a non-empty string."):
            memory.record_final_answer("")

    def test_conversation_messages_returns_a_copy(self):
        memory = Memory()

        memory.record_user_turn("Hello")
        messages = memory.conversation_messages()
        messages[0]["content"] = "Mutated"

        assert memory.conversation_messages() == [
            {"role": "user", "content": "Hello"},
        ]
