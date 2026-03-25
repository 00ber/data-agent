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

from openai import AsyncOpenAI as _AsyncOpenAI

from agent import run, load_file, Session, AgentConfig
from agent.prompts import describe_tables
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


async def _generate_suggestions(session: Session) -> list[str]:
    """Generate question suggestions from loaded table schemas."""
    if not session.tables:
        return []

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
