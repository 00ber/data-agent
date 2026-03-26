"""Structured final-answer blocks for inline narrative and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from agent.validation import require_text


@dataclass(frozen=True)
class MarkdownAnswerBlock:
    """One markdown narrative block in a final answer."""

    content: str


@dataclass(frozen=True)
class ArtifactAnswerBlock:
    """One inline artifact reference in a final answer."""

    artifact_id: str


AnswerBlock: TypeAlias = MarkdownAnswerBlock | ArtifactAnswerBlock


def coerce_answer_blocks(
    value: Any,
    *,
    available_artifact_ids: set[str],
) -> list[AnswerBlock]:
    """Validate and coerce one raw final-answer payload into typed blocks."""

    if not isinstance(value, list) or len(value) == 0:
        raise ValueError("Final answer must contain at least one block.")

    blocks: list[AnswerBlock] = []
    for raw_block in value:
        if not isinstance(raw_block, dict):
            raise ValueError("Each final answer block must be a dictionary.")

        raw_type = require_text(raw_block.get("type"), "Answer block type")
        if raw_type == "markdown":
            blocks.append(
                MarkdownAnswerBlock(
                    content=require_text(
                        raw_block.get("content"),
                        "Markdown answer block content",
                    )
                )
            )
            continue

        if raw_type == "artifact":
            artifact_id = require_text(
                raw_block.get("artifact_id"),
                "Artifact answer block artifact_id",
            )
            if artifact_id not in available_artifact_ids:
                raise ValueError(f"Unknown artifact reference '{artifact_id}'.")
            blocks.append(ArtifactAnswerBlock(artifact_id=artifact_id))
            continue

        raise ValueError(f"Unsupported answer block type '{raw_type}'.")

    return blocks


def serialize_answer_blocks(blocks: list[AnswerBlock]) -> list[dict[str, str]]:
    """Serialize typed answer blocks for events and JSON transport."""

    payload: list[dict[str, str]] = []
    for block in blocks:
        if isinstance(block, MarkdownAnswerBlock):
            payload.append({"type": "markdown", "content": block.content})
        else:
            payload.append({"type": "artifact", "artifact_id": block.artifact_id})
    return payload


def answer_blocks_to_conversation_text(
    blocks: list[AnswerBlock],
    *,
    artifact_titles: dict[str, str] | None = None,
) -> str:
    """Render one final answer to assistant-text form for conversation memory."""

    parts: list[str] = []
    titles = artifact_titles or {}

    for block in blocks:
        if isinstance(block, MarkdownAnswerBlock):
            parts.append(block.content)
        else:
            title = titles.get(block.artifact_id, block.artifact_id)
            parts.append(f"[Artifact: {title}]")

    return "\n\n".join(parts)
