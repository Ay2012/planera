"""Dataset loading utilities."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from app.config import get_settings
from app.data.mock_data import MockDataPaths, generate_mock_data
from app.data.transforms import transform_crm_dataframe, transform_sales_dataset, transform_subscriptions_dataframe


@dataclass(frozen=True)
class DataBundle:
    """In-memory datasets used for analytics."""

    raw_views: dict[str, pd.DataFrame]
    crm: pd.DataFrame
    subscriptions: pd.DataFrame | None
    reference_date: str
    source: str


def _has_real_sales_dataset() -> bool:
    settings = get_settings()
    dataset_dir = settings.crm_dataset_dir
    required = [
        dataset_dir / "sales_pipeline.csv",
        dataset_dir / "accounts.csv",
        dataset_dir / "products.csv",
        dataset_dir / "sales_teams.csv",
    ]
    return all(path.exists() for path in required)


def _resolve_sales_reference_date() -> str:
    """Use the latest close date in the real sales dataset as the analysis anchor."""

    settings = get_settings()
    pipeline = pd.read_csv(settings.crm_dataset_dir / "sales_pipeline.csv", usecols=["close_date"])
    close_dates = pd.to_datetime(pipeline["close_date"], errors="coerce").dropna()
    if close_dates.empty:
        return settings.reference_date
    return close_dates.max().date().isoformat()


def _read_real_sales_raw_views() -> dict[str, pd.DataFrame]:
    """Read the raw CRM sales dataset files once."""

    settings = get_settings()
    dataset_dir = settings.crm_dataset_dir
    return {
        "sales_pipeline": pd.read_csv(dataset_dir / "sales_pipeline.csv"),
        "accounts": pd.read_csv(dataset_dir / "accounts.csv"),
        "products": pd.read_csv(dataset_dir / "products.csv"),
        "sales_teams": pd.read_csv(dataset_dir / "sales_teams.csv"),
    }


def ensure_data_files() -> None:
    """Create demo CSVs when the expected files do not exist."""

    settings = get_settings()
    if _has_real_sales_dataset():
        return
    if settings.crm_path.exists() and settings.subscriptions_path.exists():
        return

    generate_mock_data(
        MockDataPaths(
            crm_path=settings.crm_path,
            subscriptions_path=settings.subscriptions_path,
        ),
        reference_date=settings.reference_date,
    )


@lru_cache(maxsize=1)
def load_data() -> DataBundle:
    """Load and transform datasets for analytical use."""

    settings = get_settings()

    if _has_real_sales_dataset():
        reference_date = _resolve_sales_reference_date()
        raw_views = _read_real_sales_raw_views()
        crm = transform_sales_dataset(
            sales_pipeline=raw_views["sales_pipeline"],
            accounts=raw_views["accounts"],
            products=raw_views["products"],
            sales_teams=raw_views["sales_teams"],
            reference_date=reference_date,
        )
        subscriptions = (
            transform_subscriptions_dataframe(pd.read_csv(settings.subscriptions_path))
            if settings.subscriptions_path.exists()
            else None
        )
        return DataBundle(
            raw_views=raw_views,
            crm=crm,
            subscriptions=subscriptions,
            reference_date=reference_date,
            source="crm_sales_opportunities",
        )

    ensure_data_files()
    crm_raw = pd.read_csv(settings.crm_path)
    subscriptions = pd.read_csv(settings.subscriptions_path)
    return DataBundle(
        raw_views={"crm": crm_raw, "subscriptions": subscriptions},
        crm=transform_crm_dataframe(crm_raw, settings.reference_date),
        subscriptions=transform_subscriptions_dataframe(subscriptions),
        reference_date=settings.reference_date,
        source="canonical_mock",
    )


def get_reference_date() -> str:
    """Return the active analysis reference date for the loaded dataset."""

    return load_data().reference_date
