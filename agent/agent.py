"""The agent loop: LLM → code → sandbox → events."""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Awaitable
from typing import Any

import numpy as np
import pandas as pd
from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.events import Event, FinalAnswer
from agent.prompts import build_prompt
from agent.sandbox import execute
from agent.session import Session
from agent.tools import Tools


class CodeStep(BaseModel):
    """Structured output from the LLM: thinking + code."""

    plan: str
    code: str


async def _call_llm(
    messages: list[dict], *, model: str, temperature: float
) -> CodeStep:
    """Call OpenAI with structured output to get a CodeStep."""
    client = AsyncOpenAI()
    response = await client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=CodeStep,
        temperature=temperature,
    )
    return response.choices[0].message.parsed


def _build_env(tools: Tools, session: Session) -> dict[str, Any]:
    """Build the sandbox namespace from tools and session."""
    env: dict[str, Any] = {}

    # DataFrames by name (copies so sandbox code can't mutate originals)
    for name, df in session.tables.items():
        env[name] = df.copy()

    # Tool functions (public methods)
    for attr_name in dir(tools):
        if not attr_name.startswith("_") and callable(getattr(tools, attr_name)):
            env[attr_name] = getattr(tools, attr_name)

    # Safe libraries
    env["pd"] = pd
    env["np"] = np

    return env


async def run(
    session: Session,
    message: str,
    *,
    llm: Callable[..., Awaitable[CodeStep]] | None = None,
) -> AsyncIterator[Event]:
    """Run the agent loop, yielding events.

    Args:
        session: The current session state.
        message: The user's question.
        llm: Optional LLM callable for testing. Defaults to OpenAI.

    Yields:
        Event objects: thinking, code, artifact, result, answer, error.
    """
    if llm is None:
        async def llm(messages, **kwargs):
            return await _call_llm(
                messages,
                model=session.config.model,
                temperature=session.config.temperature,
            )

    # Collect emitted events (artifacts emitted by tools)
    emitted: list[Event] = []

    def emit(event: Event) -> None:
        emitted.append(event)

    tools = Tools(session, emit=emit)
    system_prompt = build_prompt(session.tables, tools)
    env = _build_env(tools, session)

    # Add user message to history
    session.history.append({"role": "user", "content": message})

    messages = [
        {"role": "system", "content": system_prompt},
        *session.history,
    ]

    for step_num in range(session.config.max_steps):
        # Get code step from LLM
        code_step = await llm(messages)

        # Yield thinking and code events
        yield Event("thinking", {"text": code_step.plan})
        yield Event("code", {"text": code_step.code})

        # Execute in sandbox
        emitted.clear()
        try:
            result = execute(code_step.code, env)
        except FinalAnswer as fa:
            # Yield any artifacts that were emitted before final_answer
            for event in emitted:
                yield event
            yield Event("answer", {"text": fa.answer})
            session.history.append({
                "role": "assistant",
                "content": fa.answer,
            })
            return

        # Yield any artifacts emitted by tools
        for event in emitted:
            yield event

        if result.is_error:
            yield Event("error", {"text": result.output})
            # Feed error back to LLM
            messages.append({
                "role": "assistant",
                "content": f"Plan: {code_step.plan}\nCode: {code_step.code}",
            })
            messages.append({
                "role": "user",
                "content": f"Error: {result.output}\n\nPlease fix the issue and try again.",
            })
        else:
            yield Event("result", {"text": result.output})
            messages.append({
                "role": "assistant",
                "content": f"Plan: {code_step.plan}\nCode: {code_step.code}\nResult: {result.output}",
            })
            artifact_count = len(emitted)
            if artifact_count > 0:
                messages.append({
                    "role": "user",
                    "content": (
                        f"Step produced {artifact_count} artifact(s) visible to the user. "
                        "If you have displayed all the results needed to answer the question, "
                        "call final_answer() with a brief summary. Otherwise, continue."
                    ),
                })
            else:
                messages.append({
                    "role": "user",
                    "content": (
                        "Step succeeded. Continue with the next step, or call "
                        "final_answer() if you have enough to answer the question."
                    ),
                })

    # If we exit the loop without final_answer, record in history
    session.history.append({
        "role": "assistant",
        "content": "Reached maximum steps without a final answer.",
    })
