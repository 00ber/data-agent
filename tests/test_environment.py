import pandas as pd
import pytest

from agent.environment import (
    AnalysisHandoff,
    Artifact,
    Environment,
    ExecutionResult,
)
from agent.tools import Tools
from agent.sandbox import ExecutionSandbox


@pytest.fixture
def sandbox():
    return ExecutionSandbox()


class TestArtifact:
    def test_stores_artifact_fields(self):
        artifact = Artifact(
            id="artifact_1",
            kind="table",
            title="Revenue by Region",
            data={"rows": [[1, 2]]},
        )

        assert artifact.id == "artifact_1"
        assert artifact.kind == "table"
        assert artifact.title == "Revenue by Region"
        assert artifact.data == {"rows": [[1, 2]]}


class TestExecutionResult:
    def test_stores_execution_outcome_fields(self):
        outcome = ExecutionResult(
            events=[],
            output="OK",
            is_error=False,
            analysis_handoff=None,
            step_summary=None,
        )

        assert outcome.events == []
        assert outcome.output == "OK"
        assert outcome.is_error is False
        assert outcome.analysis_handoff is None
        assert outcome.step_summary is None


class TestEnvironment:
    def test_starts_with_empty_workspace_and_artifacts(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        assert environment.workspace == {}
        assert environment.artifacts == []

    def test_add_input_table_copies_dataframe_into_inputs(self, sandbox):
        source = pd.DataFrame({"value": [1, 2, 3]})
        environment = Environment(inputs={}, sandbox=sandbox)

        environment.add_input_table("sales", source)
        source["value"] = source["value"] * 10

        assert "sales" in environment.inputs
        assert environment.inputs["sales"]["value"].tolist() == [1, 2, 3]

    def test_add_input_table_rejects_duplicate_name(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        with pytest.raises(ValueError, match="Input table name 'orders' already exists."):
            environment.add_input_table("orders", orders_df)

    def test_execute_can_access_input_tables(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        outcome = environment.execute("print(len(orders))")

        assert outcome.is_error is False
        assert outcome.output == str(len(orders_df))
        assert outcome.analysis_handoff is None
        assert [event.kind for event in outcome.events] == ["result"]
        assert outcome.step_summary == "Step summary:\n- text output: " + str(len(orders_df))

    def test_execute_can_access_pandas_and_numpy(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        outcome = environment.execute(
            "totals = pd.Series([1, 2, 3])\nprint(int(np.sum(totals)))"
        )

        assert outcome.is_error is False
        assert outcome.output == "6"

    def test_successful_execution_persists_workspace_variables(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        environment.execute("high_value_orders = orders[orders['revenue'] > 200]")
        outcome = environment.execute("print(len(high_value_orders))")

        assert outcome.is_error is False
        assert outcome.output == "4"

    def test_input_table_names_reset_each_execution(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        environment.execute("orders = orders.head(1)\nfirst_order = orders")
        outcome = environment.execute(
            "print(len(orders))\nprint(len(first_order))"
        )

        assert outcome.is_error is False
        assert outcome.output == f"{len(orders_df)}\n1"

    def test_original_input_dataframe_is_not_mutated(self, orders_df, sandbox):
        source_orders = orders_df.copy(deep=True)
        environment = Environment(inputs={"orders": source_orders}, sandbox=sandbox)

        environment.execute("orders['revenue'] = orders['revenue'] * 100")
        outcome = environment.execute("print(int(orders['revenue'].iloc[0]))")

        assert outcome.is_error is False
        assert outcome.output == str(int(orders_df["revenue"].iloc[0]))
        assert source_orders.equals(orders_df)

    def test_runtime_errors_return_error_outcome(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        outcome = environment.execute("1 / 0")

        assert outcome.is_error is True
        assert outcome.analysis_handoff is None
        assert "ZeroDivisionError" in outcome.output
        assert [event.kind for event in outcome.events] == ["error"]
        assert outcome.step_summary is None

    def test_conclude_analysis_is_returned_in_outcome(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        outcome = environment.execute(
            'conclude_analysis("West leads revenue.")'
        )

        assert outcome.is_error is False
        assert outcome.output is None
        assert outcome.analysis_handoff == AnalysisHandoff(
            notes="West leads revenue.",
            artifact_ids=[],
        )
        assert outcome.events == []
        assert outcome.step_summary is None

    def test_successful_execution_tracks_new_dataframe_in_step_summary(
        self,
        orders_df,
        customers_df,
        sandbox,
    ):
        environment = Environment(
            inputs={"orders": orders_df, "customers": customers_df},
            sandbox=sandbox,
        )
        Tools().register_with(environment)

        outcome = environment.execute(
            'joined = join("orders", "customers", on="customer_id")'
        )

        assert outcome.is_error is False
        assert outcome.step_summary is not None
        assert "dataframe joined" in outcome.step_summary
        assert "region_x" in outcome.step_summary
        assert "region_y" in outcome.step_summary

    def test_successful_execution_tracks_published_artifact_in_step_summary(
        self,
        sandbox,
    ):
        environment = Environment(inputs={}, sandbox=sandbox)

        def publish_stat(execution_context, label: str, value: int) -> str:
            artifact = execution_context.publish_artifact(
                "stat",
                label,
                {"label": label, "value": value},
            )
            return artifact.id

        environment.register_action("publish_stat", publish_stat)

        outcome = environment.execute('artifact_id = publish_stat("Total Revenue", 42)')

        assert outcome.is_error is False
        assert outcome.step_summary is not None
        assert environment.artifacts[0].id in outcome.step_summary
        assert "stat 'Total Revenue'" in outcome.step_summary

    def test_successful_execution_tracks_in_place_dataframe_metadata_changes(
        self,
        orders_df,
        sandbox,
    ):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        first_outcome = environment.execute('working = orders.copy()')
        second_outcome = environment.execute(
            "working['discount'] = 0\n"
            "working = working[['order_id', 'discount']]"
        )

        assert first_outcome.is_error is False
        assert second_outcome.is_error is False
        assert second_outcome.step_summary is not None
        assert "dataframe working" in second_outcome.step_summary
        assert "discount" in second_outcome.step_summary

    def test_conclude_analysis_accepts_valid_inline_artifact_mentions(self, sandbox):
        environment = Environment(inputs={}, sandbox=sandbox)

        def publish_stat(execution_context, label: str, value: int) -> str:
            artifact = execution_context.publish_artifact(
                "stat",
                label,
                {"label": label, "value": value},
            )
            return artifact.id

        environment.register_action("publish_stat", publish_stat)

        outcome = environment.execute(
            'artifact_id = publish_stat("Total Revenue", 42)\n'
            'conclude_analysis("The stat @" + artifact_id + " shows total revenue.", [artifact_id])'
        )

        assert outcome.is_error is False
        assert outcome.analysis_handoff == AnalysisHandoff(
            notes=f"The stat @{environment.artifacts[0].id} shows total revenue.",
            artifact_ids=[environment.artifacts[0].id],
        )

    def test_conclude_analysis_rejects_mentioned_artifact_missing_from_artifact_ids(
        self,
        sandbox,
    ):
        environment = Environment(inputs={}, sandbox=sandbox)

        def publish_stat(execution_context, label: str, value: int) -> str:
            artifact = execution_context.publish_artifact(
                "stat",
                label,
                {"label": label, "value": value},
            )
            return artifact.id

        environment.register_action("publish_stat", publish_stat)

        outcome = environment.execute(
            'artifact_id = publish_stat("Total Revenue", 42)\n'
            'conclude_analysis("The stat @" + artifact_id + " shows total revenue.", [])'
        )

        assert outcome.is_error is True
        assert "mentioned in notes must also appear in artifact_ids" in outcome.output

    def test_conclude_analysis_rejects_unknown_artifact_ids(self, sandbox):
        environment = Environment(inputs={}, sandbox=sandbox)

        outcome = environment.execute(
            'conclude_analysis("The stat @artifact_missing shows total revenue.", ["artifact_missing"])'
        )

        assert outcome.is_error is True
        assert "Unknown artifact reference 'artifact_missing'" in outcome.output

    def test_publish_artifact_stores_artifact_and_emits_event_during_execution(
        self,
        sandbox,
    ):
        environment = Environment(inputs={}, sandbox=sandbox)

        def show_stat(execution_context, label: str, value: int) -> str:
            execution_context.publish_artifact(
                "stat",
                label,
                {"label": label, "value": value},
            )
            return f"Displayed stat: {label} = {value}"

        environment.register_action("show_stat", show_stat)

        outcome = environment.execute("show_stat('Total Revenue', 42)")

        assert len(environment.artifacts) == 1
        assert environment.artifacts[0].title == "Total Revenue"
        assert [event.kind for event in outcome.events] == ["artifact", "result"]
        assert outcome.output == "'Displayed stat: Total Revenue = 42'"

    def test_rejects_action_name_collision_with_input_table(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        with pytest.raises(ValueError, match="Action name 'orders' conflicts with an existing runtime name."):
            environment.register_action("orders", lambda: None)

    def test_describe_lists_input_tables_and_columns(self, orders_df, sandbox):
        environment = Environment(inputs={"orders": orders_df}, sandbox=sandbox)

        description = environment.describe()

        assert "orders" in description
        assert "revenue" in description
        assert "category" in description
