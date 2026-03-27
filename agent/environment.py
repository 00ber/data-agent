"""Runtime environment for agent code execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Callable, Literal
import uuid

import numpy as np
import pandas as pd

from agent.events import Event
from agent.sandbox import ExecutionSandbox, SandboxResult, SandboxStop
from agent.validation import require_text

ArtifactKind = Literal["table", "chart", "stat"]

_RESERVED_RUNTIME_NAMES = {"pd", "np", "conclude_analysis"}
_ARTIFACT_MENTION_PATTERN = re.compile(r"(?<!\w)@(artifact_[A-Za-z0-9_]+)\b")


@dataclass(frozen=True)
class Artifact:
    """One user-visible artifact produced during execution."""

    id: str
    kind: ArtifactKind
    title: str
    data: dict[str, Any]


@dataclass
class AnalysisHandoff:
    """Structured downstream handoff produced when analysis is complete."""

    notes: str
    artifact_ids: list[str]


@dataclass
class ExecutionResult:
    """Structured result returned from one environment execution."""

    events: list[Event]
    output: str | None
    is_error: bool
    analysis_handoff: AnalysisHandoff | None
    step_summary: str | None


@dataclass
class ExecutionContext:
    """Step-local execution state built fresh for each environment execution."""

    environment: "Environment"
    pending_events: list[Event] = field(default_factory=list)
    before_dataframe_metadata: dict[
        str,
        tuple[int, tuple[Any, ...], tuple[tuple[Any, str], ...]],
    ] = field(init=False)

    def __post_init__(self) -> None:
        """Snapshot dataframe metadata so the step can report what changed."""

        self.before_dataframe_metadata = self._snapshot_dataframe_metadata(
            self.environment.workspace
        )

    def build_namespace(self) -> dict[str, Any]:
        """Build the step namespace from environment state and bound actions."""

        namespace = {
            name: table.copy(deep=True)
            for name, table in self.environment.inputs.items()
        }
        namespace.update(self.environment.workspace)
        namespace.update(self._bind_actions())
        namespace["conclude_analysis"] = self.conclude_analysis
        namespace["pd"] = pd
        namespace["np"] = np
        return namespace

    def publish_artifact(
        self,
        kind: ArtifactKind,
        title: str,
        data: dict[str, Any],
    ) -> Artifact:
        """Store one artifact and emit its event for this execution only."""

        artifact = self.environment._store_artifact(kind, title, data)
        self.pending_events.append(
            Event(
                "artifact",
                {
                    "id": artifact.id,
                    "kind": artifact.kind,
                    "title": artifact.title,
                    "data": artifact.data,
                },
            )
        )
        return artifact

    def conclude_analysis(
        self,
        notes: Any,
        artifact_ids: Any | None = None,
    ) -> None:
        """Stop this execution with a validated downstream analysis handoff."""

        normalized_notes = require_text(notes, "Analysis handoff notes")
        normalized_artifact_ids = self._coerce_artifact_ids(artifact_ids)
        self._validate_artifact_ids_exist(normalized_artifact_ids)
        self._validate_artifact_mentions(normalized_notes, normalized_artifact_ids)
        raise SandboxStop(
            AnalysisHandoff(
                notes=normalized_notes,
                artifact_ids=normalized_artifact_ids,
            )
        )

    def success_outcome(self, result: SandboxResult) -> ExecutionResult:
        """Build the outcome for one successful sandbox execution."""

        events = [*self.pending_events, Event("result", {"text": result.output})]
        return ExecutionResult(
            events=events,
            output=result.output,
            is_error=False,
            analysis_handoff=None,
            step_summary=self._build_step_summary(result.output),
        )

    def error_outcome(self, result: SandboxResult) -> ExecutionResult:
        """Build the outcome for one failed sandbox execution."""

        events = [*self.pending_events, Event("error", {"text": result.output})]
        return ExecutionResult(
            events=events,
            output=result.output,
            is_error=True,
            analysis_handoff=None,
            step_summary=None,
        )

    def analysis_handoff_outcome(self, value: Any) -> ExecutionResult:
        """Build the outcome for one terminal analysis handoff."""

        if not isinstance(value, AnalysisHandoff):
            raise ValueError("Analysis handoff must contain notes and artifact ids.")

        return ExecutionResult(
            events=[*self.pending_events],
            output=None,
            is_error=False,
            analysis_handoff=value,
            step_summary=self._build_step_summary(None),
        )

    def _coerce_artifact_ids(self, artifact_ids: Any | None) -> list[str]:
        """Coerce one raw artifact id payload into a validated string list."""

        if artifact_ids is None:
            return []
        if not isinstance(artifact_ids, list):
            raise ValueError("Analysis handoff artifact_ids must be a list of strings.")

        normalized_artifact_ids: list[str] = []
        for raw_artifact_id in artifact_ids:
            normalized_artifact_ids.append(
                require_text(raw_artifact_id, "Analysis handoff artifact id")
            )
        return normalized_artifact_ids

    def _validate_artifact_ids_exist(self, artifact_ids: list[str]) -> None:
        """Reject handoff artifact ids that do not exist in the environment."""

        available_artifact_ids = {artifact.id for artifact in self.environment.artifacts}
        for artifact_id in artifact_ids:
            if artifact_id not in available_artifact_ids:
                raise ValueError(f"Unknown artifact reference '{artifact_id}'.")

    def _validate_artifact_mentions(
        self,
        notes: str,
        artifact_ids: list[str],
    ) -> None:
        """Reject inline artifact mentions that are missing from artifact_ids."""

        mentioned_artifact_ids = _ARTIFACT_MENTION_PATTERN.findall(notes)
        for artifact_id in mentioned_artifact_ids:
            if artifact_id not in artifact_ids:
                raise ValueError(
                    f"Artifact '{artifact_id}' mentioned in notes must also appear in artifact_ids."
                )

    def _bind_actions(self) -> dict[str, Callable[..., Any]]:
        """Bind registered actions to this execution context."""

        bound_actions: dict[str, Callable[..., Any]] = {}
        for name, action in self.environment._actions.items():
            bound_actions[name] = self._bind_action(action)
        return bound_actions

    def _bind_action(self, action: Callable[..., Any]) -> Callable[..., Any]:
        """Bind one action so generated code does not see the context argument."""

        def bound_action(*args: Any, **kwargs: Any) -> Any:
            return action(self, *args, **kwargs)

        return bound_action

    def _build_step_summary(self, text_output: str | None) -> str | None:
        """Build one compact summary string for the next agent step."""

        lines: list[str] = []
        lines.extend(self._summarize_dataframe_changes())
        lines.extend(self._summarize_published_artifacts())
        if text_output not in {None, "OK"}:
            lines.append(f"- text output: {text_output}")

        if len(lines) == 0:
            return None

        return "Step summary:\n" + "\n".join(lines)

    def _summarize_dataframe_changes(self) -> list[str]:
        """Summarize dataframe variables whose visible metadata changed this step."""

        lines: list[str] = []
        current_dataframe_metadata = self._snapshot_dataframe_metadata(
            self.environment.workspace
        )
        for name, metadata in current_dataframe_metadata.items():
            if self.before_dataframe_metadata.get(name) == metadata:
                continue

            row_count, columns, dtypes = metadata
            lines.append(
                f"- dataframe {name}: {row_count} rows; "
                f"columns={list(columns)}; "
                f"dtypes={{"
                + ", ".join(f"{column!r}: {dtype!r}" for column, dtype in dtypes)
                + "}"
            )

        return lines

    def _snapshot_dataframe_metadata(
        self,
        workspace: dict[str, Any],
    ) -> dict[str, tuple[int, tuple[Any, ...], tuple[tuple[Any, str], ...]]]:
        """Capture one compact metadata snapshot for dataframe workspace variables."""

        metadata_by_name: dict[
            str,
            tuple[int, tuple[Any, ...], tuple[tuple[Any, str], ...]],
        ] = {}
        for name, value in workspace.items():
            if not isinstance(value, pd.DataFrame):
                continue

            columns = tuple(value.columns.tolist())
            dtypes = tuple((column, str(value[column].dtype)) for column in columns)
            metadata_by_name[name] = (len(value), columns, dtypes)
        return metadata_by_name

    def _summarize_published_artifacts(self) -> list[str]:
        """Summarize published artifacts from this execution."""

        lines: list[str] = []
        for event in self.pending_events:
            if event.kind != "artifact":
                continue

            lines.append(
                f"- published artifact {event.data['id']}: "
                f"{event.data['kind']} '{event.data['title']}'"
            )

        return lines


@dataclass
class Environment:
    """Owns runtime state, actions, and sandbox execution."""

    inputs: dict[str, pd.DataFrame]
    sandbox: ExecutionSandbox
    workspace: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    _actions: dict[str, Callable[..., Any]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.inputs = self._copy_inputs(self.inputs)

    def register_action(self, name: str, action: Callable[..., Any]) -> None:
        """Register one action that will receive an ExecutionContext first."""

        self._validate_action_name(name)
        self._actions[name] = action

    def add_input_table(self, name: str, table: pd.DataFrame) -> None:
        """Add one immutable input table to the environment."""

        normalized_name = require_text(name, "Input table name")
        if normalized_name in self.inputs:
            raise ValueError(f"Input table name '{normalized_name}' already exists.")
        if normalized_name in self._actions or normalized_name in _RESERVED_RUNTIME_NAMES:
            raise ValueError(
                f"Input table name '{normalized_name}' conflicts with an existing runtime name."
            )

        self.inputs[normalized_name] = table.copy(deep=True)

    def execute(self, code: str) -> ExecutionResult:
        """Execute code against immutable inputs plus persistent workspace state."""

        execution_context = ExecutionContext(self)
        namespace = execution_context.build_namespace()

        try:
            result = self.sandbox.execute(code, namespace)
        except SandboxStop as stop:
            self._persist_workspace(namespace)
            return execution_context.analysis_handoff_outcome(stop.value)

        self._persist_workspace(namespace)

        if result.is_error:
            return execution_context.error_outcome(result)
        return execution_context.success_outcome(result)

    def _store_artifact(
        self,
        kind: ArtifactKind,
        title: str,
        data: dict[str, Any],
    ) -> Artifact:
        """Store one artifact in durable environment state."""

        artifact = Artifact(
            id=f"artifact_{uuid.uuid4().hex[:8]}",
            kind=kind,
            title=title,
            data=data,
        )
        self.artifacts.append(artifact)
        return artifact

    def describe(self) -> str:
        """Describe immutable input tables for prompt construction."""

        if not self.inputs:
            return "No input tables loaded."

        parts = []
        for name, table in self.inputs.items():
            columns = [f"  - {column} ({table[column].dtype})" for column in table.columns]
            parts.append(
                f"{name}: {len(table)} rows, {len(table.columns)} columns\n"
                + "\n".join(columns)
            )

        return "\n\n".join(parts)

    def _persist_workspace(self, namespace: dict[str, Any]) -> None:
        """Persist only caller-created runtime variables across executions."""

        reserved_names = set(self.inputs) | set(self._actions) | _RESERVED_RUNTIME_NAMES
        self.workspace = {
            name: value
            for name, value in namespace.items()
            if name not in reserved_names and not name.startswith("__")
        }

    def _copy_inputs(self, inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """Copy input tables so the environment owns its own immutable snapshot."""

        copied_inputs: dict[str, pd.DataFrame] = {}
        for name, table in inputs.items():
            self._validate_input_name(name)
            copied_inputs[name] = table.copy(deep=True)
        return copied_inputs

    def _validate_input_name(self, name: str) -> None:
        """Reject blank or reserved input table names."""

        normalized_name = require_text(name, "Input table name")
        if normalized_name in _RESERVED_RUNTIME_NAMES:
            raise ValueError(
                f"Input table name '{normalized_name}' conflicts with a reserved runtime name."
            )

    def _validate_action_name(self, name: str) -> None:
        """Reject action names that collide with reserved runtime names."""

        normalized_name = require_text(name, "Action name")
        conflicts = normalized_name in self.inputs
        conflicts = conflicts or normalized_name in self._actions
        conflicts = conflicts or normalized_name in _RESERVED_RUNTIME_NAMES

        if conflicts:
            raise ValueError(
                f"Action name '{normalized_name}' conflicts with an existing runtime name."
            )
