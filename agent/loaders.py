"""File loading and table-name normalization for environment inputs."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".parquet"}


def normalize_table_name(name: str) -> str:
    """Normalize one proposed table name into a stable model-facing identifier."""

    normalized_name = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    if not normalized_name:
        raise ValueError("Table name must contain at least one letter or number.")
    return normalized_name


def load_file(path: str | Path) -> tuple[str, pd.DataFrame]:
    """Load one file and return its normalized table name and dataframe."""

    resolved_path = Path(path)
    suffix = resolved_path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type: {resolved_path.suffix}. Supported: {supported}"
        )

    table_name = normalize_table_name(resolved_path.stem)
    dataframe = _read_dataframe(resolved_path, suffix)
    return table_name, dataframe


def load_files(paths: list[str | Path]) -> dict[str, pd.DataFrame]:
    """Load multiple files and fail loudly on duplicate normalized table names."""

    tables: dict[str, pd.DataFrame] = {}
    seen_paths: dict[str, Path] = {}

    for raw_path in paths:
        table_name, dataframe = load_file(raw_path)
        resolved_path = Path(raw_path)

        if table_name in tables:
            first_path = seen_paths[table_name]
            raise ValueError(
                f"Duplicate table name '{table_name}' for files "
                f"'{first_path.name}' and '{resolved_path.name}'."
            )

        tables[table_name] = dataframe
        seen_paths[table_name] = resolved_path

    return tables


def _read_dataframe(path: Path, suffix: str) -> pd.DataFrame:
    """Read one supported file into a dataframe."""

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".xlsx":
        return pd.read_excel(path)
    return pd.read_parquet(path)
