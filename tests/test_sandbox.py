import pandas as pd
import pytest

from agent.sandbox import ExecutionSandbox, SandboxResult, SandboxStop


@pytest.fixture
def sandbox():
    return ExecutionSandbox()


class TestSandboxResult:
    def test_stores_output_and_error_flag(self):
        result = SandboxResult(output="OK", is_error=False)

        assert result.output == "OK"
        assert result.is_error is False


class TestSandboxStop:
    def test_stores_stop_value(self):
        stop = SandboxStop("done")

        assert stop.value == "done"

    def test_is_exception(self):
        stop = SandboxStop("done")

        assert isinstance(stop, Exception)


class TestExecuteBasics:
    def test_simple_expression(self, sandbox):
        result = sandbox.execute("x = 1 + 2", {})

        assert not result.is_error
        assert result.output == "OK"

    def test_captures_print_output(self, sandbox):
        result = sandbox.execute("print('hello world')", {})

        assert not result.is_error
        assert result.output == "hello world"

    def test_captures_last_expression(self, sandbox):
        result = sandbox.execute("1 + 2", {})

        assert not result.is_error
        assert result.output == "3"

    def test_combines_print_and_last_expression_output(self, sandbox):
        result = sandbox.execute("print('hello')\n1 + 2", {})

        assert not result.is_error
        assert result.output == "hello\n3"

    def test_env_variables_are_accessible(self, sandbox):
        result = sandbox.execute("print(x)", {"x": 42})

        assert not result.is_error
        assert result.output == "42"

    def test_dataframe_in_env_is_accessible(self, sandbox):
        sales = pd.DataFrame({"a": [1, 2, 3]})

        result = sandbox.execute("print(len(sales))", {"sales": sales})

        assert not result.is_error
        assert result.output == "3"

    def test_tool_callable_in_env_can_be_called(self, sandbox):
        calls = []

        def fake_tool(value):
            calls.append(value)
            return f"called with {value}"

        result = sandbox.execute("fake_tool('hello')", {"fake_tool": fake_tool})

        assert not result.is_error
        assert result.output == "'called with hello'"
        assert calls == ["hello"]

    def test_pandas_operations_work(self, sandbox):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        result = sandbox.execute("print(df['a'].sum())", {"df": df, "pd": pd})

        assert not result.is_error
        assert result.output == "6"

    def test_multi_line_code(self, sandbox):
        code = """
x = [1, 2, 3]
total = sum(x)
print(f"total is {total}")
"""
        result = sandbox.execute(code, {})

        assert not result.is_error
        assert result.output == "total is 6"


class TestExecuteSafety:
    def test_import_is_blocked(self, sandbox):
        result = sandbox.execute("import os", {})

        assert result.is_error

    def test_open_is_blocked(self, sandbox):
        result = sandbox.execute("open('/etc/passwd')", {})

        assert result.is_error

    def test_dunder_access_is_blocked(self, sandbox):
        result = sandbox.execute("[].__class__.__bases__", {})

        assert result.is_error

    def test_exec_is_blocked(self, sandbox):
        result = sandbox.execute("exec('print(1)')", {})

        assert result.is_error

    def test_eval_is_blocked(self, sandbox):
        result = sandbox.execute("eval('1+1')", {})

        assert result.is_error


class TestStopPropagation:
    def test_stop_signal_propagates(self, sandbox):
        def finish(text):
            raise SandboxStop(text)

        with pytest.raises(SandboxStop) as exc_info:
            sandbox.execute("finish('Revenue is $8.2M')", {"finish": finish})

        assert exc_info.value.value == "Revenue is $8.2M"

    def test_stop_signal_is_not_caught_as_error(self, sandbox):
        def finish(text):
            raise SandboxStop(text)

        with pytest.raises(SandboxStop):
            sandbox.execute("finish('done')", {"finish": finish})


class TestExecuteErrors:
    def test_syntax_error_is_flagged(self, sandbox):
        result = sandbox.execute("def foo(", {})

        assert result.is_error
        assert "Compilation error:" in result.output

    def test_runtime_error_returns_message(self, sandbox):
        result = sandbox.execute("1 / 0", {})

        assert result.is_error
        assert "ZeroDivisionError" in result.output

    def test_name_error_returns_message(self, sandbox):
        result = sandbox.execute("print(undefined_var)", {})

        assert result.is_error
        assert "NameError" in result.output

    def test_error_does_not_crash_sandbox(self, sandbox):
        result = sandbox.execute("raise ValueError('bad input')", {})

        assert result.is_error
        assert "ValueError" in result.output
        assert "bad input" in result.output


class TestVariablePersistence:
    def test_variables_persist_across_calls(self, sandbox):
        env = {}

        sandbox.execute("x = 42", env)
        result = sandbox.execute("print(x)", env)

        assert not result.is_error
        assert result.output == "42"

    def test_dataframe_persists_across_calls(self, sandbox):
        env = {"pd": pd}

        sandbox.execute("df = pd.DataFrame({'a': [1, 2, 3]})", env)
        result = sandbox.execute("print(len(df))", env)

        assert not result.is_error
        assert result.output == "3"

    def test_tool_results_persist(self, sandbox):
        def fake_group():
            return "grouped_data"

        env = {"fake_group": fake_group}

        sandbox.execute("result = fake_group()", env)
        result = sandbox.execute("print(result)", env)

        assert not result.is_error
        assert result.output == "grouped_data"

    def test_original_env_variables_are_not_clobbered(self, sandbox):
        env = {"x": 10}

        sandbox.execute("y = x + 5", env)
        result = sandbox.execute("print(x, y)", env)

        assert not result.is_error
        assert result.output == "10 15"

    def test_internal_last_expression_variable_does_not_leak(self, sandbox):
        env = {}

        sandbox.execute("1 + 2", env)

        assert "sandbox_last_expr" not in env

    def test_internal_builtins_do_not_leak(self, sandbox):
        env = {}

        sandbox.execute("x = 1", env)

        assert "__builtins__" not in env
