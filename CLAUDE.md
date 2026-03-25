# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Engineering Ethos

Read and follow `ENGINEERING.md` — it governs all code in this repo. Key mandates: scope discipline (do only what's asked), screaming architecture (names reveal domain intent), boring code (obvious > clever), TDD by default (Red → Green → Refactor), fail early and loudly (no silent fallbacks), and extract abstractions only after the rule of three.

## Project Overview

Analytics Agent — an AI-powered data analysis tool. A **coding agent** where the LLM writes Python code that calls validated tool functions in a RestrictedPython sandbox. Tools are artifact producers (every tool emits a visible artifact). Events stream via SSE to the frontend.

**Status:** Active redesign. Old code archived in `archive/`. New code being built per `docs/IMPLEMENTATION_PLAN.md`.

## Design Docs

- `docs/AGENT_REDESIGN.md` — Agent architecture (coding agent, tools, sandbox, events)
- `docs/PROJECT_STRUCTURE.md` — Directory layout and migration plan
- `docs/API_DESIGN.md` — FastAPI routes and SSE streaming
- `docs/UI_DESIGN.md` — "Analysis Stream" frontend design
- `docs/IMPLEMENTATION_PLAN.md` — Step-by-step build plan with TDD

## Commands

```bash
# Setup
uv sync --all-extras
cp .env.sample .env              # Add OPENAI_API_KEY

# Tests
pytest                            # All
pytest tests/test_sandbox.py      # Single file
pytest tests/test_tools.py::TestFilter  # Single test

# Backend (after Phase 4)
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

## Architecture

```
agent/                  # Core library
├── agent.py            # run() → async generator of Events
├── events.py           # Event, FinalAnswer
├── loaders.py          # load_file() → (name, DataFrame)
├── prompts.py          # build_prompt(), describe_tool()
├── sandbox.py          # execute(code, env) → SandboxResult
├── session.py          # Session, Artifact, AgentConfig
└── tools.py            # Tools class (filter, group_by, sort, join, show_*, final_answer)

api/                    # FastAPI backend
├── main.py             # Routes + SSE streaming
├── sessions.py         # SessionManager
└── datasets.py         # Sample dataset catalog
```

### Agent Loop

```
User message → build prompt (schemas + tool docs + history)
  → LLM call → CodeStep {plan, code}
  → sandbox.execute(code, env)
  → yield events (thinking, code, artifact, result, answer, error)
  → repeat until final_answer() or max_steps
```

## Key Conventions

- **Package path**: `agent/` (root-level, `pythonpath = ["."]`)
- **Package manager**: uv for Python
- **Python >=3.12** required
- **Environment**: `OPENAI_API_KEY` is the only required env var
- **Config defaults**: `gpt-4o`, temperature 0.0
- **Sample datasets** in `data/` (ecommerce, superstore, world_indicators)
- **Old code** in `archive/` for reference (gitignored)
