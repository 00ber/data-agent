# Data Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing analytics agent with a coding agent (~450 LOC) where the LLM writes Python code calling validated tool functions in a RestrictedPython sandbox, streaming artifact-producing events to the UI via SSE.

**Architecture:** The LLM receives table schemas + tool signatures, responds with `{plan, code}` structured output. Code executes in a restricted sandbox with tools and DataFrames in scope. Tools validate inputs, produce artifacts, and return DataFrames. `final_answer()` terminates the loop via exception. Events stream to the frontend via SSE.

**Tech Stack:** Python 3.12+, OpenAI (structured output), pandas, RestrictedPython, matplotlib, FastAPI, sse-starlette, pytest, pytest-asyncio

**Design docs:** `docs/AGENT_REDESIGN.md`, `docs/PROJECT_STRUCTURE.md`, `docs/API_DESIGN.md`, `docs/UI_DESIGN.md`

**Engineering ethos:** `ENGINEERING.md` — TDD (Red → Green → Refactor), fail early and loudly, boring code, scope discipline.

**Note:** The user handles all git commits. Steps marked CHECKPOINT indicate a natural commit point.

---

## File Structure

### New files to create

```
agent/
├── __init__.py       # Public API: run(), Session, Event, load_file
├── agent.py          # run() async generator, CodeStep model
├── events.py         # Event dataclass, FinalAnswer exception
├── loaders.py        # load_file() → (name, DataFrame)
├── prompts.py        # build_prompt(), describe_tool(), describe_tables()
├── sandbox.py        # execute(code, env) with RestrictedPython
├── session.py        # Session, Artifact, AgentConfig dataclasses
└── tools.py          # Tools class with all tool methods

api/
├── __init__.py       # empty
├── main.py           # FastAPI app, routes, SSE streaming
├── sessions.py       # SessionManager (create/get/destroy)
└── datasets.py       # SAMPLE_DATASETS, get_dataset_paths

tests/
├── conftest.py       # Shared fixtures (DataFrames + Session factory)
├── fixtures/
│   ├── orders.csv
│   ├── customers.csv
│   └── products.csv
├── test_events.py
├── test_session.py
├── test_loaders.py
├── test_sandbox.py
├── test_tools.py
├── test_prompts.py
├── test_agent.py
└── test_api.py
```

### Files to archive

Everything not in `docs/`, `.env`, `.env.sample`, `.gitignore`, `CLAUDE.md`, `ENGINEERING.md`, `AGENTS.md`, `README.md`, `data/` (sample datasets only), `.claude/`.

---

## Phase 0: Archive & Scaffold

### Task 1: Archive existing code and create project structure

**Files:**
- Archive: `src/`, `apps/`, `tests/`, `pyproject.toml`, `uv.lock`, `workshop_*.ipynb`, `data/generate_dataset.py`
- Create: `agent/__init__.py`, `api/__init__.py`, `tests/__init__.py`, new `pyproject.toml`

- [ ] **Step 1: Create archive directory and move existing code**

```bash
mkdir archive
mv src archive/
mv apps archive/
mv tests archive/
mv pyproject.toml archive/
mv uv.lock archive/
mv workshop_*.ipynb archive/
mv data/generate_dataset.py archive/
```

- [ ] **Step 2: Create new directory structure**

```bash
mkdir -p agent
mkdir -p api
mkdir -p tests/fixtures
```

- [ ] **Step 3: Create empty `__init__.py` files**

Create `agent/__init__.py` — empty for now (populated in Task 13).
Create `api/__init__.py` — empty.

- [ ] **Step 4: Write new `pyproject.toml`**

```toml
[project]
name = "analytics-agent"
version = "0.2.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "pandas>=2.0",
    "openai>=1.60",
    "RestrictedPython>=7.0",
    "matplotlib>=3.8",
    "openpyxl>=3.1",
    "pyarrow>=15.0",
    "python-dotenv>=1.0",
    "numpy>=1.26",
]

[project.optional-dependencies]
api = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sse-starlette>=2.0",
    "python-multipart>=0.0.18",
]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["agent"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
```

- [ ] **Step 5: Update `.gitignore`**

Add these entries:

```
# Archive (reference only)
archive/

# Frontend build output
ui/dist/
ui/node_modules/
```

- [ ] **Step 6: Verify sample datasets exist**

The `data/` directory must contain sample CSV files that the API serves.
Confirm these exist (they should already be in the repo):

```bash
ls data/ecommerce/*.csv data/superstore/*.csv data/world_indicators/*.csv
```

Expected: `customers.csv`, `orders.csv`, `order_items.csv`, `products.csv`,
`returns.csv` in ecommerce; `orders.csv`, `returns.csv` in superstore;
`gapminder.csv` in world_indicators.

- [ ] **Step 7: Install dependencies and verify**

```bash
uv sync --all-extras
```

Run: `uv run python -c "import pandas; import pydantic; import RestrictedPython; print('OK')"`
Expected: `OK`

**CHECKPOINT: Archive complete, clean project structure, dependencies install.**

---

## Phase 1: Foundation

### Task 2: Test fixtures and conftest

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/orders.csv`, `tests/fixtures/customers.csv`, `tests/fixtures/products.csv`

- [ ] **Step 1: Create test CSV fixtures**

`tests/fixtures/orders.csv`:
```csv
order_id,customer_id,product_id,date,revenue,quantity,category,quarter,region
1,101,1,2024-01-15,150.00,3,Electronics,Q1,West
2,102,2,2024-01-20,250.00,5,Electronics,Q1,East
3,101,3,2024-02-10,75.00,1,Home,Q1,West
4,103,1,2024-03-05,300.00,6,Electronics,Q1,North
5,102,2,2024-04-15,120.00,2,Electronics,Q2,East
6,101,3,2024-05-01,200.00,4,Home,Q2,West
7,103,1,2024-06-20,180.00,3,Electronics,Q2,North
8,102,2,2024-07-10,350.00,7,Electronics,Q3,East
9,101,1,2024-08-15,90.00,2,Electronics,Q3,West
10,103,3,2024-09-25,275.00,5,Home,Q3,North
```

`tests/fixtures/customers.csv`:
```csv
customer_id,name,segment,region,signup_date
101,Alice,enterprise,West,2023-01-10
102,Bob,smb,East,2023-03-22
103,Carol,enterprise,North,2023-06-15
```

`tests/fixtures/products.csv`:
```csv
product_id,name,category,price,cost
1,Widget A,Electronics,50.00,20.00
2,Widget B,Electronics,30.00,12.00
3,Gadget C,Home,25.00,10.00
```

- [ ] **Step 2: Create `tests/conftest.py`**

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def orders_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "orders.csv")


@pytest.fixture
def customers_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "customers.csv")


@pytest.fixture
def products_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "products.csv")
```

- [ ] **Step 3: Verify fixtures load**

Run: `uv run pytest tests/ --collect-only`
Expected: No errors, conftest loads.

**CHECKPOINT: Test infrastructure ready.**

---

### Task 3: `agent/events.py`

**Files:**
- Create: `tests/test_events.py`
- Create: `agent/events.py`

- [ ] **Step 1: Write failing tests**

`tests/test_events.py`:
```python
import pytest

from agent.events import Event, FinalAnswer


class TestEvent:
    def test_create_thinking_event(self):
        event = Event("thinking", {"text": "Analyzing data..."})

        assert event.kind == "thinking"
        assert event.data == {"text": "Analyzing data..."}

    def test_create_artifact_event(self):
        event = Event("artifact", {"id": "a1", "kind": "table", "title": "Sales"})

        assert event.kind == "artifact"
        assert event.data["id"] == "a1"


class TestFinalAnswer:
    def test_stores_answer_text(self):
        exc = FinalAnswer("Revenue is $8.2M")

        assert exc.answer == "Revenue is $8.2M"

    def test_is_exception(self):
        exc = FinalAnswer("done")

        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(FinalAnswer) as exc_info:
            raise FinalAnswer("The answer is 42")

        assert exc_info.value.answer == "The answer is 42"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.events'`

- [ ] **Step 3: Implement `agent/events.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_events.py -v`
Expected: All 4 tests PASS.

**CHECKPOINT: events.py complete.**

---

### Task 4: `agent/session.py`

**Files:**
- Create: `tests/test_session.py`
- Create: `agent/session.py`

- [ ] **Step 1: Write failing tests**

`tests/test_session.py`:
```python
import pandas as pd

from agent.session import AgentConfig, Artifact, Session


class TestAgentConfig:
    def test_defaults(self):
        config = AgentConfig()

        assert config.model == "gpt-4o"
        assert config.max_steps == 10
        assert config.temperature == 0.0

    def test_custom_values(self):
        config = AgentConfig(model="gpt-4o-mini", max_steps=5, temperature=0.7)

        assert config.model == "gpt-4o-mini"
        assert config.max_steps == 5
        assert config.temperature == 0.7


class TestArtifact:
    def test_create_table_artifact(self):
        artifact = Artifact(
            id="art_001",
            kind="table",
            title="Filtered sales",
            data={"columns": ["a"], "rows": [[1]]},
        )

        assert artifact.id == "art_001"
        assert artifact.kind == "table"
        assert artifact.title == "Filtered sales"

    def test_create_chart_artifact(self):
        artifact = Artifact(
            id="art_002",
            kind="chart",
            title="Revenue by Quarter",
            data={"chart_type": "bar"},
        )

        assert artifact.kind == "chart"


class TestSession:
    def test_create_with_defaults(self):
        session = Session()

        assert session.tables == {}
        assert session.artifacts == []
        assert session.history == []
        assert isinstance(session.config, AgentConfig)

    def test_add_table(self):
        session = Session()
        df = pd.DataFrame({"a": [1, 2, 3]})

        session.tables["sales"] = df

        assert "sales" in session.tables
        assert len(session.tables["sales"]) == 3

    def test_add_artifact(self):
        session = Session()
        artifact = Artifact(id="a1", kind="stat", title="Total", data={"value": 42})

        session.artifacts.append(artifact)

        assert len(session.artifacts) == 1
        assert session.artifacts[0].title == "Total"

    def test_history_accumulates(self):
        session = Session()

        session.history.append({"role": "user", "content": "hello"})
        session.history.append({"role": "assistant", "content": "hi"})

        assert len(session.history) == 2
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_session.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.session'`

- [ ] **Step 3: Implement `agent/session.py`**

```python
"""Session state: tables, artifacts, history, config."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd


@dataclass
class AgentConfig:
    """Configuration for the agent's LLM calls."""

    model: str = "gpt-4o"
    max_steps: int = 10
    temperature: float = 0.0


@dataclass
class Artifact:
    """A displayable output: table, chart, or stat card."""

    id: str
    kind: Literal["table", "chart", "stat"]
    title: str
    data: dict[str, Any]


@dataclass
class Session:
    """All state for one analysis session."""

    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    config: AgentConfig = field(default_factory=AgentConfig)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_session.py -v`
Expected: All 7 tests PASS.

**CHECKPOINT: session.py complete.**

---

### Task 5: `agent/loaders.py`

**Files:**
- Create: `tests/test_loaders.py`
- Create: `agent/loaders.py`

- [ ] **Step 1: Write failing tests**

`tests/test_loaders.py`:
```python
from pathlib import Path

import pandas as pd
import pytest

from agent.loaders import load_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLoadFile:
    def test_load_csv(self):
        name, df = load_file(FIXTURES_DIR / "orders.csv")

        assert name == "orders"
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "revenue" in df.columns

    def test_infers_table_name_from_filename(self):
        name, _ = load_file(FIXTURES_DIR / "customers.csv")

        assert name == "customers"

    def test_normalizes_table_name(self, tmp_path):
        csv = tmp_path / "My Sales-Data.csv"
        csv.write_text("a,b\n1,2\n")

        name, _ = load_file(csv)

        assert name == "my_sales_data"

    def test_unsupported_extension_raises(self, tmp_path):
        txt = tmp_path / "data.txt"
        txt.write_text("hello")

        with pytest.raises(ValueError, match="Unsupported file type: .txt"):
            load_file(txt)

    def test_unsupported_error_lists_supported_types(self, tmp_path):
        txt = tmp_path / "data.json"
        txt.write_text("{}")

        with pytest.raises(ValueError, match=".csv"):
            load_file(txt)

    def test_load_xlsx(self, tmp_path):
        xlsx = tmp_path / "sales.xlsx"
        pd.DataFrame({"x": [1, 2]}).to_excel(xlsx, index=False)

        name, df = load_file(xlsx)

        assert name == "sales"
        assert len(df) == 2

    def test_load_parquet(self, tmp_path):
        pq = tmp_path / "events.parquet"
        pd.DataFrame({"x": [1, 2, 3]}).to_parquet(pq, index=False)

        name, df = load_file(pq)

        assert name == "events"
        assert len(df) == 3

    def test_accepts_string_path(self):
        name, df = load_file(str(FIXTURES_DIR / "products.csv"))

        assert name == "products"
        assert len(df) == 3
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_loaders.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.loaders'`

- [ ] **Step 3: Implement `agent/loaders.py`**

```python
"""File loaders for CSV, XLSX, and Parquet."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".parquet"}


def load_file(path: str | Path) -> tuple[str, pd.DataFrame]:
    """Load a data file and return (table_name, DataFrame).

    Table name is inferred from the filename: lowercased, spaces and
    hyphens replaced with underscores.

    Raises ValueError for unsupported file types.
    """
    path = Path(path)

    if path.suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type: {path.suffix}. Supported: {supported}"
        )

    name = path.stem.lower().replace(" ", "_").replace("-", "_")

    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix == ".xlsx":
        df = pd.read_excel(path)
    elif path.suffix == ".parquet":
        df = pd.read_parquet(path)

    return name, df
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_loaders.py -v`
Expected: All 8 tests PASS.

**CHECKPOINT: loaders.py complete.**

---

### Task 6: `agent/sandbox.py`

This is the most critical module. RestrictedPython compiles and executes
LLM-generated code with safety guards.

**Files:**
- Create: `tests/test_sandbox.py`
- Create: `agent/sandbox.py`

- [ ] **Step 1: Write failing tests**

`tests/test_sandbox.py`:
```python
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
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_sandbox.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.sandbox'`

- [ ] **Step 3: Implement `agent/sandbox.py`**

```python
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

_RESULT_VAR = "_sandbox_result_"


@dataclass
class SandboxResult:
    """Result of sandbox execution."""

    output: str
    is_error: bool


def _make_builtins() -> dict:
    """Build the safe builtins dict with required guards."""
    builtins = dict(safe_builtins)
    builtins["_getiter_"] = default_guarded_getiter
    builtins["_unpack_sequence_"] = guarded_unpack_sequence
    builtins["_getattr_"] = safer_getattr
    # Allow item/attribute writes (needed for df['col'] = ...)
    builtins["_write_"] = lambda x: x
    builtins["_getitem_"] = lambda obj, key: obj[key]
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_sandbox.py -v`
Expected: All tests PASS.

If RestrictedPython's guards don't match expected behavior for some tests
(e.g., dunder access may produce a different error message), adjust the
assertions to match the actual RestrictedPython error format. The behavior
(blocked) is what matters, not the exact message.

- [ ] **Step 5: Refactor if needed**

Review the sandbox implementation. If any test required workarounds or
unexpected guard behavior, clean up while green.

**CHECKPOINT: sandbox.py complete. Phase 1 done — all foundation modules tested.**

---

## Phase 2: Tools

### Task 7: Tools class setup + `filter`

Establishes the Tools pattern: constructor, `_resolve`, `_emit_artifact`,
and the first data tool.

**Files:**
- Create: `tests/test_tools.py`
- Create: `agent/tools.py`

- [ ] **Step 1: Write failing tests for `_resolve` and `filter`**

`tests/test_tools.py`:
```python
import pandas as pd
import pytest

from agent.events import Event
from agent.session import Session, Artifact
from agent.tools import Tools


@pytest.fixture
def session_with_orders(orders_df):
    session = Session()
    session.tables["orders"] = orders_df
    return session


@pytest.fixture
def collected_events():
    return []


@pytest.fixture
def tools(session_with_orders, collected_events):
    return Tools(session_with_orders, emit=collected_events.append)


class TestResolve:
    def test_resolve_string_returns_dataframe(self, tools, orders_df):
        result = tools._resolve("orders")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(orders_df)

    def test_resolve_dataframe_returns_same(self, tools):
        df = pd.DataFrame({"x": [1]})

        result = tools._resolve(df)

        assert result is df

    def test_resolve_unknown_table_raises(self, tools):
        with pytest.raises(ValueError, match="Unknown table: 'missing'"):
            tools._resolve("missing")

    def test_resolve_error_lists_available_tables(self, tools):
        with pytest.raises(ValueError, match="orders"):
            tools._resolve("missing")


class TestFilter:
    def test_equals(self, tools, collected_events):
        result = tools.filter("orders", "category", "==", "Electronics")

        assert isinstance(result, pd.DataFrame)
        assert all(result["category"] == "Electronics")

    def test_greater_than(self, tools):
        result = tools.filter("orders", "revenue", ">", 200)

        assert all(result["revenue"] > 200)

    def test_less_than(self, tools):
        result = tools.filter("orders", "revenue", "<", 100)

        assert all(result["revenue"] < 100)

    def test_not_equals(self, tools):
        result = tools.filter("orders", "region", "!=", "West")

        assert all(result["region"] != "West")

    def test_contains(self, tools):
        result = tools.filter("orders", "category", "contains", "Elec")

        assert all("Elec" in val for val in result["category"])

    def test_emits_table_artifact(self, tools, collected_events):
        tools.filter("orders", "category", "==", "Home")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "table"

    def test_invalid_column_raises(self, tools):
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            tools.filter("orders", "nonexistent", "==", "x")

    def test_error_lists_available_columns(self, tools):
        with pytest.raises(ValueError, match="revenue"):
            tools.filter("orders", "nonexistent", "==", "x")

    def test_invalid_operator_raises(self, tools):
        with pytest.raises(ValueError, match="Unknown operator: 'like'"):
            tools.filter("orders", "category", "like", "x")

    def test_accepts_dataframe_input(self, tools, orders_df):
        result = tools.filter(orders_df, "category", "==", "Home")

        assert all(result["category"] == "Home")
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools'`

- [ ] **Step 3: Implement Tools class with `_resolve`, `_emit_artifact`, and `filter`**

```python
"""Analytics tools — every public method is a tool the LLM can call."""
from __future__ import annotations

import uuid
from typing import Any, Callable

import pandas as pd

from agent.events import Event, FinalAnswer
from agent.session import Artifact, Session

FILTER_OPS = {
    "==": lambda s, v: s == v,
    "!=": lambda s, v: s != v,
    ">": lambda s, v: s > v,
    "<": lambda s, v: s < v,
    ">=": lambda s, v: s >= v,
    "<=": lambda s, v: s <= v,
    "contains": lambda s, v: s.str.contains(v, na=False),
    "startswith": lambda s, v: s.str.startswith(v, na=False),
    "endswith": lambda s, v: s.str.endswith(v, na=False),
}


class Tools:
    """Analytics tools bound to a session.

    Public methods are tools (available in the sandbox).
    Private methods are helpers.
    """

    def __init__(self, session: Session, emit: Callable[[Event], None]) -> None:
        self._session = session
        self._emit = emit

    # -- Private helpers -----------------------------------------------

    def _resolve(self, table: str | pd.DataFrame) -> pd.DataFrame:
        """Resolve a table name to a DataFrame, or pass through a DataFrame."""
        if isinstance(table, pd.DataFrame):
            return table
        if table not in self._session.tables:
            available = ", ".join(sorted(self._session.tables.keys()))
            raise ValueError(
                f"Unknown table: '{table}'. Available tables: {available}"
            )
        return self._session.tables[table]

    def _emit_artifact(
        self, kind: str, title: str, data: dict[str, Any]
    ) -> Artifact:
        """Create an artifact, store it in session, and emit an event."""
        artifact = Artifact(
            id=f"art_{uuid.uuid4().hex[:8]}",
            kind=kind,
            title=title,
            data=data,
        )
        self._session.artifacts.append(artifact)
        self._emit(Event("artifact", {
            "id": artifact.id,
            "kind": artifact.kind,
            "title": artifact.title,
            "data": artifact.data,
        }))
        return artifact

    def _validate_column(self, df: pd.DataFrame, column: str) -> None:
        """Raise ValueError if column doesn't exist in the DataFrame."""
        if column not in df.columns:
            available = ", ".join(df.columns)
            raise ValueError(
                f"Column '{column}' not found. Available columns: {available}"
            )

    def _table_data(self, df: pd.DataFrame) -> dict:
        """Convert a DataFrame to artifact data format."""
        return {
            "columns": list(df.columns),
            "rows": df.values.tolist(),
            "shape": list(df.shape),
        }

    # -- Data tools (return DataFrame, emit table artifact) ------------

    def filter(
        self, table: str | pd.DataFrame, column: str, op: str, value: Any
    ) -> pd.DataFrame:
        """Filter rows where column matches the condition.

        Args:
            table: Table name or DataFrame.
            column: Column to filter on.
            op: Operator — ==, !=, >, <, >=, <=, contains, startswith, endswith.
            value: Value to compare against.

        Returns:
            Filtered DataFrame.
        """
        df = self._resolve(table)
        self._validate_column(df, column)

        if op not in FILTER_OPS:
            raise ValueError(
                f"Unknown operator: '{op}'. "
                f"Supported: {', '.join(sorted(FILTER_OPS.keys()))}"
            )

        mask = FILTER_OPS[op](df[column], value)
        filtered = df[mask].reset_index(drop=True)

        self._emit_artifact(
            "table",
            f"Filtered: {column} {op} {value}",
            self._table_data(filtered),
        )
        return filtered
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_tools.py -v`
Expected: All tests PASS.

**CHECKPOINT: Tools pattern established with filter.**

---

### Task 8: `group_by`, `sort`, `join`

**Files:**
- Modify: `tests/test_tools.py` (add test classes)
- Modify: `agent/tools.py` (add methods)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_tools.py`:

```python
class TestGroupBy:
    def test_sum_aggregation(self, tools):
        result = tools.group_by("orders", "category", "revenue", "sum")

        assert len(result) == 2  # Electronics + Home
        assert "category" in result.columns
        assert "revenue" in result.columns

    def test_mean_aggregation(self, tools):
        result = tools.group_by("orders", "category", "revenue", "mean")

        assert len(result) == 2

    def test_count_aggregation(self, tools):
        result = tools.group_by("orders", "category", "revenue", "count")

        assert len(result) == 2

    def test_emits_table_artifact(self, tools, collected_events):
        tools.group_by("orders", "category", "revenue", "sum")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert "category" in artifact_events[0].data["title"].lower() or "group" in artifact_events[0].data["title"].lower()

    def test_invalid_column_raises(self, tools):
        with pytest.raises(ValueError, match="Column 'fake' not found"):
            tools.group_by("orders", "fake", "revenue", "sum")

    def test_invalid_agg_raises(self, tools):
        with pytest.raises(ValueError, match="Unknown aggregation: 'mode'"):
            tools.group_by("orders", "category", "revenue", "mode")

    def test_accepts_dataframe_input(self, tools, orders_df):
        result = tools.group_by(orders_df, "category", "revenue", "sum")

        assert len(result) == 2


class TestSort:
    def test_ascending(self, tools):
        result = tools.sort("orders", "revenue")

        assert list(result["revenue"]) == sorted(result["revenue"])

    def test_descending(self, tools):
        result = tools.sort("orders", "revenue", ascending=False)

        assert list(result["revenue"]) == sorted(result["revenue"], reverse=True)

    def test_emits_table_artifact(self, tools, collected_events):
        tools.sort("orders", "revenue")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1

    def test_invalid_column_raises(self, tools):
        with pytest.raises(ValueError, match="Column 'fake' not found"):
            tools.sort("orders", "fake")

    def test_accepts_dataframe_input(self, tools, orders_df):
        result = tools.sort(orders_df, "revenue")

        assert list(result["revenue"]) == sorted(result["revenue"])


class TestJoin:
    def test_inner_join(self, tools, customers_df):
        tools._session.tables["customers"] = customers_df

        result = tools.join("orders", "customers", on="customer_id")

        assert "name" in result.columns
        assert "revenue" in result.columns
        assert len(result) > 0

    def test_emits_table_artifact(self, tools, customers_df, collected_events):
        tools._session.tables["customers"] = customers_df

        tools.join("orders", "customers", on="customer_id")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1

    def test_invalid_join_column_raises(self, tools, customers_df):
        tools._session.tables["customers"] = customers_df

        with pytest.raises(ValueError, match="not found"):
            tools.join("orders", "customers", on="nonexistent")

    def test_accepts_dataframe_inputs(self, tools, orders_df, customers_df):
        result = tools.join(orders_df, customers_df, on="customer_id")

        assert "name" in result.columns
```

- [ ] **Step 2: Run new tests — verify they fail**

Run: `uv run pytest tests/test_tools.py::TestGroupBy tests/test_tools.py::TestSort tests/test_tools.py::TestJoin -v`
Expected: FAIL — `AttributeError: 'Tools' object has no attribute 'group_by'`

- [ ] **Step 3: Implement `group_by`, `sort`, `join` in `agent/tools.py`**

Add to the `Tools` class:

```python
    AGGREGATIONS = {"sum", "mean", "count", "min", "max", "median", "std"}

    def group_by(
        self,
        table: str | pd.DataFrame,
        by: str,
        column: str,
        agg: str,
    ) -> pd.DataFrame:
        """Group by a column and aggregate another.

        Args:
            table: Table name or DataFrame.
            by: Column to group by.
            column: Column to aggregate.
            agg: Aggregation — sum, mean, count, min, max, median, std.

        Returns:
            Aggregated DataFrame.
        """
        df = self._resolve(table)
        self._validate_column(df, by)
        self._validate_column(df, column)

        if agg not in self.AGGREGATIONS:
            raise ValueError(
                f"Unknown aggregation: '{agg}'. "
                f"Supported: {', '.join(sorted(self.AGGREGATIONS))}"
            )

        grouped = df.groupby(by, as_index=False)[column].agg(agg)

        self._emit_artifact(
            "table",
            f"{agg}({column}) by {by}",
            self._table_data(grouped),
        )
        return grouped

    def sort(
        self,
        table: str | pd.DataFrame,
        by: str,
        ascending: bool = True,
    ) -> pd.DataFrame:
        """Sort rows by a column.

        Args:
            table: Table name or DataFrame.
            by: Column to sort by.
            ascending: Sort direction (default True).

        Returns:
            Sorted DataFrame.
        """
        df = self._resolve(table)
        self._validate_column(df, by)

        sorted_df = df.sort_values(by, ascending=ascending).reset_index(drop=True)

        direction = "ascending" if ascending else "descending"
        self._emit_artifact(
            "table",
            f"Sorted by {by} ({direction})",
            self._table_data(sorted_df),
        )
        return sorted_df

    def join(
        self,
        left: str | pd.DataFrame,
        right: str | pd.DataFrame,
        on: str,
        how: str = "inner",
    ) -> pd.DataFrame:
        """Join two tables on a shared column.

        Args:
            left: Left table name or DataFrame.
            right: Right table name or DataFrame.
            on: Column to join on (must exist in both).
            how: Join type — inner, left, right, outer (default inner).

        Returns:
            Joined DataFrame.
        """
        left_df = self._resolve(left)
        right_df = self._resolve(right)

        if on not in left_df.columns:
            raise ValueError(
                f"Join column '{on}' not found in left table. "
                f"Available: {', '.join(left_df.columns)}"
            )
        if on not in right_df.columns:
            raise ValueError(
                f"Join column '{on}' not found in right table. "
                f"Available: {', '.join(right_df.columns)}"
            )

        joined = left_df.merge(right_df, on=on, how=how)

        self._emit_artifact(
            "table",
            f"Joined on {on} ({how})",
            self._table_data(joined),
        )
        return joined
```

- [ ] **Step 4: Run all tool tests — verify they pass**

Run: `uv run pytest tests/test_tools.py -v`
Expected: All tests PASS.

**CHECKPOINT: All data tools complete.**

---

### Task 9: Display tools — `show_chart`, `show_table`, `show_stat`

**Files:**
- Modify: `tests/test_tools.py` (add test classes)
- Modify: `agent/tools.py` (add methods)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_tools.py`:

```python
class TestShowChart:
    def test_emits_chart_artifact(self, tools, collected_events):
        df = pd.DataFrame({"quarter": ["Q1", "Q2"], "revenue": [100, 200]})

        result = tools.show_chart(df, kind="bar", title="Revenue by Quarter")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "chart"
        assert artifact_events[0].data["title"] == "Revenue by Quarter"

    def test_returns_confirmation_string(self, tools):
        df = pd.DataFrame({"x": [1], "y": [2]})

        result = tools.show_chart(df, kind="line", title="Test")

        assert isinstance(result, str)
        assert "chart" in result.lower() or "Test" in result

    def test_chart_data_includes_records(self, tools, collected_events):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})

        tools.show_chart(df, kind="scatter", title="Test")

        artifact = collected_events[0].data
        assert "data" in artifact
        assert artifact["data"]["chart_type"] == "scatter"

    def test_invalid_chart_kind_raises(self, tools):
        df = pd.DataFrame({"x": [1]})

        with pytest.raises(ValueError, match="Unknown chart type: 'heatmap'"):
            tools.show_chart(df, kind="heatmap", title="Test")

    def test_accepts_table_name(self, tools, collected_events):
        tools.show_chart("orders", kind="bar", title="Orders")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1


class TestShowTable:
    def test_emits_table_artifact(self, tools, collected_events):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        tools.show_table(df, title="My Table")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "table"
        assert artifact_events[0].data["title"] == "My Table"

    def test_returns_confirmation_string(self, tools):
        df = pd.DataFrame({"a": [1]})

        result = tools.show_table(df, title="Test")

        assert isinstance(result, str)

    def test_accepts_table_name(self, tools, collected_events):
        tools.show_table("orders", title="All Orders")

        assert len(collected_events) == 1


class TestShowStat:
    def test_emits_stat_artifact(self, tools, collected_events):
        tools.show_stat("Total Revenue", 8200000)

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "stat"

    def test_stat_data_has_label_and_value(self, tools, collected_events):
        tools.show_stat("Avg Order Value", 150.50)

        artifact = collected_events[0].data
        assert artifact["data"]["label"] == "Avg Order Value"
        assert artifact["data"]["value"] == 150.50

    def test_returns_confirmation_string(self, tools):
        result = tools.show_stat("Count", 42)

        assert isinstance(result, str)
```

- [ ] **Step 2: Run new tests — verify they fail**

Run: `uv run pytest tests/test_tools.py::TestShowChart tests/test_tools.py::TestShowTable tests/test_tools.py::TestShowStat -v`
Expected: FAIL — `AttributeError: 'Tools' object has no attribute 'show_chart'`

- [ ] **Step 3: Implement display tools in `agent/tools.py`**

Add to the `Tools` class:

```python
    CHART_TYPES = {"bar", "line", "scatter", "pie", "histogram"}

    def show_chart(
        self,
        data: str | pd.DataFrame,
        kind: str = "bar",
        title: str = "",
    ) -> str:
        """Display a chart artifact.

        Args:
            data: Table name or DataFrame to chart.
            kind: Chart type — bar, line, scatter, pie, histogram.
            title: Chart title.

        Returns:
            Confirmation string.
        """
        df = self._resolve(data)

        if kind not in self.CHART_TYPES:
            raise ValueError(
                f"Unknown chart type: '{kind}'. "
                f"Supported: {', '.join(sorted(self.CHART_TYPES))}"
            )

        self._emit_artifact("chart", title, {
            "chart_type": kind,
            "columns": list(df.columns),
            "records": df.to_dict(orient="records"),
        })
        return f"Displayed {kind} chart: {title}"

    def show_table(self, data: str | pd.DataFrame, title: str = "") -> str:
        """Display a formatted table artifact.

        Args:
            data: Table name or DataFrame to display.
            title: Table title.

        Returns:
            Confirmation string.
        """
        df = self._resolve(data)

        self._emit_artifact("table", title, self._table_data(df))
        return f"Displayed table: {title} ({len(df)} rows)"

    def show_stat(self, label: str, value: Any) -> str:
        """Display a stat card artifact.

        Args:
            label: Stat label (e.g. "Total Revenue").
            value: Stat value (e.g. 8200000).

        Returns:
            Confirmation string.
        """
        self._emit_artifact("stat", label, {
            "label": label,
            "value": value,
        })
        return f"Displayed stat: {label} = {value}"
```

- [ ] **Step 4: Run all tool tests — verify they pass**

Run: `uv run pytest tests/test_tools.py -v`
Expected: All tests PASS.

**CHECKPOINT: Display tools complete.**

---

### Task 10: `final_answer`

**Files:**
- Modify: `tests/test_tools.py` (add test class)
- Modify: `agent/tools.py` (add method)

- [ ] **Step 1: Write failing test**

Add to `tests/test_tools.py`:

```python
class TestFinalAnswer:
    def test_raises_final_answer_exception(self, tools):
        with pytest.raises(FinalAnswer) as exc_info:
            tools.final_answer("Revenue is $8.2M")

        assert exc_info.value.answer == "Revenue is $8.2M"
```

Add `from agent.events import FinalAnswer` to the test file imports.

- [ ] **Step 2: Run test — verify it fails**

Run: `uv run pytest tests/test_tools.py::TestFinalAnswer -v`
Expected: FAIL — `AttributeError: 'Tools' object has no attribute 'final_answer'`

- [ ] **Step 3: Implement `final_answer` in `agent/tools.py`**

Add to the `Tools` class:

```python
    def final_answer(self, answer: str) -> None:
        """Terminate the agent loop with a final answer.

        Args:
            answer: The answer text to return to the user.

        Raises:
            FinalAnswer: Always. This is how the agent loop terminates.
        """
        raise FinalAnswer(answer)
```

- [ ] **Step 4: Run all tool tests — verify they pass**

Run: `uv run pytest tests/test_tools.py -v`
Expected: All tests PASS.

**CHECKPOINT: Phase 2 done — all tools tested and working.**

---

## Phase 3: Prompts + Agent Loop

### Task 11: `agent/prompts.py`

**Files:**
- Create: `tests/test_prompts.py`
- Create: `agent/prompts.py`

- [ ] **Step 1: Write failing tests**

`tests/test_prompts.py`:
```python
import pandas as pd

from agent.tools import Tools
from agent.session import Session
from agent.prompts import describe_tool, describe_tables, build_prompt


class TestDescribeTool:
    def test_includes_function_name(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "filter" in result

    def test_includes_parameters(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "column" in result
        assert "op" in result

    def test_includes_docstring(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "Filter rows" in result

    def test_skips_self_parameter(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "self" not in result


class TestDescribeTables:
    def test_includes_table_name(self):
        tables = {"sales": pd.DataFrame({"a": [1, 2, 3]})}

        result = describe_tables(tables)

        assert "sales" in result

    def test_includes_row_count(self):
        tables = {"sales": pd.DataFrame({"a": [1, 2, 3]})}

        result = describe_tables(tables)

        assert "3" in result

    def test_includes_column_info(self):
        tables = {"orders": pd.DataFrame({"revenue": [1.0], "category": ["A"]})}

        result = describe_tables(tables)

        assert "revenue" in result
        assert "category" in result

    def test_multiple_tables(self):
        tables = {
            "orders": pd.DataFrame({"a": [1]}),
            "customers": pd.DataFrame({"b": [2]}),
        }

        result = describe_tables(tables)

        assert "orders" in result
        assert "customers" in result


class TestBuildPrompt:
    def test_includes_table_descriptions(self):
        tables = {"sales": pd.DataFrame({"revenue": [1.0]})}
        session = Session(tables=tables)
        tools = Tools(session, emit=lambda e: None)

        prompt = build_prompt(session.tables, tools)

        assert "sales" in prompt
        assert "revenue" in prompt

    def test_includes_tool_signatures(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        prompt = build_prompt(session.tables, tools)

        assert "filter" in prompt
        assert "group_by" in prompt
        assert "show_chart" in prompt
        assert "final_answer" in prompt

    def test_includes_system_instructions(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        prompt = build_prompt(session.tables, tools)

        # Should instruct the LLM about its role and how to use tools
        assert "code" in prompt.lower() or "python" in prompt.lower()
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.prompts'`

- [ ] **Step 3: Implement `agent/prompts.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_prompts.py -v`
Expected: All tests PASS.

**CHECKPOINT: prompts.py complete.**

---

### Task 12: `agent/agent.py`

The agent loop: LLM call → execute → yield events → repeat.

**Files:**
- Create: `tests/test_agent.py`
- Create: `agent/agent.py`

- [ ] **Step 1: Write failing tests**

The agent loop uses OpenAI for structured output. Tests use a simple fake:
a callable that returns `CodeStep` objects from a predetermined list.

`tests/test_agent.py`:
```python
import pandas as pd
import pytest

from agent.agent import run, CodeStep
from agent.events import Event, FinalAnswer
from agent.session import Session


def make_fake_llm(responses: list[CodeStep]):
    """Create a fake LLM callable that returns predetermined responses."""
    iterator = iter(responses)

    async def fake_llm(messages, **kwargs):
        return next(iterator)

    return fake_llm


class TestCodeStep:
    def test_has_plan_and_code(self):
        step = CodeStep(plan="Analyze revenue", code="print(1)")

        assert step.plan == "Analyze revenue"
        assert step.code == "print(1)"


class TestRunSingleStep:
    @pytest.mark.asyncio
    async def test_yields_thinking_event(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Thinking...", code="final_answer('done')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        thinking_events = [e for e in events if e.kind == "thinking"]
        assert len(thinking_events) == 1
        assert thinking_events[0].data["text"] == "Thinking..."

    @pytest.mark.asyncio
    async def test_yields_code_event(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('done')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        code_events = [e for e in events if e.kind == "code"]
        assert len(code_events) == 1
        assert "final_answer" in code_events[0].data["text"]

    @pytest.mark.asyncio
    async def test_yields_answer_event_on_final_answer(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('Revenue is $100')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        answer_events = [e for e in events if e.kind == "answer"]
        assert len(answer_events) == 1
        assert answer_events[0].data["text"] == "Revenue is $100"

    @pytest.mark.asyncio
    async def test_terminates_on_final_answer(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('done')"),
            CodeStep(plan="Should not run", code="print('bad')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        thinking_events = [e for e in events if e.kind == "thinking"]
        assert len(thinking_events) == 1  # Only first step ran


class TestRunMultiStep:
    @pytest.mark.asyncio
    async def test_error_feeds_back_to_next_step(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Try bad code", code="1 / 0"),
            CodeStep(plan="Fix it", code="final_answer('fixed')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        error_events = [e for e in events if e.kind == "error"]
        assert len(error_events) == 1
        assert "ZeroDivisionError" in error_events[0].data["text"]

        answer_events = [e for e in events if e.kind == "answer"]
        assert len(answer_events) == 1

    @pytest.mark.asyncio
    async def test_max_steps_respected(self):
        session = Session()
        session.config.max_steps = 2
        session.tables["x"] = pd.DataFrame({"a": [1]})
        # LLM never calls final_answer
        fake_llm = make_fake_llm([
            CodeStep(plan="Step 1", code="print('one')"),
            CodeStep(plan="Step 2", code="print('two')"),
            CodeStep(plan="Step 3", code="print('three')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        thinking_events = [e for e in events if e.kind == "thinking"]
        assert len(thinking_events) == 2  # Stopped at max_steps


class TestRunArtifacts:
    @pytest.mark.asyncio
    async def test_tool_artifacts_emitted_as_events(self):
        session = Session(tables={"sales": pd.DataFrame({
            "category": ["A", "B", "A"],
            "revenue": [100, 200, 300],
        })})
        fake_llm = make_fake_llm([
            CodeStep(
                plan="Group and answer",
                code='grouped = group_by(sales, "category", "revenue", "sum")\nfinal_answer("done")',
            ),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        artifact_events = [e for e in events if e.kind == "artifact"]
        assert len(artifact_events) >= 1
        assert artifact_events[0].data["kind"] == "table"


class TestRunHistory:
    @pytest.mark.asyncio
    async def test_history_accumulates(self):
        session = Session(tables={"x": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('done')"),
        ])

        _ = [e async for e in run(session, "What is x?", llm=fake_llm)]

        assert len(session.history) >= 2  # At least user message + assistant
        assert session.history[0]["role"] == "user"
        assert "What is x?" in session.history[0]["content"]
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.agent'`

- [ ] **Step 3: Implement `agent/agent.py`**

```python
"""The agent loop: LLM → code → sandbox → events."""
from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable, Awaitable
from typing import Any

import numpy as np
import pandas as pd
from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.events import Event, FinalAnswer
from agent.prompts import build_prompt
from agent.sandbox import execute, SandboxResult
from agent.session import Session
from agent.tools import Tools


class CodeStep(BaseModel):
    """Structured output from the LLM: thinking + code."""

    plan: str
    code: str


async def _call_llm(
    messages: list[dict], *, model: str, temperature: float
) -> CodeStep:
    """Call OpenAI with structured output to get a CodeStep."""
    client = AsyncOpenAI()
    response = await client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=CodeStep,
        temperature=temperature,
    )
    return response.choices[0].message.parsed


def _build_env(tools: Tools, session: Session) -> dict[str, Any]:
    """Build the sandbox namespace from tools and session."""
    env: dict[str, Any] = {}

    # DataFrames by name (copies so sandbox code can't mutate originals)
    for name, df in session.tables.items():
        env[name] = df.copy()

    # Tool functions (public methods)
    for attr_name in dir(tools):
        if not attr_name.startswith("_") and callable(getattr(tools, attr_name)):
            env[attr_name] = getattr(tools, attr_name)

    # Safe libraries
    env["pd"] = pd
    env["np"] = np

    return env


async def run(
    session: Session,
    message: str,
    *,
    llm: Callable[..., Awaitable[CodeStep]] | None = None,
) -> AsyncIterator[Event]:
    """Run the agent loop, yielding events.

    Args:
        session: The current session state.
        message: The user's question.
        llm: Optional LLM callable for testing. Defaults to OpenAI.

    Yields:
        Event objects: thinking, code, artifact, result, answer, error.
    """
    if llm is None:
        async def llm(messages, **kwargs):
            return await _call_llm(
                messages,
                model=session.config.model,
                temperature=session.config.temperature,
            )

    # Collect emitted events (artifacts emitted by tools)
    emitted: list[Event] = []

    def emit(event: Event) -> None:
        emitted.append(event)

    tools = Tools(session, emit=emit)
    system_prompt = build_prompt(session.tables, tools)
    env = _build_env(tools, session)

    # Add user message to history
    session.history.append({"role": "user", "content": message})

    messages = [
        {"role": "system", "content": system_prompt},
        *session.history,
    ]

    for step_num in range(session.config.max_steps):
        # Get code step from LLM
        code_step = await llm(messages)

        # Yield thinking and code events
        yield Event("thinking", {"text": code_step.plan})
        yield Event("code", {"text": code_step.code})

        # Execute in sandbox
        emitted.clear()
        try:
            result = execute(code_step.code, env)
        except FinalAnswer as fa:
            # Yield any artifacts that were emitted before final_answer
            for event in emitted:
                yield event
            yield Event("answer", {"text": fa.answer})
            session.history.append({
                "role": "assistant",
                "content": fa.answer,
            })
            return

        # Yield any artifacts emitted by tools
        for event in emitted:
            yield event

        if result.is_error:
            yield Event("error", {"text": result.output})
            # Feed error back to LLM
            messages.append({
                "role": "assistant",
                "content": f"Plan: {code_step.plan}\nCode: {code_step.code}",
            })
            messages.append({
                "role": "user",
                "content": f"Error: {result.output}\n\nPlease fix the issue and try again.",
            })
        else:
            yield Event("result", {"text": result.output})
            messages.append({
                "role": "assistant",
                "content": f"Plan: {code_step.plan}\nCode: {code_step.code}\nResult: {result.output}",
            })

    # If we exit the loop without final_answer, record in history
    session.history.append({
        "role": "assistant",
        "content": "Reached maximum steps without a final answer.",
    })
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_agent.py -v`
Expected: All tests PASS.

Note: The sandbox returns a `SandboxResult` with `is_error` flag, so error
detection is reliable (no string matching). Errors get fed back to the LLM
for correction.

- [ ] **Step 5: Refactor if needed**

Review the `run()` function. If it's getting long, extract helpers like
`_handle_execution_result()`. Keep the main loop readable.

**CHECKPOINT: agent.py complete.**

---

### Task 13: `agent/__init__.py`

**Files:**
- Modify: `agent/__init__.py`

- [ ] **Step 1: Write the public API**

```python
"""Analytics agent — coding agent that writes Python to analyze data."""
from agent.agent import run, CodeStep
from agent.events import Event, FinalAnswer
from agent.loaders import load_file
from agent.sandbox import SandboxResult
from agent.session import AgentConfig, Artifact, Session

__all__ = [
    "run",
    "CodeStep",
    "Event",
    "FinalAnswer",
    "load_file",
    "SandboxResult",
    "AgentConfig",
    "Artifact",
    "Session",
]
```

- [ ] **Step 2: Verify imports work**

Run: `uv run python -c "from agent import run, Session, Event, load_file; print('OK')"`
Expected: `OK`

**CHECKPOINT: Phase 3 done — agent library complete.**

---

## Phase 4: API

### Task 14: `api/datasets.py`

**Files:**
- Create: `tests/test_api.py` (start with dataset tests)
- Create: `api/datasets.py`

- [ ] **Step 1: Write failing tests**

`tests/test_api.py`:
```python
from pathlib import Path

import pytest

from api.datasets import SAMPLE_DATASETS, get_dataset_paths


class TestSampleDatasets:
    def test_catalog_not_empty(self):
        assert len(SAMPLE_DATASETS) > 0

    def test_each_dataset_has_required_fields(self):
        for ds in SAMPLE_DATASETS:
            assert ds.id
            assert ds.name
            assert ds.description
            assert ds.icon
            assert len(ds.files) > 0


class TestGetDatasetPaths:
    def test_returns_paths_for_known_dataset(self):
        paths = get_dataset_paths("ecommerce")

        assert len(paths) > 0
        assert all(isinstance(p, str) for p in paths)

    def test_paths_point_to_existing_files(self):
        paths = get_dataset_paths("ecommerce")

        for p in paths:
            assert Path(p).exists(), f"File not found: {p}"

    def test_unknown_dataset_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset: 'fake'"):
            get_dataset_paths("fake")
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_api.py::TestSampleDatasets tests/test_api.py::TestGetDatasetPaths -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.datasets'`

- [ ] **Step 3: Implement `api/datasets.py`**

```python
"""Sample dataset catalog."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SampleDataset:
    id: str
    name: str
    description: str
    icon: str
    files: list[str] = field(default_factory=list)


SAMPLE_DATASETS: list[SampleDataset] = [
    SampleDataset(
        id="ecommerce",
        name="E-Commerce Sales",
        description="8K customers, 30K orders across 500 products with returns",
        icon="shopping-cart",
        files=["customers.csv", "orders.csv", "order_items.csv", "products.csv", "returns.csv"],
    ),
    SampleDataset(
        id="superstore",
        name="Superstore Sales",
        description="10K orders with shipping, profit margins, and regional performance",
        icon="store",
        files=["orders.csv", "returns.csv"],
    ),
    SampleDataset(
        id="world_indicators",
        name="World Development Indicators",
        description="142 countries with GDP, life expectancy, and population from 1952 to 2007",
        icon="globe",
        files=["gapminder.csv"],
    ),
]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_dataset_paths(dataset_id: str) -> list[str]:
    """Resolve a sample dataset ID to absolute file paths.

    Raises ValueError for unknown dataset IDs.
    """
    for ds in SAMPLE_DATASETS:
        if ds.id == dataset_id:
            base = DATA_DIR / dataset_id
            return [str(base / f) for f in ds.files]
    raise ValueError(f"Unknown dataset: '{dataset_id}'")
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: All tests PASS.

**CHECKPOINT: datasets.py complete.**

---

### Task 15: `api/sessions.py`

**Files:**
- Modify: `tests/test_api.py` (add test class)
- Create: `api/sessions.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_api.py`:

```python
from agent.session import AgentConfig, Session
from api.sessions import SessionManager


class TestSessionManager:
    def test_create_returns_id(self):
        manager = SessionManager()

        session_id = manager.create()

        assert isinstance(session_id, str)
        assert len(session_id) == 12

    def test_get_returns_session(self):
        manager = SessionManager()
        session_id = manager.create()

        session = manager.get(session_id)

        assert isinstance(session, Session)

    def test_get_unknown_id_raises(self):
        manager = SessionManager()

        with pytest.raises(KeyError):
            manager.get("nonexistent")

    def test_create_with_config(self):
        manager = SessionManager()
        config = AgentConfig(model="gpt-4o-mini")

        session_id = manager.create(config)
        session = manager.get(session_id)

        assert session.config.model == "gpt-4o-mini"

    def test_destroy_removes_session(self):
        manager = SessionManager()
        session_id = manager.create()

        manager.destroy(session_id)

        with pytest.raises(KeyError):
            manager.get(session_id)
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_api.py::TestSessionManager -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.sessions'`

- [ ] **Step 3: Implement `api/sessions.py`**

```python
"""In-memory session manager."""
from __future__ import annotations

import uuid

from agent.session import AgentConfig, Session


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, config: AgentConfig | None = None) -> str:
        """Create a new session and return its ID."""
        session_id = uuid.uuid4().hex[:12]
        session = Session(config=config or AgentConfig())
        self._sessions[session_id] = session
        return session_id

    def get(self, session_id: str) -> Session:
        """Retrieve a session by ID. Raises KeyError if not found."""
        if session_id not in self._sessions:
            raise KeyError(session_id)
        return self._sessions[session_id]

    def destroy(self, session_id: str) -> None:
        """Remove a session."""
        self._sessions.pop(session_id, None)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: All tests PASS.

**CHECKPOINT: sessions.py complete.**

---

### Task 16: `api/main.py`

**Files:**
- Modify: `tests/test_api.py` (add route tests using httpx + TestClient)
- Create: `api/main.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_api.py`:

```python
import json

from fastapi.testclient import TestClient

from api.main import app


class TestHealthRoute:
    def test_health(self):
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDatasetsRoute:
    def test_list_datasets(self):
        client = TestClient(app)

        response = client.get("/api/datasets")

        assert response.status_code == 200
        datasets = response.json()
        assert len(datasets) > 0
        assert all("id" in d for d in datasets)
        assert all("name" in d for d in datasets)


class TestSessionRoutes:
    def test_create_session(self):
        client = TestClient(app)

        response = client.post("/api/sessions")

        assert response.status_code == 200
        assert "session_id" in response.json()

    def test_load_sample_dataset(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]

        response = client.post(
            f"/api/sessions/{session_id}/load-sample/ecommerce"
        )

        assert response.status_code == 200
        tables = response.json()["tables"]
        assert len(tables) > 0
        assert all("name" in t for t in tables)
        assert all("rows" in t for t in tables)

    def test_get_tables(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]
        client.post(f"/api/sessions/{session_id}/load-sample/ecommerce")

        response = client.get(f"/api/sessions/{session_id}/tables")

        assert response.status_code == 200
        tables = response.json()["tables"]
        assert len(tables) > 0
        assert "columns" in tables[0]

    def test_unknown_session_returns_404(self):
        client = TestClient(app)

        response = client.get("/api/sessions/nonexistent/tables")

        assert response.status_code == 404
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_api.py::TestHealthRoute tests/test_api.py::TestDatasetsRoute tests/test_api.py::TestSessionRoutes -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.main'`

- [ ] **Step 3: Implement `api/main.py`**

```python
"""FastAPI backend — thin HTTP layer over the agent."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent import run, load_file, Session, AgentConfig
from api.datasets import SAMPLE_DATASETS, get_dataset_paths
from api.sessions import SessionManager

app = FastAPI(title="DataAgent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SessionManager()


# -- Request schemas ---------------------------------------------------

class CreateSessionRequest(BaseModel):
    model: str | None = None
    temperature: float | None = None


class AskRequest(BaseModel):
    message: str


# -- Helpers -----------------------------------------------------------

def _get_session(session_id: str) -> Session:
    try:
        return manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


def _table_summary(name: str, df) -> dict:
    return {"name": name, "rows": len(df), "columns": len(df.columns)}


def _table_metadata(name: str, df) -> dict:
    return {
        "name": name,
        "rows": len(df),
        "columns": [
            {"name": col, "dtype": str(df[col].dtype)} for col in df.columns
        ],
    }


# -- Routes ------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/datasets")
def list_datasets():
    return [
        {
            "id": ds.id,
            "name": ds.name,
            "description": ds.description,
            "icon": ds.icon,
            "tables": len(ds.files),
            "preview": ", ".join(Path(f).stem for f in ds.files),
        }
        for ds in SAMPLE_DATASETS
    ]


@app.post("/api/sessions")
def create_session(body: CreateSessionRequest | None = None):
    config = None
    if body and (body.model or body.temperature is not None):
        kwargs: dict[str, Any] = {}
        if body.model:
            kwargs["model"] = body.model
        if body.temperature is not None:
            kwargs["temperature"] = body.temperature
        config = AgentConfig(**kwargs)
    session_id = manager.create(config)
    return {"session_id": session_id}


@app.post("/api/sessions/{session_id}/upload")
async def upload_files(session_id: str, files: list[UploadFile] = File(...)):
    session = _get_session(session_id)
    tmp_dir = Path(tempfile.mkdtemp())
    tables = []
    for f in files:
        dest = tmp_dir / (f.filename or "upload.csv")
        dest.write_bytes(await f.read())
        name, df = load_file(dest)
        session.tables[name] = df
        tables.append(_table_summary(name, df))
    return {"tables": tables}


@app.post("/api/sessions/{session_id}/load-sample/{dataset_id}")
def load_sample_dataset(session_id: str, dataset_id: str):
    session = _get_session(session_id)
    try:
        paths = get_dataset_paths(dataset_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset_id}")
    tables = []
    for path in paths:
        name, df = load_file(path)
        session.tables[name] = df
        tables.append(_table_summary(name, df))
    return {"tables": tables}


@app.get("/api/sessions/{session_id}/tables")
def get_tables(session_id: str):
    session = _get_session(session_id)
    return {
        "tables": [
            _table_metadata(name, df)
            for name, df in session.tables.items()
        ]
    }


@app.post("/api/sessions/{session_id}/ask")
async def ask(session_id: str, body: AskRequest):
    session = _get_session(session_id)

    async def stream():
        async for event in run(session, body.message):
            yield {
                "event": event.kind,
                "data": json.dumps(event.data),
            }

    return EventSourceResponse(stream())


@app.get("/api/sessions/{session_id}/artifacts/{artifact_id}")
def get_artifact(session_id: str, artifact_id: str):
    session = _get_session(session_id)
    for artifact in session.artifacts:
        if artifact.id == artifact_id:
            return {
                "id": artifact.id,
                "kind": artifact.kind,
                "title": artifact.title,
                "data": artifact.data,
            }
    raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: All tests across all files PASS.

**CHECKPOINT: Core API routes complete.**

---

### Task 17: `POST /api/sessions/{id}/suggestions` endpoint

The suggestions endpoint generates LLM-based question suggestions from
loaded table schemas. It's a lightweight single LLM call, not a full agent
run.

**Files:**
- Modify: `tests/test_api.py` (add test class)
- Modify: `api/main.py` (add route)

- [ ] **Step 1: Write failing test**

Add to `tests/test_api.py`:

```python
class TestSuggestionsRoute:
    def test_returns_suggestions_list(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]
        client.post(f"/api/sessions/{session_id}/load-sample/world_indicators")

        response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_empty_tables_returns_empty(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]

        response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        assert response.json()["suggestions"] == []
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `uv run pytest tests/test_api.py::TestSuggestionsRoute -v`
Expected: FAIL — 404 (route doesn't exist)

- [ ] **Step 3: Implement suggestions route in `api/main.py`**

Add a `_generate_suggestions` helper and the route:

```python
from openai import AsyncOpenAI as _AsyncOpenAI

async def _generate_suggestions(session: Session) -> list[str]:
    """Generate question suggestions from loaded table schemas."""
    if not session.tables:
        return []

    from agent.prompts import describe_tables

    table_desc = describe_tables(session.tables)
    client = _AsyncOpenAI()

    response = await client.chat.completions.create(
        model=session.config.model,
        temperature=0.7,
        messages=[
            {
                "role": "system",
                "content": (
                    "Given these data tables, suggest 4 interesting analytical "
                    "questions a user might ask. Return only the questions, "
                    "one per line. No numbering, no bullets."
                ),
            },
            {"role": "user", "content": table_desc},
        ],
    )
    text = response.choices[0].message.content or ""
    return [line.strip() for line in text.strip().splitlines() if line.strip()]


@app.post("/api/sessions/{session_id}/suggestions")
async def get_suggestions(session_id: str):
    session = _get_session(session_id)
    try:
        suggestions = await _generate_suggestions(session)
    except Exception:
        suggestions = []
    return {"suggestions": suggestions}
```

Note: The `test_returns_suggestions_list` test requires a real LLM call.
For CI, either mock the OpenAI client or mark the test as integration-only.
The `test_empty_tables_returns_empty` test works without LLM.

- [ ] **Step 4: Run tests — verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: All tests PASS (the suggestions test with real LLM may need
`OPENAI_API_KEY` set or be skipped in CI).

**CHECKPOINT: Phase 4 done — API complete with all 8 routes.**

---

## Phase 5: Update Project Files

### Task 18: Update CLAUDE.md and README.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Rewrite `CLAUDE.md` to reflect new architecture**

Update commands, architecture section, key conventions, and file paths to
match the new `agent/` + `api/` structure. Remove all references to
`src/analytics_agent/`, `apps/web/backend/`, tool registry, etc.

- [ ] **Step 2: Update `README.md`**

Brief project description, setup commands, and how to run.

- [ ] **Step 3: Run full test suite one final time**

Run: `uv run pytest -v`
Expected: All tests PASS.

**CHECKPOINT: Project complete. All backend code tested and working.**

---

## Summary

| Phase | Tasks | What's built |
|---|---|---|
| 0 | 1 | Archive + clean project structure |
| 1 | 2-6 | Foundation: events, session, loaders, sandbox |
| 2 | 7-10 | Tools: filter, group_by, sort, join, display, final_answer |
| 3 | 11-13 | Prompts, agent loop, public API |
| 4 | 14-17 | FastAPI routes, session manager, datasets, suggestions |
| 5 | 18 | CLAUDE.md + README.md updates |

18 tasks. ~450 LOC agent + ~180 LOC API + ~550 LOC tests.

The UI redesign (`docs/UI_DESIGN.md`) is a separate implementation plan.
