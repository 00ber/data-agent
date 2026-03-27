"""Core agent orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, cast

from pydantic import BaseModel, ConfigDict

from agent.environment import AnalysisHandoff, Environment
from agent.events import Event
from agent.llm import LLM
from agent.memory import Memory
from agent.prompts import (
    build_conversation_messages,
    build_finalization_messages,
    build_step_messages,
    build_system_prompt,
)
from agent.response import (
    FinalResponse,
    FinalResponseReview,
    serialize_final_response,
    validate_final_response_artifacts,
)
from agent.tools import Tools
from agent.validation import require_positive_int

_MAX_STEPS_EXHAUSTED = "Reached maximum steps without a final answer."


class CodeStep(BaseModel):
    """Structured LLM output for one agent step."""

    model_config = ConfigDict(extra="forbid")

    plan: str
    code: str


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
            for event in result.events:
                yield event

            if result.analysis_handoff is not None:
                yield Event(
                    "reviewing",
                    {"text": "Finalizing response from the analysis handoff."},
                )
                final_response = await self._review_analysis_handoff(
                    message=message,
                    handoff=result.analysis_handoff,
                    messages=messages,
                )
                if final_response is None:
                    continue

                self.memory.record_assistant_response(
                    final_response,
                    artifact_titles=self._artifact_titles(),
                )
                yield Event(
                    "answer",
                    {"blocks": serialize_final_response(final_response)},
                )
                return

            messages.extend(build_step_messages(code_step, result))

        yield Event("error", {"text": _MAX_STEPS_EXHAUSTED})

    async def _review_analysis_handoff(
        self,
        *,
        message: str,
        handoff: AnalysisHandoff,
        messages: list[dict[str, str]],
    ) -> FinalResponse | None:
        """Review one analysis handoff and either return a final response or continue the loop."""

        review = await self._parse_final_response_review(message, handoff)
        if review.status == "needs_more_analysis":
            self._append_review_feedback(
                messages,
                handoff.notes,
                cast(str, review.critique),
            )
            return None

        final_response = cast(FinalResponse, review.response)

        validate_final_response_artifacts(
            final_response,
            available_artifact_ids={artifact.id for artifact in self.environment.artifacts},
        )
        return final_response

    async def _parse_final_response_review(
        self,
        message: str,
        handoff: AnalysisHandoff,
    ) -> FinalResponseReview:
        """Ask the review model whether one analysis handoff is ready for the user."""

        review_messages = build_finalization_messages(message, handoff, self.environment)
        return await self.llm.parse(review_messages, FinalResponseReview)

    def _append_review_feedback(
        self,
        messages: list[dict[str, str]],
        handoff_notes: str,
        critique: str,
    ) -> None:
        """Append one rejected review back into the main agent loop."""

        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": f"Analysis handoff: {handoff_notes}",
                },
                {
                    "role": "user",
                    "content": f"Final response review: {critique}",
                },
            ]
        )

    def _artifact_titles(self) -> dict[str, str]:
        """Return artifact titles for rendering final responses into conversation text."""

        return {
            artifact.id: artifact.title
            for artifact in self.environment.artifacts
        }
