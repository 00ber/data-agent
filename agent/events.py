"""Event types for the agent event stream."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EventKind = Literal["thinking", "code", "artifact", "result", "answer", "error"]


@dataclass
class Event:
    """A single event in the agent's output stream."""

    kind: EventKind
    data: dict[str, Any]


class FinalAnswer(Exception):
    """Raised by final_answer() tool to terminate the agent loop."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        super().__init__(answer)
