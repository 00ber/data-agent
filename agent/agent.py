"""Core agent orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from agent.answer_blocks import coerce_answer_blocks, serialize_answer_blocks
from agent.environment import Environment, ExecutionResult
from agent.events import Event
from agent.llm import LLM
from agent.memory import Memory
from agent.prompts import (
    build_conversation_messages,
    build_finalization_messages,
    build_step_messages,
    build_system_prompt,
)
from agent.tools import Tools
from agent.validation import require_optional_text, require_positive_int, require_text

_MAX_STEPS_EXHAUSTED = "Reached maximum steps without a final answer."


class CodeStep(BaseModel):
    """Structured LLM output for one agent step."""

    model_config = ConfigDict(extra="forbid")

    plan: str
    code: str


class FinalResponseBlock(BaseModel):
    """One typed final-response block returned from the review LLM call."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["markdown", "artifact"]
    content: str | None
    artifact_id: str | None

    @model_validator(mode="after")
    def validate_shape(self) -> "FinalResponseBlock":
        """Require fields that match the chosen block type."""

        if self.type == "markdown":
            require_text(self.content, "Final response markdown block content")
            if self.artifact_id is not None:
                raise ValueError(
                    "Markdown final response blocks must not include artifact_id."
                )
            return self

        if self.content is not None:
            raise ValueError("Artifact final response blocks must not include content.")

        require_text(
            self.artifact_id,
            "Final response artifact block artifact_id",
        )
        return self


class FinalResponseReview(BaseModel):
    """Structured review result for the downstream analysis handoff."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "needs_more_analysis"]
    critique: str | None
    blocks: list[FinalResponseBlock]

    @model_validator(mode="after")
    def validate_outcome(self) -> "FinalResponseReview":
        """Require critique or blocks that match the review status."""

        if self.status == "approved":
            if self.critique is not None:
                raise ValueError(
                    "Approved final response reviews must not include critique."
                )
            if len(self.blocks) == 0:
                raise ValueError(
                    "Approved final response reviews must include at least one block."
                )
            return self

        require_optional_text(self.critique, "Final response review critique")
        if self.critique is None:
            raise ValueError(
                "Final response reviews that need more analysis must include critique."
            )
        if len(self.blocks) != 0:
            raise ValueError(
                "Final response reviews that need more analysis must not include blocks."
            )
        return self


@dataclass
class Agent:
    """Reusable orchestrator for one agent runtime."""

    llm: LLM
    memory: Memory
    environment: Environment
    tools: Tools = field(default_factory=Tools)
    max_steps: int = 30

    def __post_init__(self) -> None:
        self.max_steps = require_positive_int(self.max_steps, "Max steps")
        self.tools.register_with(self.environment)

    async def run(self, message: str) -> AsyncIterator[Event]:
        """Run the agent loop for one user message."""

        self.memory.record_user_turn(message)
        system_prompt = build_system_prompt(self.environment, self.tools)
        messages = build_conversation_messages(system_prompt, self.memory)

        for _ in range(self.max_steps):
            code_step = await self.llm.parse(messages, CodeStep)
            yield Event("thinking", {"text": code_step.plan})
            yield Event("code", {"text": code_step.code})

            result = self.environment.execute(code_step.code)
            self.memory.record_step(
                plan=code_step.plan,
                code=code_step.code,
                output=result.output,
                is_error=result.is_error,
            )

            for event in result.events:
                yield event

            if result.analysis_handoff is not None:
                yield Event(
                    "reviewing",
                    {"text": "Finalizing response from the analysis handoff."},
                )
                review = await self.llm.parse(
                    build_finalization_messages(message, result.analysis_handoff, self.environment),
                    FinalResponseReview,
                )

                if review.status == "needs_more_analysis":
                    if review.critique is None or review.critique.strip() == "":
                        raise ValueError(
                            "Final response review must include critique when more analysis is needed."
                        )
                    messages.extend(
                        [
                            {
                                "role": "assistant",
                                "content": f"Analysis handoff: {result.analysis_handoff.notes}",
                            },
                            {
                                "role": "user",
                                "content": f"Final response review: {review.critique}",
                            },
                        ]
                    )
                    continue

                final_answer = coerce_answer_blocks(
                    _serialize_review_blocks(review.blocks),
                    available_artifact_ids={
                        artifact.id for artifact in self.environment.artifacts
                    },
                )
                self.memory.record_final_answer(
                    final_answer,
                    artifact_titles={
                        artifact.id: artifact.title
                        for artifact in self.environment.artifacts
                    },
                )
                yield Event(
                    "answer",
                    {"blocks": serialize_answer_blocks(final_answer)},
                )
                return

            messages.extend(build_step_messages(code_step, result))

        yield Event("error", {"text": _MAX_STEPS_EXHAUSTED})


def _serialize_review_blocks(
    blocks: list[FinalResponseBlock],
) -> list[dict[str, str]]:
    """Convert typed review blocks into the raw answer-block payload shape."""

    payload: list[dict[str, str]] = []
    for block in blocks:
        if block.type == "markdown":
            payload.append(
                {
                    "type": "markdown",
                    "content": require_text(
                        block.content,
                        "Final response markdown block content",
                    ),
                }
            )
            continue

        payload.append(
            {
                "type": "artifact",
                "artifact_id": require_text(
                    block.artifact_id,
                    "Final response artifact block artifact_id",
                ),
            }
        )

    return payload
