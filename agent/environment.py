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
ObservationKind = Literal["dataframe", "artifact", "text_output"]

_RESERVED_RUNTIME_NAMES = {"pd", "np", "conclude_analysis"}
_ARTIFACT_MENTION_PATTERN = re.compile(r"(?<!\w)@(artifact_[A-Za-z0-9_]+)\b")


@dataclass(frozen=True)
class Artifact:
    """One user-visible artifact produced during execution."""

    id: str
    kind: ArtifactKind
    title: str
    data: dict[str, Any]


@dataclass(frozen=True)
class DataFrameObservation:
    """One compact observation about a dataframe created in the workspace."""

    name: str
    rows: int
    columns: list[str]
    dtypes: dict[str, str]


@dataclass(frozen=True)
class ArtifactObservation:
    """One compact observation about a published artifact."""

    artifact_id: str
    artifact_kind: ArtifactKind
    title: str


@dataclass(frozen=True)
class TextOutputObservation:
    """One compact observation about printed or repr-style step output."""

    text: str


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
    observations: list[DataFrameObservation | ArtifactObservation | TextOutputObservation]


@dataclass
class ExecutionContext:
    """Step-local execution state built fresh for each environment execution."""

    environment: "Environment"
    pending_events: list[Event] = field(default_factory=list)
    before_workspace: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        """Snapshot the workspace so the step can report what changed."""

        self.before_workspace = dict(self.environment.workspace)

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
            observations=self._collect_observations(result.output),
        )

    def error_outcome(self, result: SandboxResult) -> ExecutionResult:
        """Build the outcome for one failed sandbox execution."""

        events = [*self.pending_events, Event("error", {"text": result.output})]
        return ExecutionResult(
            events=events,
            output=result.output,
            is_error=True,
            analysis_handoff=None,
            observations=[],
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
            observations=self._collect_observations(None),
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

    def _collect_observations(
        self,
        text_output: str | None,
    ) -> list[DataFrameObservation | ArtifactObservation | TextOutputObservation]:
        """Collect one compact summary of what this step produced."""

        observations: list[
            DataFrameObservation | ArtifactObservation | TextOutputObservation
        ] = []

        observations.extend(self._collect_dataframe_observations())
        observations.extend(self._collect_artifact_observations())
        if text_output not in {None, "OK"}:
            observations.append(TextOutputObservation(text=text_output))
        return observations

    def _collect_dataframe_observations(self) -> list[DataFrameObservation]:
        """Summarize newly created or reassigned dataframe workspace variables."""

        observations: list[DataFrameObservation] = []
        for name, value in self.environment.workspace.items():
            if not isinstance(value, pd.DataFrame):
                continue

            previous_value = self.before_workspace.get(name)
            if previous_value is value:
                continue

            observations.append(
                DataFrameObservation(
                    name=name,
                    rows=len(value),
                    columns=list(value.columns),
                    dtypes={column: str(value[column].dtype) for column in value.columns},
                )
            )

        return observations

    def _collect_artifact_observations(self) -> list[ArtifactObservation]:
        """Summarize published artifacts from this execution."""

        observations: list[ArtifactObservation] = []
        for event in self.pending_events:
            if event.kind != "artifact":
                continue

            observations.append(
                ArtifactObservation(
                    artifact_id=str(event.data["id"]),
                    artifact_kind=event.data["kind"],
                    title=str(event.data["title"]),
                )
            )

        return observations


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
