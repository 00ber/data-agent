"""Sample dataset catalog."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SampleDataset:
    id: str
    name: str
    description: str
    icon: str
    files: list[str] = field(default_factory=list)


SAMPLE_DATASETS: list[SampleDataset] = [
    SampleDataset(
        id="ecommerce",
        name="E-Commerce Sales",
        description="8K customers, 30K orders across 500 products with returns",
        icon="shopping-cart",
        files=["customers.csv", "orders.csv", "order_items.csv", "products.csv", "returns.csv"],
    ),
    SampleDataset(
        id="superstore",
        name="Superstore Sales",
        description="10K orders with shipping, profit margins, and regional performance",
        icon="store",
        files=["orders.csv", "returns.csv"],
    ),
    SampleDataset(
        id="world_indicators",
        name="World Development Indicators",
        description="142 countries with GDP, life expectancy, and population from 1952 to 2007",
        icon="globe",
        files=["gapminder.csv"],
    ),
]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_dataset_paths(dataset_id: str) -> list[str]:
    """Resolve a sample dataset ID to absolute file paths.

    Raises ValueError for unknown dataset IDs.
    """
    for ds in SAMPLE_DATASETS:
        if ds.id == dataset_id:
            base = DATA_DIR / dataset_id
            return [str(base / f) for f in ds.files]
    raise ValueError(f"Unknown dataset: '{dataset_id}'")
