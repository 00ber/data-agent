# Agent Redesign Plan

## Context

The current agent (`src/analytics_agent/`, ~1,600 LOC across 14 files) is a
plan-then-execute tool-calling agent built on OpenAI function calling. It
works, but the architecture is bloated: a god-class orchestrator, a
ceremony-heavy tool registry, 20+ Pydantic models in one file, dead code,
swallowed exceptions, and mixed responsibilities throughout.

This plan replaces it entirely with a **coding agent** — the LLM writes
Python code that calls validated tool functions in a sandbox. The design is
informed by:

- The Build Fellowship workshop progression (WS4 tool-calling → WS5 coding
  agent → WS6 memory)
- HuggingFace SmolAgents (final_answer as tool, minimal abstractions)
- First-principles analysis of what an analytics agent actually needs

## Design Decisions (settled)

1. **Coding agent, not tool-calling.** The LLM writes Python. Tools are
   callable functions in a sandbox, not JSON-dispatched endpoints. Workshop 5
   proved tool-calling hits a wall for derived metrics (ratios, z-scores,
   correlations). Code is composable; tool DSLs are not.

2. **Tools are artifact producers.** Every tool produces a visible artifact —
   data tools produce table artifacts, display tools produce chart/stat
   artifacts. The user sees every intermediate step. This makes artifacts
   first-class: they're not just final outputs, they're the audit trail.

3. **final_answer is a tool.** Calling `final_answer(text)` raises
   `FinalAnswer` exception, terminating the agent loop. No `done` flag on
   the structured output. Termination is in-band.

4. **Structured output for the LLM response.** `CodeStep {plan, code}` —
   two fields. The plan is the agent's thinking (visible in UI). The code
   executes in the sandbox. Structured output guarantees parseability.

5. **Tools are a class, introspected by the agent.** Public methods = tools.
   Private methods = helpers. The class provides state binding (session +
   event emitter). The agent inspects signatures + docstrings for prompt
   generation and sandbox construction. No `env_dict()` or `prompt_section()`
   on the class — those are agent concerns.

6. **DataFrames directly in sandbox scope.** The LLM writes `sales.groupby(...)`
   not `get_table("sales").groupby(...)`. Tables are variables in the namespace.

7. **Tools provide determinism.** `filter()`, `group_by()`, `sort()`, `join()`
   use known-correct pandas implementations. The LLM doesn't need to know the
   exact pandas API for common operations. For uncommon operations, the LLM
   writes raw pandas on tool-returned DataFrames.

## Architecture

### Abstractions (4)

```
Session     — state: tables, artifacts, history, config
Tools       — class of analytics functions, bound to session
Sandbox     — execute(code, env) → result | FinalAnswer | error
Artifact    — displayable output: table, chart, stat
Event       — what flows to the UI: thinking, code, artifact, result, answer, error
```

Event is a data carrier, not a behavioral abstraction.

### Component Relationships

```
         Session
        (state)
           │
     ┌─────┴──────┐
     │             │
     ▼             ▼
   Tools        prompts.py
  (class)       (functions)
     │             │
     │    builds prompt from:
     │    - session.tables (schemas)
     │    - Tools (inspect signatures)
     │    - session.history (window)
     │             │
     └──────┬──────┘
            ▼
        agent.py
         run()
      async generator
        → Event
            │
            ▼
        sandbox.py
        execute()
```

### The Agent Loop

```
User message
     │
     ▼
Build prompt (system + table schemas + tool docs + history)
     │
     ▼
┌──► LLM call → CodeStep {plan, code}
│        │
│        ├── yield Event("thinking", plan)
│        ├── yield Event("code", code)
│        │
│        ▼
│    Sandbox.execute(code, env)
│        │
│    ┌───┼──────────┐
│    │   │          │
│  result FinalAnswer error
│    │   │          │
│    │   ├ yield    │
│    │   │ artifact │
│    │   │ events   │
│    │   ├ yield    │
│    │   │ answer   │
│    │   │ RETURN   │
│    │   │          │
│    ▼   │          ▼
│  yield │      yield error
│  artifact      add to history
│  events            │
│  yield result      │
│  add to history    │
│    │               │
└────┴───────────────┘
     (up to max_steps)
```

### Tool Categories

```
DATA (return DataFrame, emit table artifact):
  filter(table, column, op, value)    — validated filter
  group_by(table, by, column, agg)    — validated aggregation
  sort(table, by, ascending)          — validated sort
  join(left, right, on)               — validated join

DISPLAY (emit rich artifact):
  show_chart(data, kind, title)       — chart artifact (bar/line/scatter/pie/histogram)
  show_table(data, title)             — formatted table artifact
  show_stat(label, value)             — stat card artifact

CONTROL:
  final_answer(answer)                — terminates loop via FinalAnswer exception
```

Data tools accept `str | DataFrame` — the LLM can pass a table name or pipe
the result of a previous tool. `_resolve()` handles the dispatch.

### Sandbox Namespace

```python
env = {
    # Source DataFrames (by name)
    "sales": df_sales,
    "customers": df_customers,

    # Tool functions (bound methods from Tools instance)
    "filter": tools.filter,
    "group_by": tools.group_by,
    "sort": tools.sort,
    "join": tools.join,
    "show_chart": tools.show_chart,
    "show_table": tools.show_table,
    "show_stat": tools.show_stat,
    "final_answer": tools.final_answer,

    # Safe libraries
    "pd": pandas,
    "np": numpy,
}
```

### Event Stream (what the frontend receives)

```
Event("thinking",  {text: "Filter Q4 sales, group by category..."})
Event("code",      {text: "filtered = filter(sales, 'quarter', '==', 'Q4')..."})
Event("artifact",  {id, kind: "table", title: "Filtered: quarter==Q4", data: ...})
Event("artifact",  {id, kind: "table", title: "sum(revenue) by category", data: ...})
Event("artifact",  {id, kind: "chart", title: "Q4 Revenue", data: ...})
Event("answer",    {text: "Technology leads Q4 revenue at $2.3M..."})
```

## File Structure

```
agent/
├── __init__.py       # Public API: run(), Session, Event, load_file
├── agent.py          # run() → async generator of Events, CodeStep
├── events.py         # Event dataclass
├── loaders.py        # load_file() for CSV/XLSX/Parquet
├── prompts.py        # build_prompt(), describe_tool()
├── sandbox.py        # execute(code, env), FinalAnswer, RestrictedPython
├── session.py        # Session, Artifact, AgentConfig
└── tools.py          # Tools class — all tool methods
```

~450 LOC total, 8 files, each fits on one screen.

See `docs/PROJECT_STRUCTURE.md` for full project layout.

### What gets deleted

Everything in the current `src/analytics_agent/`:

- `agent/session.py` (412-line god class) → replaced by `agent.py` (~80 LOC)
- `agent/executor.py` → replaced by `sandbox.py` (~50 LOC)
- `agent/memory.py` (mostly dead code) → history is `list[dict]` in Session
- `agent/prompts.py` (4 prompt builders) → replaced by `prompts.py` (~50 LOC)
- `tools/registry.py` (ToolRegistry + ToolSpec) → deleted, no registry needed
- `tools/introspection.py` → tools on the Tools class
- `tools/analysis.py` → tools on the Tools class
- `tools/visualization.py` → `show_chart` on the Tools class
- `tools/codegen.py` → the entire agent IS the code executor
- `store/analytics_store.py` → Session.tables + Session.artifacts
- `store/loaders.py` → `loaders.py` (kept, simplified)
- `store/relationships.py` → useful heuristic, fold into prompts or Tools
- `models.py` (20+ models) → types live next to what uses them
- `api.py` (thin wrapper) → deleted
- `config.py` → AgentConfig in session.py
- `datasets.py` → move to api (it's a UI/routing concern)
- `reports/memo.py` → LLM handles synthesis in final_answer

## Implementation Phases

### Phase 1: Foundation (Session + Events + Sandbox)

Build the bottom layers that everything else depends on.

**Files**: `agent/events.py`, `agent/session.py`, `agent/sandbox.py`, `agent/loaders.py`

1. `events.py` — Event dataclass, FinalAnswer exception
2. `session.py` — Session, Artifact, AgentConfig. All dataclasses, no behavior.
3. `sandbox.py` — `execute(code: str, env: dict) → str`. RestrictedPython
   with AST validation, safe builtins, guarded attribute access. Catches
   FinalAnswer and re-raises. Returns captured stdout + last expression repr.
4. `loaders.py` — `load_file(path) → tuple[str, DataFrame]`. CSV/XLSX/Parquet.
   Infer table name from filename.

**Tests**: Sandbox is the critical path. Test: safe execution, forbidden
imports, forbidden attribute access, FinalAnswer propagation, error messages
include what went wrong.

### Phase 2: Tools

Build the Tools class with all analytics functions.

**Files**: `agent/tools.py`

1. Tools class with `__init__(session, emit)`.
2. Data tools: `filter`, `group_by`, `sort`, `join`. Each validates inputs,
   uses correct pandas API, emits table artifact, returns DataFrame.
3. Display tools: `show_chart`, `show_table`, `show_stat`. Each creates
   artifact with appropriate data format, emits artifact event.
4. Control: `final_answer` raises FinalAnswer exception.
5. Private: `_resolve(table)` accepts str or DataFrame. `_emit_artifact()`
   creates Artifact, appends to session, calls emit callback.

**Tests**: Each tool in isolation. Verify: correct pandas operation, artifact
emitted, DataFrame returned, input validation (bad column name → clear error),
str and DataFrame both accepted.

### Phase 3: Prompts + Agent Loop

Wire everything together.

**Files**: `agent/prompts.py`, `agent/agent.py`, `agent/__init__.py`

1. `prompts.py`:
   - `describe_tool(method) → str` — uses `inspect.signature` + `__doc__`
   - `describe_tables(tables) → str` — table name, shape, columns, dtypes
   - `build_prompt(tables, tool_methods) → str` — system instructions +
     table descriptions + tool signatures

2. `agent.py`:
   - `CodeStep(BaseModel)` — `{plan: str, code: str}`
   - `run(session, message) → AsyncIterator[Event]` — the loop:
     - Create Tools instance
     - Introspect for prompt + sandbox env
     - Loop: LLM call → yield thinking/code → execute → yield results/errors
     - Terminate on FinalAnswer

3. `__init__.py` — public API: `run`, `Session`, `Event`, `load_file`

**Tests**: Agent loop with mock LLM. Verify: events emitted in correct order,
FinalAnswer terminates loop, errors feed back to LLM, max_steps respected,
history accumulates correctly.

### Phase 4: Integration + API

Connect to the FastAPI backend.

1. Update `api/main.py` to use new `run()` API
2. SSE endpoint wraps `async for event in run(session, message)`
3. Session management (create, store, retrieve)
4. File upload → `load_file()` → session.tables
5. Update frontend event handling to match new Event types

**Tests**: End-to-end with real LLM (integration test). Upload file, ask
question, verify artifact events + final answer.

## Key Design Rules

- **Every tool produces an artifact.** If a tool runs, the user sees it.
- **Tools validate inputs.** Bad column name → clear error message, not a
  pandas traceback.
- **The agent introspects Tools.** The Tools class doesn't know about prompts
  or sandboxes. Python conventions (`_private`, `inspect`, `__doc__`) are
  the metadata system.
- **History is `list[dict]`.** OpenAI message format. No wrapper class. Window
  in `build_prompt()` by slicing.
- **Structured output `{plan, code}`.** Two fields. Always. The plan is the
  thinking, the code is the action, `final_answer()` is the termination.

## What This Plan Does NOT Cover

- **Frontend redesign** — separate effort, will consume the new Event stream
- **Long-term memory / summarization** — add after core works
- **Multi-file upload UX** — the backend supports it, but the upload flow is
  a frontend concern
- **Authentication / multi-user** — production concern, not architectural
