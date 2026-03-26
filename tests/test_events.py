from typing import get_args

from agent.events import Event, EventKind


class TestEventKind:
    def test_includes_all_streamed_event_kinds(self):
        event_kinds = get_args(EventKind)

        assert event_kinds == (
            "thinking",
            "code",
            "artifact",
            "reviewing",
            "result",
            "answer",
            "error",
        )


class TestEvent:
    def test_stores_kind_and_data(self):
        event = Event("thinking", {"text": "Analyzing data..."})

        assert event.kind == "thinking"
        assert event.data == {"text": "Analyzing data..."}

    def test_stores_artifact_payload(self):
        event = Event(
            "artifact",
            {
                "id": "artifact-1",
                "kind": "table",
                "title": "Revenue by Region",
            },
        )

        assert event.kind == "artifact"
        assert event.data["id"] == "artifact-1"
        assert event.data["kind"] == "table"

    def test_stores_answer_payload(self):
        event = Event("answer", {"text": "West drives the most revenue."})

        assert event.kind == "answer"
        assert event.data["text"] == "West drives the most revenue."

    def test_stores_reviewing_payload(self):
        event = Event("reviewing", {"text": "Finalizing response."})

        assert event.kind == "reviewing"
        assert event.data["text"] == "Finalizing response."
