"""Structured final responses for narrative sections and artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from agent.validation import require_optional_text, require_text


class ResponseSection(BaseModel):
    """One ordered section in a final user-facing response."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["markdown", "artifact"]
    markdown: str | None
    artifact_id: str | None

    @model_validator(mode="after")
    def validate_shape(self) -> "ResponseSection":
        """Require fields that match the chosen section kind."""

        if self.kind == "markdown":
            require_text(self.markdown, "Final response markdown section")
            if self.artifact_id is not None:
                raise ValueError(
                    "Markdown response sections must not include artifact_id."
                )
            return self

        if self.markdown is not None:
            raise ValueError("Artifact response sections must not include markdown.")

        require_text(self.artifact_id, "Final response artifact section artifact_id")
        return self


class FinalResponse(BaseModel):
    """One final user-facing response composed of ordered sections."""

    model_config = ConfigDict(extra="forbid")

    sections: list[ResponseSection]

    @model_validator(mode="after")
    def validate_sections(self) -> "FinalResponse":
        """Require at least one response section."""

        if len(self.sections) == 0:
            raise ValueError("Final response must contain at least one section.")
        return self


class FinalResponseReview(BaseModel):
    """Structured review result for the downstream analysis handoff."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "needs_more_analysis"]
    critique: str | None
    response: FinalResponse | None

    @model_validator(mode="after")
    def validate_outcome(self) -> "FinalResponseReview":
        """Require critique or response that match the review status."""

        if self.status == "approved":
            if self.critique is not None:
                raise ValueError(
                    "Approved final response reviews must not include critique."
                )
            if self.response is None:
                raise ValueError(
                    "Approved final response reviews must include a response."
                )
            return self

        require_optional_text(self.critique, "Final response review critique")
        if self.critique is None:
            raise ValueError(
                "Final response reviews that need more analysis must include critique."
            )
        if self.response is not None:
            raise ValueError(
                "Final response reviews that need more analysis must not include a response."
            )
        return self


def validate_final_response_artifacts(
    response: FinalResponse,
    *,
    available_artifact_ids: set[str],
) -> None:
    """Reject artifact references that do not exist in the environment."""

    for section in response.sections:
        if section.kind != "artifact":
            continue

        artifact_id = require_text(
            section.artifact_id,
            "Final response artifact section artifact_id",
        )
        if artifact_id not in available_artifact_ids:
            raise ValueError(f"Unknown artifact reference '{artifact_id}'.")


def serialize_final_response(response: FinalResponse) -> list[dict[str, str]]:
    """Serialize one final response for streamed events and JSON payloads."""

    payload: list[dict[str, str]] = []
    for section in response.sections:
        if section.kind == "markdown":
            payload.append(
                {
                    "type": "markdown",
                    "content": require_text(
                        section.markdown,
                        "Final response markdown section",
                    ),
                }
            )
            continue

        payload.append(
            {
                "type": "artifact",
                "artifact_id": require_text(
                    section.artifact_id,
                    "Final response artifact section artifact_id",
                ),
            }
        )

    return payload


def response_to_conversation_text(
    response: FinalResponse,
    *,
    artifact_titles: dict[str, str] | None = None,
) -> str:
    """Render one final response into assistant text for conversation memory."""

    parts: list[str] = []
    titles = artifact_titles or {}

    for section in response.sections:
        if section.kind == "markdown":
            parts.append(
                require_text(section.markdown, "Final response markdown section")
            )
            continue

        artifact_id = require_text(
            section.artifact_id,
            "Final response artifact section artifact_id",
        )
        title = titles.get(artifact_id, artifact_id)
        parts.append(f"[Artifact: {title}]")

    return "\n\n".join(parts)
