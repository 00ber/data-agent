"""Core agent orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator

from agent.answer_blocks import serialize_answer_blocks
from agent.environment import Environment, ExecutionResult
from agent.events import Event
from agent.llm import LLM
from agent.memory import Memory
from agent.prompts import (
    build_conversation_messages,
    build_step_messages,
    build_system_prompt,
)
from agent.tools import Tools
from agent.validation import require_positive_int

_MAX_STEPS_EXHAUSTED = "Reached maximum steps without a final answer."


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
            code_step = await self.llm.generate(messages)
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

            if result.final_answer is not None:
                self.memory.record_final_answer(
                    result.final_answer,
                    artifact_titles={
                        artifact.id: artifact.title
                        for artifact in self.environment.artifacts
                    },
                )
                yield Event(
                    "answer",
                    {"blocks": serialize_answer_blocks(result.final_answer)},
                )
                return

            messages.extend(build_step_messages(code_step, result))

        yield Event("error", {"text": _MAX_STEPS_EXHAUSTED})
