from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def orders_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "orders.csv")


@pytest.fixture
def customers_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "customers.csv")


@pytest.fixture
def products_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / "products.csv")
