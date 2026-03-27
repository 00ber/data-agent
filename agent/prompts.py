"""Prompt assembly for the agent core."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from agent.environment import (
    AnalysisHandoff,
    Environment,
    ExecutionResult,
)
from agent.memory import Memory
from agent.tools import Tools

if TYPE_CHECKING:
    from agent.agent import CodeStep

SYSTEM_INSTRUCTIONS = """\
You are an analytics agent. Answer questions about the loaded data by writing Python code.

Use the available actions when they fit the task. Work like a notebook user:
perform one meaningful operation per step, inspect uncertain outputs before
relying on them (for example. inspecting the schema of a dataframe), 
and prefer assigning new variables instead of mutating prior
ones in place. Use schema(), head(), and sample() for intermediate inspection.
When you have enough information, you must call conclude_analysis()
with a stand-alone downstream handoff. The handoff is not polished UI copy.
It should state the findings directly, mention the important categories,
regions, rankings, or values when they matter, and reference relevant
published artifacts inline with @artifact_id mentions. If the question asks
about a correlation, relationship or likelihood,
comparison, or trend, do not stop at raw tables. Compute and explain a direct
measure such as a rate, difference, change, ranking, or normalized comparison.
"""

CONCLUDE_ANALYSIS_DESCRIPTION = """\
conclude_analysis(notes, artifact_ids=[])
Purpose: End the analysis loop with a downstream handoff for final response review.
Parameters:
- notes: A stand-alone downstream handoff that summarizes the findings directly. Do not write polished UI copy. Reference published artifacts inline with @artifact_id when they support the conclusion.
- artifact_ids: A list of published artifact ids that the handoff may reference.
Returns: No value.
Emits: no artifact
Example: chart_id = publish_chart(revenue_by_region, kind="bar", title="Revenue by Region")
conclude_analysis(
  "West leads revenue overall, with East close behind. The chart @"
  + chart_id
  + " shows the ranking clearly.",
  [chart_id],
)
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

{CONCLUDE_ANALYSIS_DESCRIPTION}

## Runtime

- Input tables are immutable and reset fresh on each execution step.
- Variables you create in the workspace persist across steps.
- After join() on tables with overlapping non-key column names, expect pandas-style suffixes such as _x and _y in the joined dataframe. Do not assume the original unsuffixed column name still exists.
- After an ambiguous join, use schema() before grouping, filtering, or sorting on guessed column names.
- Use schema(), head(), and sample() for internal inspection only.
- Use publish_chart(), publish_table(), and publish_stat() only for results you want the user to see.
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


def build_step_messages(
    code_step: CodeStep,
    result: ExecutionResult,
) -> list[dict[str, str]]:
    """Build the transient assistant/user messages for one finished step."""

    if result.analysis_handoff is not None:
        raise ValueError("Step messages should not be built for an analysis handoff.")

    assistant_lines = [
        f"Plan: {code_step.plan}",
        f"Code: {code_step.code}",
    ]
    if not result.is_error:
        assistant_lines.append(f"Result: {result.output}")

    if result.step_summary is not None:
        assistant_lines.append(result.step_summary)

    return [
        {"role": "assistant", "content": "\n".join(assistant_lines)},
        {"role": "user", "content": _build_step_follow_up(result)},
    ]


def _build_step_follow_up(result: ExecutionResult) -> str:
    """Build the next user instruction after one execution step."""

    if result.analysis_handoff is not None:
        raise ValueError("Step follow-up should not be built for an analysis handoff.")

    if result.is_error:
        return (
            f"Error: {result.output}\n\n"
            "Fix the issue and try again. Change the code or approach instead of "
            "repeating the same failing step."
        )

    artifact_count = sum(1 for event in result.events if event.kind == "artifact")
    if artifact_count > 0:
        return (
            f"Step produced {artifact_count} artifact(s) visible to the user."
            + (
                "\n\n" + result.step_summary
                if result.step_summary is not None
                else ""
            )
            + "\n\n"
            "If you have displayed all the results needed to answer the question, "
            "call conclude_analysis() with a stand-alone handoff that states the "
            "actual findings directly and references any supporting artifacts inline. "
            "If the question asks about a relationship or likelihood, make sure you "
            "computed and interpreted the relevant rate or comparison before ending. "
            "Otherwise, continue."
        )

    if result.step_summary is not None:
        return (
            "Step succeeded.\n\n"
            + result.step_summary
            + "\n\n"
            "Continue with the next step, or call conclude_analysis() "
            "if you have enough to answer the question."
        )

    return (
        "Step succeeded. Continue with the next step, or call conclude_analysis() "
        "if you have enough to answer the question."
    )


def build_finalization_messages(
    question: str,
    handoff: AnalysisHandoff,
    environment: Environment,
) -> list[dict[str, str]]:
    """Build the review-and-synthesis prompt for a completed analysis handoff."""

    artifact_by_id = {artifact.id: artifact for artifact in environment.artifacts}
    artifact_previews: list[str] = []

    for artifact_id in handoff.artifact_ids:
        artifact = artifact_by_id[artifact_id]
        artifact_previews.append(_format_artifact_preview(artifact))

    user_content = "\n\n".join(
        [
            f"Question:\n{question}",
            f"Analysis handoff:\n{handoff.notes}",
            "Artifact previews:\n"
            + ("\n\n".join(artifact_previews) if artifact_previews else "None"),
            (
                "Review instructions:\n"
                "- If the handoff is sufficient, return status='approved' and "
                "a final response with ordered sections.\n"
                "- If more work is needed, return status='needs_more_analysis' "
                "with a concrete critique.\n"
                "- For approved responses, include response.sections in the final reading order.\n"
                '- Use {"kind": "markdown", "markdown": "...", "artifact_id": null} '
                "for narrative sections.\n"
                '- Use {"kind": "artifact", "markdown": null, "artifact_id": "..."} '
                "for artifact references."
            ),
        ]
    )

    return [
        {
            "role": "system",
            "content": (
                "You are the final response review for an analytics agent. "
                "Decide whether the analysis handoff is ready to become the "
                "final user-facing response. Approve only if the handoff "
                "directly answers the question and the supporting artifacts fit "
                "the conclusion."
            ),
        },
        {"role": "user", "content": user_content},
    ]


def _format_artifact_preview(artifact: object) -> str:
    """Format one compact artifact preview for final response review."""

    kind = getattr(artifact, "kind")
    title = getattr(artifact, "title")
    data = getattr(artifact, "data")
    artifact_id = getattr(artifact, "id")

    if kind == "table":
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        shape = data.get("shape", [len(rows), len(columns)])
        preview_rows = rows[:8]
        return (
            f"{artifact_id} ({kind})\n"
            f"Title: {title}\n"
            f"Columns: {columns}\n"
            f"Rows: {shape[0]}\n"
            f"Preview rows: {preview_rows}"
        )

    if kind == "chart":
        records = data.get("records", [])
        return (
            f"{artifact_id} ({kind})\n"
            f"Title: {title}\n"
            f"Chart type: {data.get('chart_type')}\n"
            f"Columns: {data.get('columns', [])}\n"
            f"Preview records: {records[:8]}"
        )

    return (
        f"{artifact_id} ({kind})\n"
        f"Title: {title}\n"
        f"Value: {data}"
    )
