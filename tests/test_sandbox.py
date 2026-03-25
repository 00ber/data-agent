import pandas as pd
import pytest

from agent.events import FinalAnswer
from agent.sandbox import execute


class TestExecuteBasics:
    def test_simple_expression(self):
        result = execute("x = 1 + 2", {})

        assert not result.is_error
        assert "OK" in result.output

    def test_captures_print_output(self):
        result = execute("print('hello world')", {})

        assert not result.is_error
        assert "hello world" in result.output

    def test_last_expression_captured(self):
        result = execute("1 + 2", {})

        assert not result.is_error
        assert "3" in result.output

    def test_env_variables_accessible(self):
        result = execute("print(x)", {"x": 42})

        assert not result.is_error
        assert "42" in result.output

    def test_dataframe_in_env(self):
        df = pd.DataFrame({"a": [1, 2, 3]})

        result = execute("print(len(sales))", {"sales": df})

        assert not result.is_error
        assert "3" in result.output

    def test_tool_callable_in_env(self):
        calls = []

        def fake_tool(x):
            calls.append(x)
            return f"called with {x}"

        execute("fake_tool('hello')", {"fake_tool": fake_tool})

        assert calls == ["hello"]

    def test_pandas_operations(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        result = execute("print(df['a'].sum())", {"df": df, "pd": pd})

        assert not result.is_error
        assert "6" in result.output

    def test_multi_line_code(self):
        code = """
x = [1, 2, 3]
total = sum(x)
print(f"total is {total}")
"""
        result = execute(code, {})

        assert not result.is_error
        assert "total is 6" in result.output


class TestExecuteSafety:
    def test_import_blocked(self):
        result = execute("import os", {})

        assert result.is_error

    def test_open_blocked(self):
        result = execute("open('/etc/passwd')", {})

        assert result.is_error

    def test_dunder_access_blocked(self):
        result = execute("[].__class__.__bases__", {})

        assert result.is_error

    def test_exec_blocked(self):
        result = execute("exec('print(1)')", {})

        assert result.is_error

    def test_eval_blocked(self):
        result = execute("eval('1+1')", {})

        assert result.is_error


class TestFinalAnswerPropagation:
    def test_final_answer_propagates(self):
        def final_answer(text):
            raise FinalAnswer(text)

        with pytest.raises(FinalAnswer) as exc_info:
            execute(
                "final_answer('Revenue is $8.2M')",
                {"final_answer": final_answer},
            )

        assert exc_info.value.answer == "Revenue is $8.2M"

    def test_final_answer_not_caught_by_sandbox(self):
        def final_answer(text):
            raise FinalAnswer(text)

        with pytest.raises(FinalAnswer):
            execute("final_answer('done')", {"final_answer": final_answer})


class TestExecuteErrors:
    def test_syntax_error_is_flagged(self):
        result = execute("def foo(", {})

        assert result.is_error

    def test_runtime_error_returns_message(self):
        result = execute("1 / 0", {})

        assert result.is_error
        assert "ZeroDivisionError" in result.output

    def test_name_error_returns_message(self):
        result = execute("print(undefined_var)", {})

        assert result.is_error
        assert "NameError" in result.output

    def test_error_does_not_crash_sandbox(self):
        result = execute("raise ValueError('bad input')", {})

        assert result.is_error
        assert "ValueError" in result.output
        assert "bad input" in result.output
