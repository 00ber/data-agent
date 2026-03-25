import pandas as pd
import pytest

from agent.events import Event, FinalAnswer
from agent.session import Session, Artifact
from agent.tools import Tools


@pytest.fixture
def session_with_orders(orders_df):
    session = Session()
    session.tables["orders"] = orders_df
    return session


@pytest.fixture
def collected_events():
    return []


@pytest.fixture
def tools(session_with_orders, collected_events):
    return Tools(session_with_orders, emit=collected_events.append)


class TestResolve:
    def test_resolve_string_returns_dataframe(self, tools, orders_df):
        result = tools._resolve("orders")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(orders_df)

    def test_resolve_dataframe_returns_same(self, tools):
        df = pd.DataFrame({"x": [1]})

        result = tools._resolve(df)

        assert result is df

    def test_resolve_unknown_table_raises(self, tools):
        with pytest.raises(ValueError, match="Unknown table: 'missing'"):
            tools._resolve("missing")

    def test_resolve_error_lists_available_tables(self, tools):
        with pytest.raises(ValueError, match="orders"):
            tools._resolve("missing")


class TestFilter:
    def test_equals(self, tools, collected_events):
        result = tools.filter("orders", "category", "==", "Electronics")

        assert isinstance(result, pd.DataFrame)
        assert all(result["category"] == "Electronics")

    def test_greater_than(self, tools):
        result = tools.filter("orders", "revenue", ">", 200)

        assert all(result["revenue"] > 200)

    def test_less_than(self, tools):
        result = tools.filter("orders", "revenue", "<", 100)

        assert all(result["revenue"] < 100)

    def test_not_equals(self, tools):
        result = tools.filter("orders", "region", "!=", "West")

        assert all(result["region"] != "West")

    def test_contains(self, tools):
        result = tools.filter("orders", "category", "contains", "Elec")

        assert all("Elec" in val for val in result["category"])

    def test_emits_table_artifact(self, tools, collected_events):
        tools.filter("orders", "category", "==", "Home")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "table"

    def test_invalid_column_raises(self, tools):
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            tools.filter("orders", "nonexistent", "==", "x")

    def test_error_lists_available_columns(self, tools):
        with pytest.raises(ValueError, match="revenue"):
            tools.filter("orders", "nonexistent", "==", "x")

    def test_invalid_operator_raises(self, tools):
        with pytest.raises(ValueError, match="Unknown operator: 'like'"):
            tools.filter("orders", "category", "like", "x")

    def test_accepts_dataframe_input(self, tools, orders_df):
        result = tools.filter(orders_df, "category", "==", "Home")

        assert all(result["category"] == "Home")


class TestGroupBy:
    def test_sum_aggregation(self, tools):
        result = tools.group_by("orders", "category", "revenue", "sum")

        assert len(result) == 2  # Electronics + Home
        assert "category" in result.columns
        assert "revenue" in result.columns

    def test_mean_aggregation(self, tools):
        result = tools.group_by("orders", "category", "revenue", "mean")

        assert len(result) == 2

    def test_count_aggregation(self, tools):
        result = tools.group_by("orders", "category", "revenue", "count")

        assert len(result) == 2

    def test_emits_table_artifact(self, tools, collected_events):
        tools.group_by("orders", "category", "revenue", "sum")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert "category" in artifact_events[0].data["title"].lower() or "group" in artifact_events[0].data["title"].lower()

    def test_invalid_column_raises(self, tools):
        with pytest.raises(ValueError, match="Column 'fake' not found"):
            tools.group_by("orders", "fake", "revenue", "sum")

    def test_invalid_agg_raises(self, tools):
        with pytest.raises(ValueError, match="Unknown aggregation: 'mode'"):
            tools.group_by("orders", "category", "revenue", "mode")

    def test_accepts_dataframe_input(self, tools, orders_df):
        result = tools.group_by(orders_df, "category", "revenue", "sum")

        assert len(result) == 2


class TestSort:
    def test_ascending(self, tools):
        result = tools.sort("orders", "revenue")

        assert list(result["revenue"]) == sorted(result["revenue"])

    def test_descending(self, tools):
        result = tools.sort("orders", "revenue", ascending=False)

        assert list(result["revenue"]) == sorted(result["revenue"], reverse=True)

    def test_emits_table_artifact(self, tools, collected_events):
        tools.sort("orders", "revenue")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1

    def test_invalid_column_raises(self, tools):
        with pytest.raises(ValueError, match="Column 'fake' not found"):
            tools.sort("orders", "fake")

    def test_accepts_dataframe_input(self, tools, orders_df):
        result = tools.sort(orders_df, "revenue")

        assert list(result["revenue"]) == sorted(result["revenue"])


class TestJoin:
    def test_inner_join(self, tools, customers_df):
        tools._session.tables["customers"] = customers_df

        result = tools.join("orders", "customers", on="customer_id")

        assert "name" in result.columns
        assert "revenue" in result.columns
        assert len(result) > 0

    def test_emits_table_artifact(self, tools, customers_df, collected_events):
        tools._session.tables["customers"] = customers_df

        tools.join("orders", "customers", on="customer_id")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1

    def test_invalid_join_column_raises(self, tools, customers_df):
        tools._session.tables["customers"] = customers_df

        with pytest.raises(ValueError, match="not found"):
            tools.join("orders", "customers", on="nonexistent")

    def test_accepts_dataframe_inputs(self, tools, orders_df, customers_df):
        result = tools.join(orders_df, customers_df, on="customer_id")

        assert "name" in result.columns


class TestShowChart:
    def test_emits_chart_artifact(self, tools, collected_events):
        df = pd.DataFrame({"quarter": ["Q1", "Q2"], "revenue": [100, 200]})

        result = tools.show_chart(df, kind="bar", title="Revenue by Quarter")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "chart"
        assert artifact_events[0].data["title"] == "Revenue by Quarter"

    def test_returns_confirmation_string(self, tools):
        df = pd.DataFrame({"x": [1], "y": [2]})

        result = tools.show_chart(df, kind="line", title="Test")

        assert isinstance(result, str)
        assert "chart" in result.lower() or "Test" in result

    def test_chart_data_includes_records(self, tools, collected_events):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})

        tools.show_chart(df, kind="scatter", title="Test")

        artifact = collected_events[0].data
        assert "data" in artifact
        assert artifact["data"]["chart_type"] == "scatter"

    def test_invalid_chart_kind_raises(self, tools):
        df = pd.DataFrame({"x": [1]})

        with pytest.raises(ValueError, match="Unknown chart type: 'heatmap'"):
            tools.show_chart(df, kind="heatmap", title="Test")

    def test_accepts_table_name(self, tools, collected_events):
        tools.show_chart("orders", kind="bar", title="Orders")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1


class TestShowTable:
    def test_emits_table_artifact(self, tools, collected_events):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        tools.show_table(df, title="My Table")

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "table"
        assert artifact_events[0].data["title"] == "My Table"

    def test_returns_confirmation_string(self, tools):
        df = pd.DataFrame({"a": [1]})

        result = tools.show_table(df, title="Test")

        assert isinstance(result, str)

    def test_accepts_table_name(self, tools, collected_events):
        tools.show_table("orders", title="All Orders")

        assert len(collected_events) == 1


class TestShowStat:
    def test_emits_stat_artifact(self, tools, collected_events):
        tools.show_stat("Total Revenue", 8200000)

        artifact_events = [e for e in collected_events if e.kind == "artifact"]
        assert len(artifact_events) == 1
        assert artifact_events[0].data["kind"] == "stat"

    def test_stat_data_has_label_and_value(self, tools, collected_events):
        tools.show_stat("Avg Order Value", 150.50)

        artifact = collected_events[0].data
        assert artifact["data"]["label"] == "Avg Order Value"
        assert artifact["data"]["value"] == 150.50

    def test_returns_confirmation_string(self, tools):
        result = tools.show_stat("Count", 42)

        assert isinstance(result, str)


class TestFinalAnswer:
    def test_raises_final_answer_exception(self, tools):
        with pytest.raises(FinalAnswer) as exc_info:
            tools.final_answer("Revenue is $8.2M")

        assert exc_info.value.answer == "Revenue is $8.2M"
