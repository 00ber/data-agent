import pytest

from agent.answer_blocks import (
    ArtifactAnswerBlock,
    MarkdownAnswerBlock,
    answer_blocks_to_conversation_text,
    coerce_answer_blocks,
    serialize_answer_blocks,
)


class TestCoerceAnswerBlocks:
    def test_accepts_markdown_and_artifact_blocks(self):
        blocks = coerce_answer_blocks(
            [
                {"type": "markdown", "content": "## Summary\n\nConsumer leads."},
                {"type": "artifact", "artifact_id": "artifact_123"},
            ],
            available_artifact_ids={"artifact_123"},
        )

        assert blocks == [
            MarkdownAnswerBlock(content="## Summary\n\nConsumer leads."),
            ArtifactAnswerBlock(artifact_id="artifact_123"),
        ]

    def test_rejects_unknown_artifact_reference(self):
        with pytest.raises(ValueError, match="Unknown artifact reference 'artifact_999'"):
            coerce_answer_blocks(
                [{"type": "artifact", "artifact_id": "artifact_999"}],
                available_artifact_ids={"artifact_123"},
            )

    def test_rejects_unknown_block_type(self):
        with pytest.raises(ValueError, match="Unsupported answer block type 'table'"):
            coerce_answer_blocks(
                [{"type": "table", "content": "bad"}],
                available_artifact_ids=set(),
            )


class TestSerializeAnswerBlocks:
    def test_serializes_blocks_for_events(self):
        payload = serialize_answer_blocks(
            [
                MarkdownAnswerBlock(content="Hello"),
                ArtifactAnswerBlock(artifact_id="artifact_123"),
            ]
        )

        assert payload == [
            {"type": "markdown", "content": "Hello"},
            {"type": "artifact", "artifact_id": "artifact_123"},
        ]


class TestAnswerBlocksToConversationText:
    def test_renders_markdown_and_artifact_references_for_memory(self):
        text = answer_blocks_to_conversation_text(
            [
                MarkdownAnswerBlock(content="Consumer leads."),
                ArtifactAnswerBlock(artifact_id="artifact_123"),
            ],
            artifact_titles={"artifact_123": "Revenue by segment"},
        )

        assert "Consumer leads." in text
        assert "[Artifact: Revenue by segment]" in text
