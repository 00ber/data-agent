"""FastAPI backend for the API-layer session architecture."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI as _AsyncOpenAI
from pydantic import BaseModel, field_validator
from sse_starlette.sse import EventSourceResponse

from agent import OpenAILLM, load_files
from agent.validation import require_text
from api.datasets import SAMPLE_DATASETS, get_dataset_paths
from api.sessions import (
    AgentSession,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    InMemoryAgentSessionStore,
)

app = FastAPI(title="DataAgent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_store = InMemoryAgentSessionStore()


class CreateSessionRequest(BaseModel):
    """Optional LLM overrides for one new session."""

    model: str | None = None
    temperature: float | None = None

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        """Reject blank model names."""

        if value is None:
            return None
        return require_text(value, "Model")


class MessageRequest(BaseModel):
    """One user message sent to the agent."""

    message: str


def _get_session(session_id: str) -> AgentSession:
    """Return one live session or raise a 404."""

    try:
        return session_store.get(session_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        ) from exc


def _table_summary(name: str, table) -> dict[str, object]:
    """Return compact table metadata for load responses."""

    return {"name": name, "rows": len(table), "columns": len(table.columns)}


def _table_metadata(name: str, table) -> dict[str, object]:
    """Return detailed immutable table metadata for the UI."""

    return {
        "name": name,
        "rows": len(table),
        "columns": [
            {"name": column, "dtype": str(table[column].dtype)}
            for column in table.columns
        ],
    }


def _load_tables(paths: list[str]) -> dict[str, object]:
    """Load one or more files into normalized table names."""

    try:
        return load_files(paths)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _add_tables_to_session(
    session: AgentSession,
    loaded_tables: dict[str, object],
) -> list[dict[str, object]]:
    """Add loaded tables to one live session after duplicate checks."""

    existing_names = set(session.agent.environment.inputs)
    duplicate_names = sorted(existing_names & set(loaded_tables))
    if duplicate_names:
        duplicate_list = ", ".join(duplicate_names)
        raise HTTPException(
            status_code=400,
            detail=f"Input table name(s) already exists: {duplicate_list}",
        )

    table_summaries: list[dict[str, object]] = []
    for name, table in loaded_tables.items():
        session.agent.environment.add_input_table(name, table)
        table_summaries.append(_table_summary(name, table))

    return table_summaries


def _session_model(session: AgentSession) -> str:
    """Return the OpenAI model configured for one session."""

    llm = session.agent.llm
    if not isinstance(llm, OpenAILLM):
        raise TypeError("Suggestions require an OpenAILLM-backed session.")

    return llm.model


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/datasets")
def list_datasets():
    return [
        {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "icon": dataset.icon,
            "tables": len(dataset.files),
            "preview": ", ".join(Path(path).stem for path in dataset.files),
        }
        for dataset in SAMPLE_DATASETS
    ]


@app.post("/api/sessions")
def create_session(body: CreateSessionRequest | None = None):
    request = body or CreateSessionRequest()
    session_id = session_store.create(
        model=request.model or DEFAULT_MODEL,
        temperature=(
            request.temperature
            if request.temperature is not None
            else DEFAULT_TEMPERATURE
        ),
    )
    return {"session_id": session_id}


@app.post("/api/sessions/{session_id}/files")
async def upload_files(session_id: str, files: list[UploadFile] = File(...)):
    session = _get_session(session_id)
    temp_dir = Path(tempfile.mkdtemp())
    paths: list[str] = []

    for file in files:
        destination = temp_dir / (file.filename or "upload.csv")
        destination.write_bytes(await file.read())
        paths.append(str(destination))

    loaded_tables = _load_tables(paths)
    tables = _add_tables_to_session(session, loaded_tables)
    return {"tables": tables}


@app.post("/api/sessions/{session_id}/datasets/{dataset_id}")
def load_sample_dataset(session_id: str, dataset_id: str):
    session = _get_session(session_id)
    try:
        paths = get_dataset_paths(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset: {dataset_id}",
        ) from exc

    loaded_tables = _load_tables(paths)
    tables = _add_tables_to_session(session, loaded_tables)
    return {"tables": tables}


@app.get("/api/sessions/{session_id}/tables")
def get_tables(session_id: str):
    session = _get_session(session_id)
    return {
        "tables": [
            _table_metadata(name, table)
            for name, table in session.agent.environment.inputs.items()
        ]
    }


@app.post("/api/sessions/{session_id}/messages")
async def create_message(session_id: str, body: MessageRequest):
    session = _get_session(session_id)

    async def stream():
        async for event in session.agent.run(body.message):
            yield {"event": event.kind, "data": json.dumps(event.data)}

    return EventSourceResponse(stream())


async def _generate_suggestions(session: AgentSession) -> list[str]:
    """Generate question suggestions from the current input table schemas."""

    if not session.agent.environment.inputs:
        return []

    client = _AsyncOpenAI()
    response = await client.responses.create(
        model=_session_model(session),
        input=[
            {
                "role": "system",
                "content": (
                    "Given these data tables, suggest 4 interesting analytical "
                    "questions a user might ask. Return only the questions, "
                    "one per line. No numbering, no bullets."
                ),
            },
            {
                "role": "user",
                "content": session.agent.environment.describe(),
            },
        ],
    )
    text = response.output_text or ""
    return [line.strip() for line in text.strip().splitlines() if line.strip()]


@app.post("/api/sessions/{session_id}/suggestions")
async def get_suggestions(session_id: str):
    session = _get_session(session_id)
    try:
        suggestions = await _generate_suggestions(session)
    except Exception:
        suggestions = []
    return {"suggestions": suggestions}
