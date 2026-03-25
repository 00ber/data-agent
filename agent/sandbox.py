"""Restricted sandbox for executing LLM-generated Python code."""
from __future__ import annotations

import ast
import contextlib
import io
from dataclasses import dataclass

from RestrictedPython import compile_restricted_exec, safe_builtins
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import guarded_unpack_sequence, safer_getattr

from agent.events import FinalAnswer

_RESULT_VAR = "sandbox_last_expr"


@dataclass
class SandboxResult:
    """Result of sandbox execution."""

    output: str
    is_error: bool


class _PrintHandler:
    """Print handler for RestrictedPython.

    RestrictedPython transforms ``print(x)`` into
    ``_print_(_getattr_)._call_print(x)``. This handler delegates
    directly to the real ``print`` so output goes to stdout (which
    the sandbox captures via ``redirect_stdout``).
    """

    def __init__(self, _getattr_=None):
        pass

    def _call_print(self, *args, **kwargs):
        print(*args, **kwargs)


# Builtins that safe_builtins omits but are safe for data analysis.
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


def _make_builtins() -> dict:
    """Build the safe builtins dict with required guards."""
    builtins = dict(safe_builtins)
    builtins.update(_EXTRA_BUILTINS)
    builtins["_getiter_"] = default_guarded_getiter
    builtins["_unpack_sequence_"] = guarded_unpack_sequence
    builtins["_getattr_"] = safer_getattr
    builtins["_write_"] = lambda x: x
    builtins["_getitem_"] = lambda obj, key: obj[key]
    builtins["_print_"] = _PrintHandler
    return builtins


def _capture_last_expression(source: str) -> str:
    """If the last statement is a bare expression, assign it to a variable.

    This lets us capture and return the value of the last expression,
    similar to a REPL.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source  # Let RestrictedPython report the error

    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = tree.body[-1]
        tree.body[-1] = ast.Assign(
            targets=[ast.Name(id=_RESULT_VAR, ctx=ast.Store())],
            value=last.value,
            lineno=last.lineno,
            col_offset=last.col_offset,
        )
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    return source


def execute(code: str, env: dict) -> SandboxResult:
    """Execute code in a restricted sandbox.

    Returns a SandboxResult with:
    - output: captured stdout + last expression repr, or error message
    - is_error: True if execution failed

    Raises FinalAnswer if the code calls final_answer() — this is the
    only exception that propagates out.
    """
    code = _capture_last_expression(code)

    compiled = compile_restricted_exec(code)
    if compiled.errors:
        return SandboxResult(
            output=f"Compilation error: {'; '.join(compiled.errors)}",
            is_error=True,
        )

    namespace = {**env, "__builtins__": _make_builtins()}
    stdout = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout):
            exec(compiled.code, namespace)
    except FinalAnswer:
        raise
    except Exception as exc:
        return SandboxResult(
            output=f"{type(exc).__name__}: {exc}",
            is_error=True,
        )

    output = stdout.getvalue()
    last_value = namespace.get(_RESULT_VAR)

    parts = []
    if output:
        parts.append(output.rstrip())
    if last_value is not None:
        parts.append(repr(last_value))

    return SandboxResult(
        output="\n".join(parts) if parts else "OK",
        is_error=False,
    )
