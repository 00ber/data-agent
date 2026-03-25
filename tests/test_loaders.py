from pathlib import Path

import pandas as pd
import pytest

from agent.loaders import load_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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

    def test_normalizes_table_name(self, tmp_path):
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
        pq = tmp_path / "events.parquet"
        pd.DataFrame({"x": [1, 2, 3]}).to_parquet(pq, index=False)

        name, df = load_file(pq)

        assert name == "events"
        assert len(df) == 3

    def test_accepts_string_path(self):
        name, df = load_file(str(FIXTURES_DIR / "products.csv"))

        assert name == "products"
        assert len(df) == 3
