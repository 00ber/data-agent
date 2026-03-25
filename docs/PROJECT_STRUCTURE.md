# Project Structure Plan

## Proposed Structure

```
data-agent/
│
├── agent/                         # Core library
│   ├── __init__.py                # Public API: run(), Session, Event, load_file
│   ├── agent.py                   # run() async generator, CodeStep model
│   ├── events.py                  # Event, FinalAnswer
│   ├── loaders.py                 # load_file() → (name, DataFrame)
│   ├── prompts.py                 # build_prompt(), describe_tool()
│   ├── sandbox.py                 # execute(code, env)
│   ├── session.py                 # Session, Artifact, AgentConfig
│   └── tools.py                   # Tools class
│
├── api/                           # FastAPI backend
│   ├── main.py                    # App, routes, SSE streaming
│   └── sessions.py                # In-memory session manager
│
├── ui/                            # React frontend
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── tests/                         # Python tests (flat)
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── orders.csv
│   │   ├── customers.csv
│   │   └── products.csv
│   ├── test_agent.py
│   ├── test_sandbox.py
│   ├── test_tools.py
│   ├── test_prompts.py
│   ├── test_loaders.py
│   └── test_integration.py
│
├── data/                          # Sample datasets
│   ├── ecommerce/
│   ├── superstore/
│   └── world_indicators/
│
├── docs/                          # Design documents
│   ├── AGENT_REDESIGN.md
│   └── PROJECT_STRUCTURE.md
│
├── pyproject.toml
├── ENGINEERING.md
├── CLAUDE.md
├── README.md
├── .env.sample
└── .gitignore
```

## What Changes

### Directory moves

| Before | After |
|--------|-------|
| `src/analytics_agent/` | `agent/` |
| `apps/web/backend/` | `api/` |
| `apps/web/frontend/` | `ui/` |
| `apps/web/frontend/dist/` | deleted (gitignored) |
| `workshop_*.ipynb` | deleted (not part of this repo) |
| `data/generate_dataset.py` | deleted (using real datasets) |
| `apps/__init__.py`, `apps/web/__init__.py` | deleted |

### Import path

```python
# Before
from analytics_agent import AgentSession, AgentConfig
from apps.web.backend.sessions import SessionManager

# After
from agent import run, Session, Event
from api.sessions import SessionManager
```

## pyproject.toml

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
]

[project.optional-dependencies]
api = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sse-starlette>=2.0",
    "python-multipart>=0.0.18",
]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["agent"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

## Commands

```bash
# Setup
uv sync --all-extras
cp .env.sample .env              # Add OPENAI_API_KEY
cd ui && npm install

# Backend (port 8001)
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

# Frontend (port 5173)
cd ui && npm run dev

# Tests
pytest                            # All
pytest tests/test_sandbox.py      # Single file
pytest tests/test_tools.py::test_filter  # Single test
```

## Migration Steps

One commit before the agent rewrite:

1. Move frontend: `mv apps/web/frontend ui/` then `rm -rf ui/dist/`
2. Move backend: `mkdir api && mv apps/web/backend/main.py api/ && mv apps/web/backend/sessions.py api/`
3. Delete apps tree: `rm -rf apps/`
4. Delete workshops: `rm workshop_*.ipynb`
5. Delete dataset script: `rm data/generate_dataset.py`
6. Update `api/main.py` imports (drop `apps.web.backend` prefix)
7. Update `pyproject.toml`
8. Update `.gitignore` (add `ui/dist/`, `ui/node_modules/`)
9. Update `CLAUDE.md`
10. Verify: `uv sync && pytest && uvicorn api.main:app`

The `src/analytics_agent/` → `agent/` and `tests/` restructuring happens
as part of the agent rewrite, not this step.
