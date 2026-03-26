import pandas as pd
import pytest

from agent.environment import Environment, ExecutionContext
from agent.sandbox import ExecutionSandbox
from agent.tools import Tools


@pytest.fixture
def sandbox():
    return ExecutionSandbox()


@pytest.fixture
def environment(orders_df, customers_df, sandbox):
    return Environment(
        inputs={"orders": orders_df, "customers": customers_df},
        sandbox=sandbox,
    )


@pytest.fixture
def execution_context(environment):
    return ExecutionContext(environment)


@pytest.fixture
def tools():
    return Tools()


class TestResolve:
    def test_resolve_string_returns_dataframe(self, tools, execution_context, orders_df):
        result = tools._resolve(execution_context, "orders")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(orders_df)

    def test_resolve_dataframe_returns_same(self, tools, execution_context):
        df = pd.DataFrame({"x": [1]})

        result = tools._resolve(execution_context, df)

        assert result is df

    def test_resolve_workspace_dataframe_by_name(self, tools, execution_context):
        execution_context.environment.workspace["grouped"] = pd.DataFrame({"x": [1, 2]})

        result = tools._resolve(execution_context, "grouped")

        assert list(result["x"]) == [1, 2]

    def test_resolve_unknown_table_raises(self, tools, execution_context):
        with pytest.raises(ValueError, match="Unknown table: 'missing'"):
            tools._resolve(execution_context, "missing")

    def test_resolve_error_lists_available_tables(self, tools, execution_context):
        with pytest.raises(ValueError, match="orders"):
            tools._resolve(execution_context, "missing")


class TestFilter:
    def test_equals(self, tools, execution_context):
        result = tools.filter(execution_context, "orders", "category", "==", "Electronics")

        assert isinstance(result, pd.DataFrame)
        assert all(result["category"] == "Electronics")

    def test_greater_than(self, tools, execution_context):
        result = tools.filter(execution_context, "orders", "revenue", ">", 200)

        assert all(result["revenue"] > 200)

    def test_contains(self, tools, execution_context):
        result = tools.filter(execution_context, "orders", "category", "contains", "Elec")

        assert all("Elec" in value for value in result["category"])

    def test_does_not_emit_table_artifact(self, tools, execution_context):
        tools.filter(execution_context, "orders", "category", "==", "Home")

        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []

    def test_invalid_column_raises(self, tools, execution_context):
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            tools.filter(execution_context, "orders", "nonexistent", "==", "x")

    def test_invalid_operator_raises(self, tools, execution_context):
        with pytest.raises(ValueError, match="Unknown operator: 'like'"):
            tools.filter(execution_context, "orders", "category", "like", "x")

    def test_accepts_dataframe_input(self, tools, execution_context, orders_df):
        result = tools.filter(execution_context, orders_df, "category", "==", "Home")

        assert all(result["category"] == "Home")


class TestGroupBy:
    def test_sum_aggregation(self, tools, execution_context):
        result = tools.group_by(execution_context, "orders", "category", "revenue", "sum")

        assert len(result) == 2
        assert "category" in result.columns
        assert "revenue" in result.columns

    def test_group_by_multiple_columns(self, tools, execution_context):
        result = tools.group_by(
            execution_context,
            "orders",
            ["category", "region"],
            "revenue",
            "sum",
        )

        assert "category" in result.columns
        assert "region" in result.columns
        assert "revenue" in result.columns

    def test_invalid_agg_raises(self, tools, execution_context):
        with pytest.raises(ValueError, match="Unknown aggregation: 'mode'"):
            tools.group_by(execution_context, "orders", "category", "revenue", "mode")

    def test_does_not_emit_table_artifact(self, tools, execution_context):
        tools.group_by(execution_context, "orders", "category", "revenue", "sum")

        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []


class TestSort:
    def test_descending(self, tools, execution_context):
        result = tools.sort(execution_context, "orders", "revenue", ascending=False)

        assert list(result["revenue"]) == sorted(result["revenue"], reverse=True)

    def test_sort_multiple_columns_with_multiple_directions(
        self,
        tools,
        execution_context,
    ):
        df = pd.DataFrame(
            {
                "segment": ["consumer", "consumer", "smb", "consumer"],
                "total": [200, 100, 300, 150],
            }
        )

        result = tools.sort(
            execution_context,
            df,
            by=["segment", "total"],
            ascending=[True, False],
        )

        assert result["segment"].tolist() == ["consumer", "consumer", "consumer", "smb"]
        assert result["total"].tolist() == [200, 150, 100, 300]

    def test_sort_rejects_mismatched_ascending_length(self, tools, execution_context):
        with pytest.raises(
            ValueError,
            match="Ascending flags must match the number of sort columns.",
        ):
            tools.sort(
                execution_context,
                "orders",
                by=["category", "region"],
                ascending=[True],
            )

    def test_does_not_emit_table_artifact(self, tools, execution_context):
        tools.sort(execution_context, "orders", "revenue", ascending=False)

        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []


class TestJoin:
    def test_inner_join(self, tools, execution_context):
        result = tools.join(execution_context, "orders", "customers", on="customer_id")

        assert "name" in result.columns
        assert "revenue" in result.columns
        assert len(result) > 0

    def test_join_applies_suffixes_to_overlapping_non_key_columns(
        self,
        tools,
        execution_context,
    ):
        result = tools.join(execution_context, "orders", "customers", on="customer_id")

        assert "region_x" in result.columns
        assert "region_y" in result.columns

    def test_join_accepts_multiple_key_columns(self, tools, execution_context):
        left = pd.DataFrame(
            {
                "category": ["Furniture", "Furniture", "Technology"],
                "sub-category": ["Chairs", "Tables", "Phones"],
                "orders": [10, 8, 12],
            }
        )
        right = pd.DataFrame(
            {
                "category": ["Furniture", "Technology"],
                "sub-category": ["Chairs", "Phones"],
                "returned": [2, 3],
            }
        )

        result = tools.join(
            execution_context,
            left,
            right,
            on=["category", "sub-category"],
            how="left",
        )

        assert list(result.columns) == ["category", "sub-category", "orders", "returned"]
        assert result["returned"].iloc[0] == 2
        assert pd.isna(result["returned"].iloc[1])
        assert result["returned"].iloc[2] == 3

    def test_invalid_join_column_raises(self, tools, execution_context):
        with pytest.raises(ValueError, match="not found"):
            tools.join(execution_context, "orders", "customers", on="nonexistent")

    def test_does_not_emit_table_artifact(self, tools, execution_context):
        tools.join(execution_context, "orders", "customers", on="customer_id")

        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []


class TestInspect:
    def test_schema_returns_table_shape_columns_and_dtypes(self, tools, execution_context):
        result = tools.schema(execution_context, "orders")

        assert result["rows"] == len(execution_context.environment.inputs["orders"])
        assert "revenue" in result["columns"]
        assert "revenue" in result["dtypes"]
        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []

    def test_head_returns_preview_without_emitting_artifact(self, tools, execution_context):
        result = tools.head(execution_context, "orders", n=2)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []

    def test_sample_returns_preview_without_emitting_artifact(self, tools, execution_context):
        result = tools.sample(execution_context, "orders", n=2)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert execution_context.environment.artifacts == []
        assert execution_context.pending_events == []


class TestShowChart:
    def test_emits_chart_artifact_and_returns_artifact_id(self, tools, execution_context):
        df = pd.DataFrame({"quarter": ["Q1", "Q2"], "revenue": [100, 200]})

        result = tools.publish_chart(
            execution_context,
            df,
            kind="bar",
            title="Revenue by Quarter",
        )

        assert isinstance(result, str)
        assert result.startswith("artifact_")
        assert execution_context.pending_events[0].data["kind"] == "chart"
        assert execution_context.pending_events[0].data["title"] == "Revenue by Quarter"

    def test_invalid_chart_kind_raises(self, tools, execution_context):
        df = pd.DataFrame({"x": [1]})

        with pytest.raises(ValueError, match="Unknown chart type: 'heatmap'"):
            tools.publish_chart(execution_context, df, kind="heatmap", title="Test")


class TestShowTable:
    def test_emits_table_artifact_and_returns_artifact_id(self, tools, execution_context):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        result = tools.publish_table(execution_context, df, title="My Table")

        assert isinstance(result, str)
        assert result.startswith("artifact_")
        assert execution_context.pending_events[0].data["kind"] == "table"


class TestShowStat:
    def test_emits_stat_artifact_and_returns_artifact_id(self, tools, execution_context):
        result = tools.publish_stat(execution_context, "Total Revenue", 8200000)

        assert isinstance(result, str)
        assert result.startswith("artifact_")
        assert execution_context.pending_events[0].data["kind"] == "stat"
        assert execution_context.pending_events[0].data["data"]["value"] == 8200000


class TestRegistration:
    def test_register_with_makes_tools_available_in_environment(self, tools, environment):
        tools.register_with(environment)

        outcome = environment.execute(
            "grouped = group_by('orders', 'category', 'revenue', 'sum')"
        )

        assert outcome.is_error is False
        assert outcome.output == "OK"
        assert "grouped" in environment.workspace
        assert isinstance(environment.workspace["grouped"], pd.DataFrame)
        assert [event.kind for event in outcome.events] == ["result"]
