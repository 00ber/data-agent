import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from agent import Agent, CodeStep, OpenAILLM
from api.datasets import SAMPLE_DATASETS, get_dataset_paths
from api.sessions import AgentSession, InMemoryAgentSessionStore


class FakeLLM:
    def __init__(self, responses: list[CodeStep]) -> None:
        self._responses = iter(responses)

    async def generate(self, messages: list[dict[str, str]]) -> CodeStep:
        return next(self._responses)


def parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    current_event = ""

    for line in body.splitlines():
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ").strip()
            continue

        if line.startswith("data: ") and current_event:
            events.append(
                {
                    "event": current_event,
                    "data": json.loads(line.removeprefix("data: ").strip()),
                }
            )
            current_event = ""

    return events


@pytest.fixture
def session_store(monkeypatch: pytest.MonkeyPatch) -> InMemoryAgentSessionStore:
    store = InMemoryAgentSessionStore()
    monkeypatch.setattr(api_main, "session_store", store)
    return store


@pytest.fixture
def client(session_store: InMemoryAgentSessionStore) -> TestClient:
    return TestClient(api_main.app)


class TestSampleDatasets:
    def test_catalog_not_empty(self):
        assert len(SAMPLE_DATASETS) > 0

    def test_each_dataset_has_required_fields(self):
        for dataset in SAMPLE_DATASETS:
            assert dataset.id
            assert dataset.name
            assert dataset.description
            assert dataset.icon
            assert len(dataset.files) > 0


class TestGetDatasetPaths:
    def test_returns_paths_for_known_dataset(self):
        paths = get_dataset_paths("ecommerce")

        assert len(paths) > 0
        assert all(isinstance(path, str) for path in paths)

    def test_paths_point_to_existing_files(self):
        paths = get_dataset_paths("ecommerce")

        for path in paths:
            assert Path(path).exists(), f"File not found: {path}"

    def test_unknown_dataset_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset: 'fake'"):
            get_dataset_paths("fake")


class TestInMemoryAgentSessionStore:
    def test_create_returns_id_and_live_agent_session(self):
        store = InMemoryAgentSessionStore()

        session_id = store.create()
        session = store.get(session_id)

        assert isinstance(session_id, str)
        assert len(session_id) == 12
        assert isinstance(session, AgentSession)
        assert isinstance(session.agent, Agent)

    def test_create_uses_requested_model_and_temperature(self):
        store = InMemoryAgentSessionStore()

        session_id = store.create(model="gpt-4o-mini", temperature=0.4)
        session = store.get(session_id)

        assert isinstance(session.agent.llm, OpenAILLM)
        assert session.agent.llm.model == "gpt-4o-mini"
        assert session.agent.llm.temperature == 0.4

    def test_get_unknown_id_raises(self):
        store = InMemoryAgentSessionStore()

        with pytest.raises(KeyError):
            store.get("missing")

    def test_delete_removes_session(self):
        store = InMemoryAgentSessionStore()
        session_id = store.create()

        store.delete(session_id)

        with pytest.raises(KeyError):
            store.get(session_id)


class TestHealthRoute:
    def test_health(self, client: TestClient):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDatasetsRoute:
    def test_list_datasets(self, client: TestClient):
        response = client.get("/api/datasets")

        assert response.status_code == 200
        datasets = response.json()
        assert len(datasets) > 0
        assert all("id" in dataset for dataset in datasets)
        assert all("name" in dataset for dataset in datasets)


class TestSessionRoutes:
    def test_create_session_builds_live_agent_session(
        self,
        client: TestClient,
        session_store: InMemoryAgentSessionStore,
    ):
        response = client.post("/api/sessions", json={})

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        session = session_store.get(session_id)
        assert isinstance(session, AgentSession)
        assert isinstance(session.agent, Agent)
        assert session.agent.environment.inputs == {}
        assert session.agent.memory.conversation_messages() == []

    def test_create_session_rejects_blank_model(self, client: TestClient):
        response = client.post(
            "/api/sessions",
            json={"model": "   "},
        )

        assert response.status_code == 422

    def test_load_sample_dataset_adds_input_tables(
        self,
        client: TestClient,
        session_store: InMemoryAgentSessionStore,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]

        response = client.post(f"/api/sessions/{session_id}/datasets/ecommerce")

        assert response.status_code == 200
        tables = response.json()["tables"]
        assert len(tables) > 0

        session = session_store.get(session_id)
        assert set(session.agent.environment.inputs) == {
            table["name"] for table in tables
        }

    def test_load_sample_dataset_rejects_duplicate_table_names(
        self,
        client: TestClient,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]

        first = client.post(f"/api/sessions/{session_id}/datasets/ecommerce")
        second = client.post(f"/api/sessions/{session_id}/datasets/ecommerce")

        assert first.status_code == 200
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"]

    def test_upload_files_adds_input_tables(
        self,
        client: TestClient,
        session_store: InMemoryAgentSessionStore,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]

        files = [
            (
                "files",
                ("sales-report.csv", b"region,revenue\nWest,100\nEast,200\n", "text/csv"),
            )
        ]

        response = client.post(f"/api/sessions/{session_id}/files", files=files)

        assert response.status_code == 200
        assert response.json()["tables"] == [{"name": "sales_report", "rows": 2, "columns": 2}]

        session = session_store.get(session_id)
        assert "sales_report" in session.agent.environment.inputs

    def test_upload_files_rejects_duplicate_table_names(
        self,
        client: TestClient,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]
        client.post(f"/api/sessions/{session_id}/datasets/ecommerce")

        files = [
            (
                "files",
                ("orders.csv", b"order_id,revenue\n1,100\n", "text/csv"),
            )
        ]

        response = client.post(f"/api/sessions/{session_id}/files", files=files)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_get_tables_reads_environment_inputs(
        self,
        client: TestClient,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]
        client.post(f"/api/sessions/{session_id}/datasets/ecommerce")

        response = client.get(f"/api/sessions/{session_id}/tables")

        assert response.status_code == 200
        tables = response.json()["tables"]
        assert len(tables) > 0
        assert "name" in tables[0]
        assert "columns" in tables[0]
        assert "dtype" in tables[0]["columns"][0]

    def test_unknown_session_returns_404(self, client: TestClient):
        response = client.get("/api/sessions/missing/tables")

        assert response.status_code == 404

    def test_unknown_dataset_returns_404(self, client: TestClient):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]

        response = client.post(f"/api/sessions/{session_id}/datasets/missing")

        assert response.status_code == 404


class TestMessagesRoute:
    def test_messages_route_streams_agent_events(
        self,
        client: TestClient,
        session_store: InMemoryAgentSessionStore,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]
        session = session_store.get(session_id)
        session.agent.llm = FakeLLM(
            [CodeStep(plan="Answer directly", code="final_answer('done')")]
        )

        response = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "What happened?"},
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)
        assert [event["event"] for event in events] == ["thinking", "code", "answer"]
        assert events[-1]["data"] == {"text": "done"}

    def test_same_session_preserves_memory_workspace_and_artifacts(
        self,
        client: TestClient,
        session_store: InMemoryAgentSessionStore,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]
        session = session_store.get(session_id)
        session.agent.llm = FakeLLM(
            [
                CodeStep(
                    plan="Store a value",
                    code="saved_total = 7\nfinal_answer('Saved total.')",
                ),
                CodeStep(
                    plan="Recall it",
                    code="final_answer(str(saved_total))",
                ),
            ]
        )

        first = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Store the total."},
        )
        second = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "What total did you store?"},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert session.agent.environment.workspace["saved_total"] == 7
        assert session.agent.memory.conversation_messages() == [
            {"role": "user", "content": "Store the total."},
            {"role": "assistant", "content": "Saved total."},
            {"role": "user", "content": "What total did you store?"},
            {"role": "assistant", "content": "7"},
        ]

        second_events = parse_sse_events(second.text)
        assert second_events[-1]["data"] == {"text": "7"}


class TestSuggestionsRoute:
    def test_returns_suggestions_list(
        self,
        client: TestClient,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]
        client.post(f"/api/sessions/{session_id}/datasets/world_indicators")

        mock_response = type(
            "FakeResponse",
            (),
            {"output_text": "What is the GDP trend?\nWhich country has highest life expectancy?\nHow has population grown?\nWhat correlates with GDP?"},
        )()

        with patch("api.main._AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.responses.create.return_value = mock_response
            mock_cls.return_value = mock_client

            response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == [
            "What is the GDP trend?",
            "Which country has highest life expectancy?",
            "How has population grown?",
            "What correlates with GDP?",
        ]

    def test_empty_tables_returns_empty(
        self,
        client: TestClient,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]

        response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        assert response.json()["suggestions"] == []

    def test_llm_error_returns_empty(
        self,
        client: TestClient,
    ):
        session_id = client.post("/api/sessions", json={}).json()["session_id"]
        client.post(f"/api/sessions/{session_id}/datasets/world_indicators")

        with patch("api.main._AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.responses.create.side_effect = Exception("API error")
            mock_cls.return_value = mock_client

            response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        assert response.json()["suggestions"] == []
