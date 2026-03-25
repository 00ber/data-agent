"""Small validation helpers shared across core agent modules."""

from __future__ import annotations

from typing import Any


def require_text(value: Any, field_name: str) -> str:
    """Require a non-empty string value for one named field."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")

    return value.strip()


def require_optional_text(value: Any, field_name: str) -> str | None:
    """Allow absent text, but reject blank strings when provided."""

    if value is None:
        return None

    return require_text(value, field_name)


def require_positive_int(value: Any, field_name: str) -> int:
    """Require a positive integer value for one named field."""

    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return value
