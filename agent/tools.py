"""Analytics tools exposed inside the execution environment."""

from __future__ import annotations

from typing import Any

import pandas as pd

from agent.environment import Environment, ExecutionContext

FILTER_OPS = {
    "==": lambda series, value: series == value,
    "!=": lambda series, value: series != value,
    ">": lambda series, value: series > value,
    "<": lambda series, value: series < value,
    ">=": lambda series, value: series >= value,
    "<=": lambda series, value: series <= value,
    "contains": lambda series, value: series.str.contains(value, na=False),
    "startswith": lambda series, value: series.str.startswith(value, na=False),
    "endswith": lambda series, value: series.str.endswith(value, na=False),
}


class Tools:
    """Analytics actions that can be registered with an environment."""

    ACTION_NAMES = (
        "filter",
        "group_by",
        "sort",
        "join",
        "show_chart",
        "show_table",
        "show_stat",
    )
    AGGREGATIONS = {"sum", "mean", "count", "min", "max", "median", "std"}
    CHART_TYPES = {"bar", "line", "scatter", "pie", "histogram"}

    def register_with(self, environment: Environment) -> None:
        """Register all public tool actions with one environment."""

        for action_name in self.ACTION_NAMES:
            environment.register_action(action_name, getattr(self, action_name))

    def filter(
        self,
        execution_context: ExecutionContext,
        table: str | pd.DataFrame,
        column: str,
        op: str,
        value: Any,
    ) -> pd.DataFrame:
        """Purpose: Filter rows where one column matches the requested condition.
        Parameters:
        - table: Table name such as "orders" or a dataframe from a previous step.
        - column: Existing column to test.
        - op: One of ==, !=, >, <, >=, <=, contains, startswith, or endswith.
        - value: Value compared against that column.
        Returns: A filtered dataframe.
        Emits: table artifact
        Example: west_orders = filter("orders", "region", "==", "West")
        """

        df = self._resolve(execution_context, table)
        self._validate_column(df, column)

        if op not in FILTER_OPS:
            raise ValueError(
                f"Unknown operator: '{op}'. Supported: {', '.join(sorted(FILTER_OPS))}"
            )

        filtered = df[FILTER_OPS[op](df[column], value)].reset_index(drop=True)
        execution_context.publish_artifact(
            "table",
            f"Filtered: {column} {op} {value}",
            self._table_data(filtered),
        )
        return filtered

    def group_by(
        self,
        execution_context: ExecutionContext,
        table: str | pd.DataFrame,
        by: str | list[str],
        column: str,
        agg: str,
    ) -> pd.DataFrame:
        """Purpose: Group rows by one or more columns and aggregate another column.
        Parameters:
        - table: Table name or dataframe to group.
        - by: One column name or a list of column names to group on.
        - column: Column whose values will be aggregated.
        - agg: One of sum, mean, count, min, max, median, or std.
        Returns: A grouped dataframe with the grouping columns and aggregated column.
        Emits: table artifact
        Example: revenue_by_region = group_by("orders", "region", "revenue", "sum")
        """

        df = self._resolve(execution_context, table)
        by_columns = [by] if isinstance(by, str) else by

        for group_column in by_columns:
            self._validate_column(df, group_column)
        self._validate_column(df, column)

        if agg not in self.AGGREGATIONS:
            raise ValueError(
                f"Unknown aggregation: '{agg}'. Supported: {', '.join(sorted(self.AGGREGATIONS))}"
            )

        grouped = df.groupby(by_columns, as_index=False)[column].agg(agg)
        execution_context.publish_artifact(
            "table",
            f"{agg}({column}) by {', '.join(by_columns)}",
            self._table_data(grouped),
        )
        return grouped

    def sort(
        self,
        execution_context: ExecutionContext,
        table: str | pd.DataFrame,
        by: str | list[str],
        ascending: bool | list[bool] = True,
    ) -> pd.DataFrame:
        """Purpose: Sort rows by one or more existing columns.
        Parameters:
        - table: Table name or dataframe to sort.
        - by: One existing column name or a list of column names to sort on.
        - ascending: True or False for a single sort, or a list of True/False
          flags matching the sort columns for a multi-column sort.
        Returns: A sorted dataframe.
        Emits: table artifact
        Example: top_orders = sort("orders", ["segment", "revenue"], ascending=[True, False])
        """

        df = self._resolve(execution_context, table)
        by_columns = [by] if isinstance(by, str) else by
        for sort_column in by_columns:
            self._validate_column(df, sort_column)

        if isinstance(ascending, list) and len(ascending) != len(by_columns):
            raise ValueError("Ascending flags must match the number of sort columns.")

        sorted_df = df.sort_values(by_columns, ascending=ascending).reset_index(drop=True)
        if isinstance(ascending, list):
            direction = "mixed"
        else:
            direction = "ascending" if ascending else "descending"
        execution_context.publish_artifact(
            "table",
            f"Sorted by {', '.join(by_columns)} ({direction})",
            self._table_data(sorted_df),
        )
        return sorted_df

    def join(
        self,
        execution_context: ExecutionContext,
        left: str | pd.DataFrame,
        right: str | pd.DataFrame,
        on: str | list[str],
        how: str = "inner",
    ) -> pd.DataFrame:
        """Purpose: Join two tables on one shared key column.
        Parameters:
        - left: Left table name or dataframe.
        - right: Right table name or dataframe.
        - on: One shared key column name, or a list of shared key column names.
        - how: Join mode such as inner, left, right, or outer.
        Returns: A joined dataframe. If both tables share non-key column names,
        pandas-style suffixes such as _x and _y are applied to those overlapping
        columns in the result.
        Emits: table artifact
        Example: orders_with_customers = join("orders", "customers", on="customer_id")
        """

        left_df = self._resolve(execution_context, left)
        right_df = self._resolve(execution_context, right)
        join_columns = [on] if isinstance(on, str) else on

        for join_column in join_columns:
            if join_column not in left_df.columns:
                raise ValueError(
                    f"Join column '{join_column}' not found in left table. Available: {', '.join(left_df.columns)}"
                )
            if join_column not in right_df.columns:
                raise ValueError(
                    f"Join column '{join_column}' not found in right table. Available: {', '.join(right_df.columns)}"
                )

        joined = left_df.merge(right_df, on=join_columns, how=how)
        execution_context.publish_artifact(
            "table",
            f"Joined on {', '.join(join_columns)} ({how})",
            self._table_data(joined),
        )
        return joined

    def show_chart(
        self,
        execution_context: ExecutionContext,
        data: str | pd.DataFrame,
        kind: str = "bar",
        title: str = "",
    ) -> str:
        """Purpose: Display a dataframe as a visible chart artifact.
        Parameters:
        - data: Table name or dataframe to visualize.
        - kind: One of bar, line, scatter, pie, or histogram.
        - title: Chart title shown to the user.
        Returns: A confirmation string.
        Emits: chart artifact
        Example: show_chart(revenue_by_region, kind="bar", title="Revenue by Region")
        """

        df = self._resolve(execution_context, data)

        if kind not in self.CHART_TYPES:
            raise ValueError(
                f"Unknown chart type: '{kind}'. Supported: {', '.join(sorted(self.CHART_TYPES))}"
            )

        execution_context.publish_artifact(
            "chart",
            title,
            {
                "chart_type": kind,
                "columns": list(df.columns),
                "records": df.to_dict(orient="records"),
            },
        )
        return f"Displayed {kind} chart: {title}"

    def show_table(
        self,
        execution_context: ExecutionContext,
        data: str | pd.DataFrame,
        title: str = "",
    ) -> str:
        """Purpose: Display a dataframe as a visible table artifact.
        Parameters:
        - data: Table name or dataframe to display.
        - title: Table title shown to the user.
        Returns: A confirmation string.
        Emits: table artifact
        Example: show_table(top_orders, title="Top Orders by Revenue")
        """

        df = self._resolve(execution_context, data)
        execution_context.publish_artifact("table", title, self._table_data(df))
        return f"Displayed table: {title} ({len(df)} rows)"

    def show_stat(
        self,
        execution_context: ExecutionContext,
        label: str,
        value: Any,
    ) -> str:
        """Purpose: Display one label-value pair as a visible stat artifact.
        Parameters:
        - label: Stat name shown to the user.
        - value: Value shown for that stat.
        Returns: A confirmation string.
        Emits: stat artifact
        Example: show_stat("Total Revenue", orders["revenue"].sum())
        """

        execution_context.publish_artifact(
            "stat",
            label,
            {"label": label, "value": value},
        )
        return f"Displayed stat: {label} = {value}"

    def _resolve(
        self,
        execution_context: ExecutionContext,
        table: str | pd.DataFrame,
    ) -> pd.DataFrame:
        """Resolve a table name to a dataframe, or pass through a dataframe."""

        if isinstance(table, pd.DataFrame):
            return table

        available_tables = self._available_tables(execution_context)
        if table not in available_tables:
            available_names = ", ".join(sorted(available_tables))
            raise ValueError(
                f"Unknown table: '{table}'. Available tables: {available_names}"
            )

        return available_tables[table]

    def _available_tables(
        self,
        execution_context: ExecutionContext,
    ) -> dict[str, pd.DataFrame]:
        """Return all resolvable dataframe names in the environment."""

        available = dict(execution_context.environment.inputs)

        for name, value in execution_context.environment.workspace.items():
            if isinstance(value, pd.DataFrame):
                available[name] = value

        return available

    def _validate_column(self, df: pd.DataFrame, column: str) -> None:
        """Raise a clear error when a dataframe column is missing."""

        if column not in df.columns:
            raise ValueError(
                f"Column '{column}' not found. Available columns: {', '.join(df.columns)}"
            )

    def _table_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """Convert a dataframe into table artifact payload data."""

        return {
            "columns": list(df.columns),
            "rows": df.values.tolist(),
            "shape": list(df.shape),
        }
