"""Prompt construction from session state and tool introspection."""
from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from agent.tools import Tools

SYSTEM_INSTRUCTIONS = """\
You are an analytics agent. You answer questions about data by writing Python code.

You have access to:
- DataFrames loaded as variables (listed below)
- Tool functions for common operations (listed below)
- pandas (as `pd`) and numpy (as `np`) for advanced operations

Write code that:
1. Uses tool functions for standard operations (filter, group_by, sort, join)
2. Uses show_chart(), show_table(), show_stat() to display results
3. Calls final_answer() with your conclusion when done

Every tool call produces a visible artifact. Use tools for clarity.
For derived metrics (ratios, z-scores, custom calculations), write pandas directly.
"""


def describe_tool(method: object) -> str:
    """Describe a tool method using its signature and docstring."""
    sig = inspect.signature(method)
    params = [
        f"{name}: {getattr(p.annotation, '__name__', str(p.annotation))}"
        if p.annotation != inspect.Parameter.empty
        else name
        for name, p in sig.parameters.items()
        if name != "self"
    ]
    param_str = ", ".join(params)
    name = getattr(method, "__name__", str(method))
    doc = inspect.getdoc(method) or ""
    return f"{name}({param_str})\n    {doc}"


def describe_tables(tables: dict[str, pd.DataFrame]) -> str:
    """Describe all loaded tables with schema info."""
    if not tables:
        return "No tables loaded."

    parts = []
    for name, df in tables.items():
        cols = [f"  - {col} ({df[col].dtype})" for col in df.columns]
        col_text = "\n".join(cols)
        parts.append(f"{name}: {len(df)} rows, {len(df.columns)} columns\n{col_text}")

    return "\n\n".join(parts)


def build_prompt(tables: dict[str, pd.DataFrame], tools: Tools) -> str:
    """Build the full system prompt from tables and tools."""
    # Collect public methods (tools) from the Tools instance
    tool_methods = [
        getattr(tools, name)
        for name in dir(tools)
        if not name.startswith("_") and callable(getattr(tools, name))
    ]
    tool_docs = "\n\n".join(describe_tool(m) for m in tool_methods)
    table_docs = describe_tables(tables)

    return f"""{SYSTEM_INSTRUCTIONS}

## Available Tables

{table_docs}

## Available Tools

{tool_docs}

## Variables in Scope

Tables: {', '.join(tables.keys()) if tables else 'none'}
Libraries: pd (pandas), np (numpy)
"""
