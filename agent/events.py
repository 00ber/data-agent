"""Event types emitted by the agent loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EventKind = Literal["thinking", "code", "artifact", "result", "answer", "error"]


@dataclass
class Event:
    """A single streamed event emitted during agent execution."""

    kind: EventKind
    data: dict[str, Any]
