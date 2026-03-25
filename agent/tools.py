"""Analytics tools — every public method is a tool the LLM can call."""
from __future__ import annotations

import uuid
from typing import Any, Callable

import pandas as pd

from agent.events import Event, FinalAnswer
from agent.session import Artifact, Session

FILTER_OPS = {
    "==": lambda s, v: s == v,
    "!=": lambda s, v: s != v,
    ">": lambda s, v: s > v,
    "<": lambda s, v: s < v,
    ">=": lambda s, v: s >= v,
    "<=": lambda s, v: s <= v,
    "contains": lambda s, v: s.str.contains(v, na=False),
    "startswith": lambda s, v: s.str.startswith(v, na=False),
    "endswith": lambda s, v: s.str.endswith(v, na=False),
}


class Tools:
    """Analytics tools bound to a session.

    Public methods are tools (available in the sandbox).
    Private methods are helpers.
    """

    def __init__(self, session: Session, emit: Callable[[Event], None]) -> None:
        self._session = session
        self._emit = emit

    # -- Private helpers -----------------------------------------------

    def _resolve(self, table: str | pd.DataFrame) -> pd.DataFrame:
        """Resolve a table name to a DataFrame, or pass through a DataFrame."""
        if isinstance(table, pd.DataFrame):
            return table
        if table not in self._session.tables:
            available = ", ".join(sorted(self._session.tables.keys()))
            raise ValueError(
                f"Unknown table: '{table}'. Available tables: {available}"
            )
        return self._session.tables[table]

    def _emit_artifact(
        self, kind: str, title: str, data: dict[str, Any]
    ) -> Artifact:
        """Create an artifact, store it in session, and emit an event."""
        artifact = Artifact(
            id=f"art_{uuid.uuid4().hex[:8]}",
            kind=kind,
            title=title,
            data=data,
        )
        self._session.artifacts.append(artifact)
        self._emit(Event("artifact", {
            "id": artifact.id,
            "kind": artifact.kind,
            "title": artifact.title,
            "data": artifact.data,
        }))
        return artifact

    def _validate_column(self, df: pd.DataFrame, column: str) -> None:
        """Raise ValueError if column doesn't exist in the DataFrame."""
        if column not in df.columns:
            available = ", ".join(df.columns)
            raise ValueError(
                f"Column '{column}' not found. Available columns: {available}"
            )

    def _table_data(self, df: pd.DataFrame) -> dict:
        """Convert a DataFrame to artifact data format."""
        return {
            "columns": list(df.columns),
            "rows": df.values.tolist(),
            "shape": list(df.shape),
        }

    # -- Data tools (return DataFrame, emit table artifact) ------------

    def filter(
        self, table: str | pd.DataFrame, column: str, op: str, value: Any
    ) -> pd.DataFrame:
        """Filter rows where column matches the condition.

        Args:
            table: Table name or DataFrame.
            column: Column to filter on.
            op: Operator — ==, !=, >, <, >=, <=, contains, startswith, endswith.
            value: Value to compare against.

        Returns:
            Filtered DataFrame.
        """
        df = self._resolve(table)
        self._validate_column(df, column)

        if op not in FILTER_OPS:
            raise ValueError(
                f"Unknown operator: '{op}'. "
                f"Supported: {', '.join(sorted(FILTER_OPS.keys()))}"
            )

        mask = FILTER_OPS[op](df[column], value)
        filtered = df[mask].reset_index(drop=True)

        self._emit_artifact(
            "table",
            f"Filtered: {column} {op} {value}",
            self._table_data(filtered),
        )
        return filtered

    AGGREGATIONS = {"sum", "mean", "count", "min", "max", "median", "std"}

    def group_by(
        self,
        table: str | pd.DataFrame,
        by: str,
        column: str,
        agg: str,
    ) -> pd.DataFrame:
        """Group by a column and aggregate another.

        Args:
            table: Table name or DataFrame.
            by: Column to group by.
            column: Column to aggregate.
            agg: Aggregation — sum, mean, count, min, max, median, std.

        Returns:
            Aggregated DataFrame.
        """
        df = self._resolve(table)
        self._validate_column(df, by)
        self._validate_column(df, column)

        if agg not in self.AGGREGATIONS:
            raise ValueError(
                f"Unknown aggregation: '{agg}'. "
                f"Supported: {', '.join(sorted(self.AGGREGATIONS))}"
            )

        grouped = df.groupby(by, as_index=False)[column].agg(agg)

        self._emit_artifact(
            "table",
            f"{agg}({column}) by {by}",
            self._table_data(grouped),
        )
        return grouped

    def sort(
        self,
        table: str | pd.DataFrame,
        by: str,
        ascending: bool = True,
    ) -> pd.DataFrame:
        """Sort rows by a column.

        Args:
            table: Table name or DataFrame.
            by: Column to sort by.
            ascending: Sort direction (default True).

        Returns:
            Sorted DataFrame.
        """
        df = self._resolve(table)
        self._validate_column(df, by)

        sorted_df = df.sort_values(by, ascending=ascending).reset_index(drop=True)

        direction = "ascending" if ascending else "descending"
        self._emit_artifact(
            "table",
            f"Sorted by {by} ({direction})",
            self._table_data(sorted_df),
        )
        return sorted_df

    def join(
        self,
        left: str | pd.DataFrame,
        right: str | pd.DataFrame,
        on: str,
        how: str = "inner",
    ) -> pd.DataFrame:
        """Join two tables on a shared column.

        Args:
            left: Left table name or DataFrame.
            right: Right table name or DataFrame.
            on: Column to join on (must exist in both).
            how: Join type — inner, left, right, outer (default inner).

        Returns:
            Joined DataFrame.
        """
        left_df = self._resolve(left)
        right_df = self._resolve(right)

        if on not in left_df.columns:
            raise ValueError(
                f"Join column '{on}' not found in left table. "
                f"Available: {', '.join(left_df.columns)}"
            )
        if on not in right_df.columns:
            raise ValueError(
                f"Join column '{on}' not found in right table. "
                f"Available: {', '.join(right_df.columns)}"
            )

        joined = left_df.merge(right_df, on=on, how=how)

        self._emit_artifact(
            "table",
            f"Joined on {on} ({how})",
            self._table_data(joined),
        )
        return joined

    # -- Display tools (emit artifact, return confirmation string) ------

    CHART_TYPES = {"bar", "line", "scatter", "pie", "histogram"}

    def show_chart(
        self,
        data: str | pd.DataFrame,
        kind: str = "bar",
        title: str = "",
    ) -> str:
        """Display a chart artifact.

        Args:
            data: Table name or DataFrame to chart.
            kind: Chart type — bar, line, scatter, pie, histogram.
            title: Chart title.

        Returns:
            Confirmation string.
        """
        df = self._resolve(data)

        if kind not in self.CHART_TYPES:
            raise ValueError(
                f"Unknown chart type: '{kind}'. "
                f"Supported: {', '.join(sorted(self.CHART_TYPES))}"
            )

        self._emit_artifact("chart", title, {
            "chart_type": kind,
            "columns": list(df.columns),
            "records": df.to_dict(orient="records"),
        })
        return f"Displayed {kind} chart: {title}"

    def show_table(self, data: str | pd.DataFrame, title: str = "") -> str:
        """Display a formatted table artifact.

        Args:
            data: Table name or DataFrame to display.
            title: Table title.

        Returns:
            Confirmation string.
        """
        df = self._resolve(data)

        self._emit_artifact("table", title, self._table_data(df))
        return f"Displayed table: {title} ({len(df)} rows)"

    def show_stat(self, label: str, value: Any) -> str:
        """Display a stat card artifact.

        Args:
            label: Stat label (e.g. "Total Revenue").
            value: Stat value (e.g. 8200000).

        Returns:
            Confirmation string.
        """
        self._emit_artifact("stat", label, {
            "label": label,
            "value": value,
        })
        return f"Displayed stat: {label} = {value}"

    # -- Termination ---------------------------------------------------

    def final_answer(self, answer: str) -> None:
        """Terminate the agent loop with a final answer.

        Args:
            answer: The answer text to return to the user.

        Raises:
            FinalAnswer: Always. This is how the agent loop terminates.
        """
        raise FinalAnswer(answer)
