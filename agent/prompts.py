"""Prompt assembly for the agent core."""

from __future__ import annotations

import inspect

from agent.environment import Environment, ExecutionResult
from agent.llm import CodeStep
from agent.memory import Memory
from agent.tools import Tools

SYSTEM_INSTRUCTIONS = """\
You are an analytics agent. Answer questions about the loaded data by writing Python code.

Use the available actions when they fit the task. Use print() for intermediate
inspection. When you have enough information, you must call final_answer() with
a brief conclusion that states the findings directly. Do not just say that the
answer is shown in a table or chart. State the concrete findings, including the
most important categories, regions, rankings, or values when they matter.
"""

FINAL_ANSWER_DESCRIPTION = """\
final_answer(answer)
Purpose: End the run with the final user-facing answer.
Parameters:
- answer: Final conclusion returned to the user.
Returns: No value.
Emits: no artifact
Example: final_answer("West region leads revenue growth.")
"""


def describe_tool(method: object) -> str:
    """Describe one public tool method for inclusion in the system prompt."""

    signature = inspect.signature(method)
    parameter_names = [
        name
        for name in signature.parameters
        if name not in {"self", "execution_context"}
    ]
    tool_name = getattr(method, "__name__", str(method))
    docstring = inspect.getdoc(method) or ""
    return f"{tool_name}({', '.join(parameter_names)})\n{docstring}"


def describe_tools(tools: Tools) -> str:
    """Describe all public tool methods that the model may call."""

    return "\n\n".join(
        describe_tool(getattr(tools, action_name))
        for action_name in tools.ACTION_NAMES
    )


def build_system_prompt(environment: Environment, tools: Tools) -> str:
    """Build the system prompt from environment and tool descriptions."""

    return f"""{SYSTEM_INSTRUCTIONS}

## Input Tables

Reference input tables by their unique names exactly as listed below.

{environment.describe()}

## Available Actions

{describe_tools(tools)}

{FINAL_ANSWER_DESCRIPTION}

## Runtime

- Input tables are immutable and reset fresh on each execution step.
- Variables you create in the workspace persist across steps.
- After join() on tables with overlapping non-key column names, expect pandas-style suffixes such as _x and _y in the joined dataframe. Do not assume the original unsuffixed column name still exists.
- Use show_chart(), show_table(), and show_stat() only for results you want the user to see.
- Libraries in scope: pd (pandas), np (numpy)
"""


def build_conversation_messages(
    system_prompt: str,
    memory: Memory,
) -> list[dict[str, str]]:
    """Build the full message list for the next LLM call."""

    return [
        {"role": "system", "content": system_prompt},
        *memory.conversation_messages(),
    ]


def build_step_feedback(result: ExecutionResult) -> str:
    """Build the follow-up user message after one execution step."""

    if result.final_answer is not None:
        raise ValueError("Step feedback should not be built for a final answer.")

    if result.is_error:
        return (
            f"Error: {result.output}\n\n"
            "Fix the issue and try again. Change the code or approach instead of "
            "repeating the same failing step."
        )

    artifact_count = sum(1 for event in result.events if event.kind == "artifact")
    if artifact_count > 0:
        return (
            f"Step produced {artifact_count} artifact(s) visible to the user. "
            "If you have displayed all the results needed to answer the question, "
            "call final_answer() and summarize the actual findings, not just that "
            "the answer is visible. Otherwise, continue."
        )

    return (
        "Step succeeded. Continue with the next step, or call final_answer() "
        "if you have enough to answer the question."
    )


def build_step_messages(
    code_step: CodeStep,
    result: ExecutionResult,
) -> list[dict[str, str]]:
    """Build the transient assistant/user messages for one finished step."""

    if result.final_answer is not None:
        raise ValueError("Step messages should not be built for a final answer.")

    assistant_lines = [
        f"Plan: {code_step.plan}",
        f"Code: {code_step.code}",
    ]
    if not result.is_error:
        assistant_lines.append(f"Result: {result.output}")

    return [
        {"role": "assistant", "content": "\n".join(assistant_lines)},
        {"role": "user", "content": build_step_feedback(result)},
    ]
