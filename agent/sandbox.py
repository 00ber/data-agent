"""Restricted Python execution for agent-generated code."""

from __future__ import annotations

import ast
import contextlib
import io
from dataclasses import dataclass
from typing import Any

from RestrictedPython import compile_restricted_exec, safe_builtins
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import guarded_unpack_sequence, safer_getattr

_RESULT_VAR = "sandbox_last_expr"


@dataclass
class SandboxResult:
    """Result of one sandbox execution."""

    output: str
    is_error: bool


class SandboxStop(Exception):
    """Internal execution stop signal for sandboxed code."""

    def __init__(self, value: Any) -> None:
        self.value = value
        super().__init__(value)


class _PrintHandler:
    """Bridge RestrictedPython print calls to redirected stdout."""

    def __init__(self, _getattr_=None) -> None:
        self._getattr = _getattr_

    def _call_print(self, *args: Any, **kwargs: Any) -> None:
        print(*args, **kwargs)


_EXTRA_BUILTINS = {
    "sum": sum,
    "min": min,
    "max": max,
    "all": all,
    "any": any,
    "enumerate": enumerate,
    "map": map,
    "filter": filter,
    "reversed": reversed,
    "list": list,
    "dict": dict,
    "set": set,
    "frozenset": frozenset,
    "type": type,
}


class ExecutionSandbox:
    """Low-level restricted Python execution service."""

    def execute(self, code: str, env: dict[str, Any]) -> SandboxResult:
        """Execute code in a restricted environment using the provided namespace."""

        instrumented_code = self._capture_last_expression(code)
        compiled = compile_restricted_exec(instrumented_code)

        if compiled.errors:
            return SandboxResult(
                output=f"Compilation error: {'; '.join(compiled.errors)}",
                is_error=True,
            )

        env["__builtins__"] = self._make_builtins()
        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                exec(compiled.code, env)
        except SandboxStop:
            raise
        except Exception as exc:
            return SandboxResult(
                output=f"{type(exc).__name__}: {exc}",
                is_error=True,
            )
        finally:
            env.pop("__builtins__", None)

        printed_output = stdout.getvalue().rstrip()
        last_value = env.pop(_RESULT_VAR, None)

        parts: list[str] = []
        if printed_output:
            parts.append(printed_output)
        if last_value is not None:
            parts.append(repr(last_value))

        return SandboxResult(
            output="\n".join(parts) if parts else "OK",
            is_error=False,
        )

    def _make_builtins(self) -> dict[str, Any]:
        """Build the safe builtins dictionary used by RestrictedPython."""

        builtins = dict(safe_builtins)
        builtins.update(_EXTRA_BUILTINS)
        builtins["_getiter_"] = default_guarded_getiter
        builtins["_unpack_sequence_"] = guarded_unpack_sequence
        builtins["_getattr_"] = safer_getattr
        builtins["_write_"] = lambda value: value
        builtins["_getitem_"] = lambda obj, key: obj[key]
        builtins["_print_"] = _PrintHandler
        return builtins

    def _capture_last_expression(self, source: str) -> str:
        """Assign the final bare expression to a hidden variable."""

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        if not tree.body or not isinstance(tree.body[-1], ast.Expr):
            return source

        last_expression = tree.body[-1]
        tree.body[-1] = ast.Assign(
            targets=[ast.Name(id=_RESULT_VAR, ctx=ast.Store())],
            value=last_expression.value,
            lineno=last_expression.lineno,
            col_offset=last_expression.col_offset,
        )
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
