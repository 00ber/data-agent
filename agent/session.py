"""Session state: tables, artifacts, history, config."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd


@dataclass
class AgentConfig:
    """Configuration for the agent's LLM calls."""

    model: str = "gpt-4o"
    max_steps: int = 10
    temperature: float = 0.0


@dataclass
class Artifact:
    """A displayable output: table, chart, or stat card."""

    id: str
    kind: Literal["table", "chart", "stat"]
    title: str
    data: dict[str, Any]


@dataclass
class Session:
    """All state for one analysis session."""

    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    config: AgentConfig = field(default_factory=AgentConfig)
