"""LLM transport for generating the next code step."""

from __future__ import annotations

from typing import Any, Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict

from agent.validation import require_text


class CodeStep(BaseModel):
    """Structured LLM output for one agent step."""

    model_config = ConfigDict(extra="forbid")

    plan: str
    code: str


class LLM(Protocol):
    """Protocol for generating the next structured code step."""

    async def generate(self, messages: list[dict[str, str]]) -> CodeStep:
        """Generate the next structured code step from conversation messages."""


class OpenAILLM:
    """OpenAI-backed generator for structured code steps."""

    def __init__(
        self,
        model: str,
        *,
        temperature: float = 0.0,
        client: Any | None = None,
    ) -> None:
        self.model = require_text(model, "Model name")
        self.temperature = temperature
        self.client = client or AsyncOpenAI()

    async def generate(self, messages: list[dict[str, str]]) -> CodeStep:
        """Generate the next structured code step from conversation messages."""

        response = await self.client.responses.parse(
            model=self.model,
            input=messages,
            text_format=CodeStep,
            temperature=self.temperature,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("LLM response did not contain a parsed code step.")

        return parsed
