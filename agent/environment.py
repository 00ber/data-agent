"""Runtime environment for agent code execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal
import uuid

import numpy as np
import pandas as pd

from agent.events import Event
from agent.sandbox import ExecutionSandbox, SandboxResult, SandboxStop
from agent.validation import require_text

ArtifactKind = Literal["table", "chart", "stat"]

_RESERVED_RUNTIME_NAMES = {"pd", "np", "final_answer"}


@dataclass(frozen=True)
class Artifact:
    """One user-visible artifact produced during execution."""

    id: str
    kind: ArtifactKind
    title: str
    data: dict[str, Any]


@dataclass
class ExecutionResult:
    """Structured result returned from one environment execution."""

    events: list[Event]
    output: str | None
    is_error: bool
    final_answer: str | None


@dataclass
class ExecutionContext:
    """Step-local execution state built fresh for each environment execution."""

    environment: "Environment"
    pending_events: list[Event] = field(default_factory=list)

    def build_namespace(self) -> dict[str, Any]:
        """Build the step namespace from environment state and bound actions."""

        namespace = {
            name: table.copy(deep=True)
            for name, table in self.environment.inputs.items()
        }
        namespace.update(self.environment.workspace)
        namespace.update(self._bind_actions())
        namespace["final_answer"] = self.final_answer
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

    def final_answer(self, answer: str) -> None:
        """Stop this execution with a validated final answer."""

        normalized_answer = require_text(answer, "Final answer")
        raise SandboxStop(normalized_answer)

    def success_outcome(self, result: SandboxResult) -> ExecutionResult:
        """Build the outcome for one successful sandbox execution."""

        events = [*self.pending_events, Event("result", {"text": result.output})]
        return ExecutionResult(
            events=events,
            output=result.output,
            is_error=False,
            final_answer=None,
        )

    def error_outcome(self, result: SandboxResult) -> ExecutionResult:
        """Build the outcome for one failed sandbox execution."""

        events = [*self.pending_events, Event("error", {"text": result.output})]
        return ExecutionResult(
            events=events,
            output=result.output,
            is_error=True,
            final_answer=None,
        )

    def final_answer_outcome(self, value: Any) -> ExecutionResult:
        """Build the outcome for one terminal final answer."""

        final_answer = require_text(value, "Final answer")
        return ExecutionResult(
            events=[*self.pending_events],
            output=None,
            is_error=False,
            final_answer=final_answer,
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
            return execution_context.final_answer_outcome(stop.value)

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
