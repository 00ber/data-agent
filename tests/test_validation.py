import pytest

from agent.validation import (
    require_optional_text,
    require_positive_int,
    require_text,
)


class TestRequireText:
    def test_returns_stripped_text(self):
        assert require_text("  hello  ", "Greeting") == "hello"

    def test_rejects_blank_text(self):
        with pytest.raises(ValueError, match="Greeting must be a non-empty string."):
            require_text("   ", "Greeting")


class TestRequireOptionalText:
    def test_allows_none(self):
        assert require_optional_text(None, "Optional field") is None

    def test_returns_stripped_text_when_present(self):
        assert require_optional_text("  value  ", "Optional field") == "value"

    def test_rejects_blank_text(self):
        with pytest.raises(
            ValueError,
            match="Optional field must be a non-empty string.",
        ):
            require_optional_text(" ", "Optional field")


class TestRequirePositiveInt:
    def test_accepts_positive_integer(self):
        assert require_positive_int(3, "Count") == 3

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="Count must be a positive integer."):
            require_positive_int(0, "Count")

    def test_rejects_boolean(self):
        with pytest.raises(ValueError, match="Count must be a positive integer."):
            require_positive_int(True, "Count")
