from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from agent.session import AgentConfig, Session
from api.datasets import SAMPLE_DATASETS, get_dataset_paths
from api.main import app
from api.sessions import SessionManager


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


class TestSuggestionsRoute:
    def test_returns_suggestions_list(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]
        client.post(f"/api/sessions/{session_id}/load-sample/world_indicators")

        mock_message = AsyncMock()
        mock_message.content = "What is the GDP trend?\nWhich country has highest life expectancy?\nHow has population grown?\nWhat correlates with GDP?"
        mock_choice = AsyncMock()
        mock_choice.message = mock_message
        mock_response = AsyncMock()
        mock_response.choices = [mock_choice]

        with patch("api.main._AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_cls.return_value = mock_client

            response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) == 4

    def test_empty_tables_returns_empty(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]

        response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        assert response.json()["suggestions"] == []

    def test_llm_error_returns_empty(self):
        client = TestClient(app)
        session_id = client.post("/api/sessions").json()["session_id"]
        client.post(f"/api/sessions/{session_id}/load-sample/world_indicators")

        with patch("api.main._AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = Exception("API error")
            mock_cls.return_value = mock_client

            response = client.post(f"/api/sessions/{session_id}/suggestions")

        assert response.status_code == 200
        assert response.json()["suggestions"] == []
