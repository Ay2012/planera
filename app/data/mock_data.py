"""Deterministic mock data generation for demo reliability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import random

import pandas as pd

from app.utils.constants import VALID_PLAN_TIERS, VALID_SEGMENTS, VALID_STAGES
from app.utils.dates import parse_date


@dataclass(frozen=True)
class MockDataPaths:
    """Filesystem locations for generated CSV data."""

    crm_path: Path
    subscriptions_path: Path


def _segment_owner(segment: str) -> str:
    mapping = {
        "SMB": "Avery",
        "Mid-Market": "Jordan",
        "Enterprise": "Casey",
    }
    return mapping[segment]


def generate_mock_data(paths: MockDataPaths, reference_date: str) -> None:
    """Generate deterministic CSVs if they do not already exist."""

    paths.crm_path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    ref_date = parse_date(reference_date)

    crm_rows: list[dict[str, object]] = []
    account_ids = [f"ACC-{idx:03d}" for idx in range(1, 91)]
    deal_counter = 1

    for account_id in account_ids:
        segment = VALID_SEGMENTS[(int(account_id.split("-")[1]) - 1) % len(VALID_SEGMENTS)]
        owner = _segment_owner(segment)
        deal_value_base = {"SMB": 15000, "Mid-Market": 42000, "Enterprise": 98000}[segment]

        for weeks_back in range(8):
            close_date = ref_date - timedelta(days=weeks_back * 7 + rng.randint(0, 5))
            status = "won" if rng.random() > 0.22 else "lost"
            stage = "Closed Won" if status == "won" else "Closed Lost"

            if close_date >= ref_date - timedelta(days=6):
                cycle_days = {"SMB": 28, "Mid-Market": 20, "Enterprise": 18}[segment] + rng.randint(0, 4)
            elif close_date >= ref_date - timedelta(days=13):
                cycle_days = {"SMB": 19, "Mid-Market": 18, "Enterprise": 17}[segment] + rng.randint(0, 3)
            else:
                cycle_days = {"SMB": 18, "Mid-Market": 19, "Enterprise": 20}[segment] + rng.randint(0, 5)

            created_date = close_date - timedelta(days=cycle_days)
            crm_rows.append(
                {
                    "deal_id": f"D-{deal_counter:04d}",
                    "account_id": account_id,
                    "owner": owner,
                    "segment": segment,
                    "stage": stage,
                    "created_date": created_date.isoformat(),
                    "stage_entered_date": (close_date - timedelta(days=rng.randint(1, 5))).isoformat(),
                    "close_date": close_date.isoformat(),
                    "deal_value": deal_value_base + rng.randint(-5000, 8000),
                    "status": status,
                }
            )
            deal_counter += 1

        open_stage = "Stage 2" if segment == "SMB" and rng.random() > 0.35 else rng.choice(VALID_STAGES[:4])
        age_days = rng.randint(16, 28) if open_stage == "Stage 2" and segment == "SMB" else rng.randint(4, 15)
        created_date = ref_date - timedelta(days=age_days + rng.randint(3, 12))
        crm_rows.append(
            {
                "deal_id": f"D-{deal_counter:04d}",
                "account_id": account_id,
                "owner": owner,
                "segment": segment,
                "stage": open_stage,
                "created_date": created_date.isoformat(),
                "stage_entered_date": (ref_date - timedelta(days=age_days)).isoformat(),
                "close_date": "",
                "deal_value": deal_value_base + rng.randint(-6000, 9000),
                "status": "open",
            }
        )
        deal_counter += 1

    subscriptions_rows: list[dict[str, object]] = []
    for idx, account_id in enumerate(account_ids, start=1):
        plan_tier = VALID_PLAN_TIERS[(idx - 1) % len(VALID_PLAN_TIERS)]
        start_date = ref_date - timedelta(days=240 + (idx % 50))
        churned = 1 if plan_tier == "Starter" and idx % 5 == 0 else 0
        subscription_end = (ref_date - timedelta(days=idx % 20)).isoformat() if churned else ""
        subscriptions_rows.append(
            {
                "account_id": account_id,
                "plan_tier": plan_tier,
                "subscription_start": start_date.isoformat(),
                "subscription_end": subscription_end,
                "churned": churned,
                "revenue": {"Starter": 1200, "Growth": 4800, "Enterprise": 14000}[plan_tier] + rng.randint(-200, 600),
            }
        )

    pd.DataFrame(crm_rows).to_csv(paths.crm_path, index=False)
    pd.DataFrame(subscriptions_rows).to_csv(paths.subscriptions_path, index=False)
