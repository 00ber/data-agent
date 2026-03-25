"""Conversation memory for the agent core."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.validation import require_optional_text, require_text


@dataclass(frozen=True)
class StepRecord:
    """One recorded execution step from the agent loop."""

    plan: str
    code: str
    output: str | None
    is_error: bool


@dataclass
class Memory:
    """Explicit conversation and step memory for one agent runtime."""

    step_history: list[StepRecord] = field(default_factory=list)
    final_answers: list[str] = field(default_factory=list)
    _conversation_history: list[dict[str, str]] = field(default_factory=list)

    def record_user_turn(self, message: str) -> None:
        """Record one user turn in the conversation history."""

        normalized_message = require_text(message, "User message")
        self._conversation_history.append(
            {"role": "user", "content": normalized_message}
        )

    def record_step(
        self,
        *,
        plan: str,
        code: str,
        output: str | None = None,
        is_error: bool = False,
    ) -> StepRecord:
        """Record one execution step without mutating conversation turns."""

        normalized_plan = require_text(plan, "Step plan")
        normalized_code = require_text(code, "Step code")
        normalized_output = require_optional_text(output, "Step output")

        step_record = StepRecord(
            plan=normalized_plan,
            code=normalized_code,
            output=normalized_output,
            is_error=is_error,
        )
        self.step_history.append(step_record)
        return step_record

    def record_final_answer(self, answer: str) -> None:
        """Record one final answer as both a fact and an assistant turn."""

        normalized_answer = require_text(answer, "Final answer")
        self.final_answers.append(normalized_answer)
        self._conversation_history.append(
            {"role": "assistant", "content": normalized_answer}
        )

    def conversation_messages(self) -> list[dict[str, str]]:
        """Return a copy of the stored conversation turns."""

        return [message.copy() for message in self._conversation_history]
