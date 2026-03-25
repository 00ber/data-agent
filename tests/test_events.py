import pytest

from agent.events import Event, FinalAnswer


class TestEvent:
    def test_create_thinking_event(self):
        event = Event("thinking", {"text": "Analyzing data..."})

        assert event.kind == "thinking"
        assert event.data == {"text": "Analyzing data..."}

    def test_create_artifact_event(self):
        event = Event("artifact", {"id": "a1", "kind": "table", "title": "Sales"})

        assert event.kind == "artifact"
        assert event.data["id"] == "a1"


class TestFinalAnswer:
    def test_stores_answer_text(self):
        exc = FinalAnswer("Revenue is $8.2M")

        assert exc.answer == "Revenue is $8.2M"

    def test_is_exception(self):
        exc = FinalAnswer("done")

        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(FinalAnswer) as exc_info:
            raise FinalAnswer("The answer is 42")

        assert exc_info.value.answer == "The answer is 42"
