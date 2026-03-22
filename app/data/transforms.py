"""Data transformations for CRM and subscription CSVs."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from app.utils.dates import parse_date


def bucket_deal_age(days: int) -> str:
    """Convert a deal age in days into a stable bucket."""

    if days <= 7:
        return "0-7"
    if days <= 14:
        return "8-14"
    if days <= 30:
        return "15-30"
    return "31+"


def derive_segment(employees: float | int | None, revenue: float | int | None) -> str:
    """Derive a GTM segment from account size proxies."""

    employee_count = 0 if pd.isna(employees) else int(employees)
    revenue_value = 0.0 if pd.isna(revenue) else float(revenue)

    if employee_count >= 5000 or revenue_value >= 3000:
        return "Enterprise"
    if employee_count >= 1000 or revenue_value >= 800:
        return "Mid-Market"
    return "SMB"


def normalize_product_name(value: str) -> str:
    """Normalize product labels across source files."""

    normalized = value.strip()
    mapping = {"GTXPro": "GTX Pro"}
    return mapping.get(normalized, normalized)


def map_stage(raw_stage: str) -> tuple[str, str]:
    """Map raw CRM stage values to normalized stage and status."""

    stage = raw_stage.strip()
    if stage == "Won":
        return "Closed Won", "won"
    if stage == "Lost":
        return "Closed Lost", "lost"
    if stage == "Engaging":
        return "Stage 2", "open"
    return "Stage 1", "open"


def map_plan_tier(product_name: str, sales_price: float | int | None) -> str:
    """Derive a plan tier from product metadata."""

    normalized = normalize_product_name(product_name).lower()
    price = 0.0 if pd.isna(sales_price) else float(sales_price)
    if "gtk" in normalized or price >= 10000:
        return "Enterprise"
    if "pro" in normalized or "advanced" in normalized or price >= 3000:
        return "Growth"
    return "Starter"


def transform_crm_dataframe(df: pd.DataFrame, reference_date: str) -> pd.DataFrame:
    """Add analytics-friendly columns to the CRM dataset."""

    crm = df.copy()
    ref_date = parse_date(reference_date)

    crm["created_date"] = pd.to_datetime(crm["created_date"])
    crm["stage_entered_date"] = pd.to_datetime(crm["stage_entered_date"])
    crm["close_date"] = pd.to_datetime(crm["close_date"], errors="coerce")
    crm["deal_value"] = pd.to_numeric(crm["deal_value"], errors="coerce").fillna(0.0)

    effective_close = crm["close_date"].fillna(pd.Timestamp(ref_date))
    crm["pipeline_velocity_days"] = (effective_close - crm["created_date"]).dt.days
    crm["deal_age_days"] = (pd.Timestamp(ref_date) - crm["created_date"]).dt.days
    crm["stage_age_days"] = (pd.Timestamp(ref_date) - crm["stage_entered_date"]).dt.days
    crm["deal_age_bucket"] = crm["deal_age_days"].apply(bucket_deal_age)

    current_start = pd.Timestamp(ref_date - timedelta(days=6))
    previous_start = pd.Timestamp(ref_date - timedelta(days=13))
    previous_end = pd.Timestamp(ref_date - timedelta(days=7))
    crm["current_period"] = crm["close_date"].between(current_start, pd.Timestamp(ref_date), inclusive="both")
    crm["previous_period"] = crm["close_date"].between(previous_start, previous_end, inclusive="both")
    return crm


def transform_subscriptions_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize subscription dataset types."""

    subs = df.copy()
    subs["subscription_start"] = pd.to_datetime(subs["subscription_start"])
    subs["subscription_end"] = pd.to_datetime(subs["subscription_end"], errors="coerce")
    subs["churned"] = pd.to_numeric(subs["churned"], errors="coerce").fillna(0).astype(int)
    subs["revenue"] = pd.to_numeric(subs["revenue"], errors="coerce").fillna(0.0)
    return subs


def transform_sales_dataset(
    sales_pipeline: pd.DataFrame,
    accounts: pd.DataFrame,
    products: pd.DataFrame,
    sales_teams: pd.DataFrame,
    reference_date: str,
) -> pd.DataFrame:
    """Transform the CRM+Sales+Opportunities dataset into the app's canonical CRM shape."""

    pipeline = sales_pipeline.copy()
    account_df = accounts.copy()
    product_df = products.copy()
    team_df = sales_teams.copy()

    pipeline["product"] = pipeline["product"].astype(str).map(normalize_product_name)
    product_df["product"] = product_df["product"].astype(str).map(normalize_product_name)

    crm = pipeline.merge(account_df, on="account", how="left")
    crm = crm.merge(product_df, on="product", how="left")
    crm = crm.merge(team_df, on="sales_agent", how="left")

    stage_info = crm["deal_stage"].astype(str).map(map_stage)
    crm["stage"] = stage_info.map(lambda item: item[0])
    crm["status"] = stage_info.map(lambda item: item[1])
    crm["segment"] = crm.apply(lambda row: derive_segment(row.get("employees"), row.get("revenue")), axis=1)
    crm["plan_tier"] = crm.apply(lambda row: map_plan_tier(row.get("product", ""), row.get("sales_price")), axis=1)

    transformed = pd.DataFrame(
        {
            "deal_id": crm["opportunity_id"],
            "account_id": crm["account"],
            "owner": crm["sales_agent"],
            "segment": crm["segment"],
            "stage": crm["stage"],
            "created_date": crm["engage_date"],
            "stage_entered_date": crm["engage_date"],
            "close_date": crm["close_date"],
            "deal_value": crm["close_value"].fillna(crm["sales_price"]).fillna(0.0),
            "status": crm["status"],
            "plan_tier": crm["plan_tier"],
            "manager": crm["manager"],
            "regional_office": crm["regional_office"],
            "sector": crm["sector"],
            "employees": crm["employees"],
            "office_location": crm["office_location"],
        }
    )
    return transform_crm_dataframe(transformed, reference_date)
