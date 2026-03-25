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
