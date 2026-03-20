"""Shared pytest fixtures."""
from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture()
def fact_df() -> pd.DataFrame:
    """Minimal fact_order_line fixture with 4 rows — 3 active, 1 cancelled.

    Expected KPI values (non-cancelled rows 0-2):
        total_revenue       = 100 + 50 + 200 = 350.0
        total_cogs          = 60  + 30 + 120 = 210.0
        gross_margin        = 40  + 20 + 80  = 140.0
        gross_margin_pct    = 140 / 350 * 100 = 40.0
        order_count         = 2  (distinct: O1, O2)
        on_time_ship_rate   = 2 / 3 * 100 ≈ 66.67
        avg_cycle_time      = (4 + 4 + 3) / 3 ≈ 3.67
        cancellation_rate   = 1 / 4 * 100 = 25.0
    """
    return pd.DataFrame(
        {
            "order_id": ["O1", "O1", "O2", "O3"],
            "order_date": pd.to_datetime(["2024-01-01"] * 4),
            "delivery_date": pd.to_datetime(
                ["2024-01-05", "2024-01-05", "2024-01-04", pd.NaT]
            ),
            "is_cancelled": [0, 0, 0, 1],
            "revenue": [100.0, 50.0, 200.0, 80.0],
            "cogs": [60.0, 30.0, 120.0, 50.0],
            "gross_margin": [40.0, 20.0, 80.0, 30.0],
            "on_time_ship": [1, 1, 0, 0],
            "cycle_time_days": [4.0, 4.0, 3.0, None],
        }
    )
