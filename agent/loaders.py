"""File loaders for CSV, XLSX, and Parquet."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".parquet"}


def load_file(path: str | Path) -> tuple[str, pd.DataFrame]:
    """Load a data file and return (table_name, DataFrame).

    Table name is inferred from the filename: lowercased, spaces and
    hyphens replaced with underscores.

    Raises ValueError for unsupported file types.
    """
    path = Path(path)

    if path.suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type: {path.suffix}. Supported: {supported}"
        )

    name = path.stem.lower().replace(" ", "_").replace("-", "_")

    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix == ".xlsx":
        df = pd.read_excel(path)
    elif path.suffix == ".parquet":
        df = pd.read_parquet(path)

    return name, df
