"""LLM transport for parsing structured responses."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.validation import require_text

T = TypeVar("T", bound=BaseModel)


class LLM(Protocol):
    """Protocol for parsing one structured response model from messages."""

    async def parse(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
    ) -> T:
        """Parse one structured response model from conversation messages."""


class OpenAILLM:
    """OpenAI-backed parser for structured responses."""

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

    async def parse(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
    ) -> T:
        """Parse one structured response model from conversation messages."""

        response = await self.client.responses.parse(
            model=self.model,
            input=messages,
            text_format=response_model,
            temperature=self.temperature,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError(
                f"LLM response did not contain a parsed {response_model.__name__}."
            )

        return parsed
