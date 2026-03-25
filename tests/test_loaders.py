from pathlib import Path

import pandas as pd
import pytest

from agent.loaders import load_file, load_files, normalize_table_name

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestNormalizeTableName:
    def test_lowercases_and_replaces_separators(self):
        assert normalize_table_name("My Sales-Data") == "my_sales_data"

    def test_collapses_repeated_non_alphanumeric_characters(self):
        assert normalize_table_name("Orders   +++ 2024") == "orders_2024"

    def test_rejects_empty_normalized_name(self):
        with pytest.raises(ValueError, match="Table name must contain at least one letter or number."):
            normalize_table_name("!!!")


class TestLoadFile:
    def test_load_csv(self):
        name, df = load_file(FIXTURES_DIR / "orders.csv")

        assert name == "orders"
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "revenue" in df.columns

    def test_infers_table_name_from_filename(self):
        name, _ = load_file(FIXTURES_DIR / "customers.csv")

        assert name == "customers"

    def test_normalizes_table_name_from_filename(self, tmp_path):
        csv = tmp_path / "My Sales-Data.csv"
        csv.write_text("a,b\n1,2\n")

        name, _ = load_file(csv)

        assert name == "my_sales_data"

    def test_unsupported_extension_raises(self, tmp_path):
        txt = tmp_path / "data.txt"
        txt.write_text("hello")

        with pytest.raises(ValueError, match="Unsupported file type: .txt"):
            load_file(txt)

    def test_unsupported_error_lists_supported_types(self, tmp_path):
        txt = tmp_path / "data.json"
        txt.write_text("{}")

        with pytest.raises(ValueError, match=".csv"):
            load_file(txt)

    def test_load_xlsx(self, tmp_path):
        xlsx = tmp_path / "sales.xlsx"
        pd.DataFrame({"x": [1, 2]}).to_excel(xlsx, index=False)

        name, df = load_file(xlsx)

        assert name == "sales"
        assert len(df) == 2

    def test_load_parquet(self, tmp_path):
        parquet = tmp_path / "events.parquet"
        pd.DataFrame({"x": [1, 2, 3]}).to_parquet(parquet, index=False)

        name, df = load_file(parquet)

        assert name == "events"
        assert len(df) == 3

    def test_accepts_string_path(self):
        name, df = load_file(str(FIXTURES_DIR / "products.csv"))

        assert name == "products"
        assert len(df) == 3


class TestLoadFiles:
    def test_loads_multiple_files_into_name_keyed_mapping(self, tmp_path):
        orders = tmp_path / "orders.csv"
        customers = tmp_path / "customers.csv"
        orders.write_text("id\n1\n")
        customers.write_text("id\n2\n")

        tables = load_files([orders, customers])

        assert list(tables) == ["orders", "customers"]
        assert list(tables["orders"]["id"]) == [1]
        assert list(tables["customers"]["id"]) == [2]

    def test_raises_on_duplicate_normalized_names(self, tmp_path):
        first = tmp_path / "My Sales-Data.csv"
        second = tmp_path / "my_sales_data.parquet"
        first.write_text("id\n1\n")
        pd.DataFrame({"id": [2]}).to_parquet(second, index=False)

        with pytest.raises(ValueError, match="Duplicate table name 'my_sales_data'"):
            load_files([first, second])

    def test_duplicate_error_lists_conflicting_paths(self, tmp_path):
        first = tmp_path / "Orders.csv"
        second = tmp_path / "orders.xlsx"
        first.write_text("id\n1\n")
        pd.DataFrame({"id": [2]}).to_excel(second, index=False)

        with pytest.raises(ValueError, match="Orders.csv"):
            load_files([first, second])

        with pytest.raises(ValueError, match="orders.xlsx"):
            load_files([first, second])
