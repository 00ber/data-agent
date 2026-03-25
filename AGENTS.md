# Repository Guidelines

Read `ENGINEERING.md` first; it defines the engineering ethos for all contributions.

## Project Structure & Module Organization
`src/analytics_agent/` is the main Python package. `agent/` handles session flow and prompts, `store/` manages tables and relationships, `tools/` contains analysis helpers, and `reports/` generates memo outputs. `apps/web/backend/` is the FastAPI layer. `apps/web/frontend/src/` is the Vite React UI, organized into `components/`, `stores/`, `lib/`, and `types/`. Sample datasets live in `data/`; tests and fixtures live under `tests/`, mirrored by folders such as `tests/agent/` and `tests/tools/`.

## Build, Test, and Development Commands
`uv sync --extra dev --extra web` installs Python dependencies, pytest, and FastAPI extras.
`uv run pytest` runs the backend test suite.
`uv run uvicorn apps.web.backend.main:app --reload --port 8001` starts the API.
`cd apps/web/frontend && npm install` installs frontend packages.
`cd apps/web/frontend && npm run dev` starts Vite on `http://localhost:5173` and proxies `/api` to port `8001`.
`cd apps/web/frontend && npm run build` runs TypeScript build checks and creates production assets.
`cd apps/web/frontend && npm run lint` runs ESLint over the React/TypeScript codebase.

## Coding Style & Naming Conventions
Use 4-space indentation and type hints in Python. Keep Python modules in `snake_case.py`; use `PascalCase` for classes and Pydantic models. In the frontend, keep React components in `PascalCase.tsx`, and use lower-case or kebab-case names for stores and utilities such as `session-store.ts` and `api-client.ts`. Prefer the existing `@/` import alias. Match the surrounding quote and semicolon style instead of reformatting unrelated files.

## Testing Guidelines
Pytest loads tests from `tests/` with `src/` on the Python path. Name files `test_*.py` and place them next to the area they cover, for example `tests/store/test_loaders.py`. Reuse fixtures from `tests/conftest.py` and CSV samples in `tests/fixtures/` when possible. Add regression coverage for new tools, store behavior, and session flows before merging.

## Commit & Pull Request Guidelines
Git history is minimal (`Initial commit`), so use short imperative commit subjects and add a scope when helpful, for example `store: tighten relationship detection`. Keep the first line under 72 characters. Pull requests should include a summary, linked issues, the commands you ran (`uv run pytest`, `npm run lint`), and screenshots for visible frontend changes.

## Security & Configuration
The backend loads environment variables through `python-dotenv`; keep API keys in a local `.env` file and never commit secrets. Avoid committing generated caches or dependency folders such as `__pycache__/` and `node_modules/`. Treat sample datasets in `data/` as demo content only; do not add sensitive real-world data.
