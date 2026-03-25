# Data Agent

AI-powered data analysis tool. A coding agent where the LLM writes Python code that runs in a RestrictedPython sandbox with validated tool functions. Every tool produces a visible artifact (tables, charts, stat cards). Events stream via SSE.

## Setup

```bash
uv sync --all-extras
cp .env.sample .env   # Add OPENAI_API_KEY
```

## Run

```bash
# Tests
uv run pytest

# Backend
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/datasets` | List sample datasets |
| POST | `/api/sessions` | Create session |
| POST | `/api/sessions/{id}/upload` | Upload CSV/XLSX/Parquet files |
| POST | `/api/sessions/{id}/load-sample/{dataset}` | Load sample dataset |
| GET | `/api/sessions/{id}/tables` | List loaded tables with schemas |
| POST | `/api/sessions/{id}/ask` | Ask a question (SSE stream) |
| POST | `/api/sessions/{id}/suggestions` | Get AI-generated question suggestions |
| GET | `/api/sessions/{id}/artifacts/{aid}` | Fetch a specific artifact |

## Architecture

```
agent/          Core library (events, session, sandbox, tools, prompts, agent loop)
api/            FastAPI backend (routes, session manager, dataset catalog)
data/           Sample datasets (ecommerce, superstore, world_indicators)
tests/          Test suite (118+ tests)
```

See `CLAUDE.md` for detailed architecture and conventions.
