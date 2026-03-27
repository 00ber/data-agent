import pytest

from agent.response import (
    FinalResponse,
    ResponseSection,
    response_to_conversation_text,
    serialize_final_response,
    validate_final_response_artifacts,
)


class TestResponseSection:
    def test_accepts_markdown_section(self):
        section = ResponseSection(
            kind="markdown",
            markdown="## Summary\n\nConsumer leads.",
            artifact_id=None,
        )

        assert section.kind == "markdown"
        assert section.markdown == "## Summary\n\nConsumer leads."
        assert section.artifact_id is None

    def test_accepts_artifact_section(self):
        section = ResponseSection(
            kind="artifact",
            markdown=None,
            artifact_id="artifact_123",
        )

        assert section.kind == "artifact"
        assert section.markdown is None
        assert section.artifact_id == "artifact_123"

    def test_rejects_unknown_section_kind(self):
        with pytest.raises(ValueError):
            ResponseSection(kind="table", markdown="bad", artifact_id=None)


class TestFinalResponse:
    def test_rejects_empty_sections(self):
        with pytest.raises(ValueError, match="Final response must contain at least one section."):
            FinalResponse(sections=[])

    def test_validates_artifact_references(self):
        response = FinalResponse(
            sections=[
                ResponseSection(
                    kind="artifact",
                    markdown=None,
                    artifact_id="artifact_999",
                )
            ]
        )

        with pytest.raises(ValueError, match="Unknown artifact reference 'artifact_999'"):
            validate_final_response_artifacts(
                response,
                available_artifact_ids={"artifact_123"},
            )


class TestSerializeFinalResponse:
    def test_serializes_sections_for_events(self):
        response = FinalResponse(
            sections=[
                ResponseSection(
                    kind="markdown",
                    markdown="Hello",
                    artifact_id=None,
                ),
                ResponseSection(
                    kind="artifact",
                    markdown=None,
                    artifact_id="artifact_123",
                ),
            ]
        )

        payload = serialize_final_response(response)

        assert payload == [
            {"type": "markdown", "content": "Hello"},
            {"type": "artifact", "artifact_id": "artifact_123"},
        ]


class TestResponseToConversationText:
    def test_renders_markdown_and_artifact_references_for_memory(self):
        response = FinalResponse(
            sections=[
                ResponseSection(
                    kind="markdown",
                    markdown="Consumer leads.",
                    artifact_id=None,
                ),
                ResponseSection(
                    kind="artifact",
                    markdown=None,
                    artifact_id="artifact_123",
                ),
            ]
        )

        text = response_to_conversation_text(
            response,
            artifact_titles={"artifact_123": "Revenue by segment"},
        )

        assert "Consumer leads." in text
        assert "[Artifact: Revenue by segment]" in text
