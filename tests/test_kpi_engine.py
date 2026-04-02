"""Tests for the config-driven KPI engine."""

from __future__ import annotations

import pandas as pd
import pytest

from kpi.definitions import REGISTRY
from kpi.engine import compute_all, compute_by_name

# ── KPI correctness ───────────────────────────────────────────────────────────


def test_total_revenue(fact_df: pd.DataFrame) -> None:
    assert compute_by_name(fact_df, "total_revenue") == pytest.approx(350.0)


def test_total_cogs(fact_df: pd.DataFrame) -> None:
    assert compute_by_name(fact_df, "total_cogs") == pytest.approx(210.0)


def test_gross_margin(fact_df: pd.DataFrame) -> None:
    assert compute_by_name(fact_df, "gross_margin") == pytest.approx(140.0)


def test_gross_margin_pct(fact_df: pd.DataFrame) -> None:
    # 140 / 350 * 100 = 40.0
    assert compute_by_name(fact_df, "gross_margin_pct") == pytest.approx(40.0)


def test_order_count_is_distinct(fact_df: pd.DataFrame) -> None:
    # Non-cancelled orders: O1 (×2 lines), O2 → 2 distinct order IDs
    assert compute_by_name(fact_df, "order_count") == pytest.approx(2.0)


def test_on_time_ship_rate(fact_df: pd.DataFrame) -> None:
    # on_time_ship values for non-cancelled rows: [1, 1, 0] → 2/3 * 100
    assert compute_by_name(fact_df, "on_time_ship_rate") == pytest.approx(200 / 3, rel=1e-4)


def test_avg_cycle_time(fact_df: pd.DataFrame) -> None:
    # cycle_time_days for non-cancelled: [4, 4, 3] → mean = 11/3
    assert compute_by_name(fact_df, "avg_cycle_time") == pytest.approx(11 / 3, rel=1e-4)


def test_cancellation_rate(fact_df: pd.DataFrame) -> None:
    # 1 cancelled out of 4 rows → 25.0 %
    assert compute_by_name(fact_df, "cancellation_rate") == pytest.approx(25.0)


# ── Engine behaviour ──────────────────────────────────────────────────────────


def test_compute_all_returns_every_registered_kpi(fact_df: pd.DataFrame) -> None:
    results = compute_all(fact_df)
    assert set(results.keys()) == {kpi.name for kpi in REGISTRY}


def test_compute_by_name_raises_for_unknown_kpi(fact_df: pd.DataFrame) -> None:
    with pytest.raises(KeyError, match="Unknown KPI"):
        compute_by_name(fact_df, "nonexistent_kpi")


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_empty_dataframe_returns_none() -> None:
    empty = pd.DataFrame(
        columns=[
            "order_id",
            "is_cancelled",
            "revenue",
            "cogs",
            "gross_margin",
            "on_time_ship",
            "cycle_time_days",
        ]
    )
    assert compute_by_name(empty, "total_revenue") is None
    assert compute_by_name(empty, "order_count") is None


def test_all_cancelled_returns_none_for_revenue_kpis() -> None:
    all_cancelled = pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "is_cancelled": [1, 1],
            "revenue": [100.0, 200.0],
            "cogs": [60.0, 120.0],
            "gross_margin": [40.0, 80.0],
            "on_time_ship": [0, 0],
            "cycle_time_days": [None, None],
        }
    )
    assert compute_by_name(all_cancelled, "total_revenue") is None
    assert compute_by_name(all_cancelled, "order_count") is None


def test_zero_denominator_returns_none() -> None:
    """gross_margin_pct when all revenue is 0 → denominator is 0 → None."""
    df = pd.DataFrame(
        {
            "order_id": ["O1"],
            "is_cancelled": [0],
            "revenue": [0.0],
            "cogs": [0.0],
            "gross_margin": [0.0],
            "on_time_ship": [1],
            "cycle_time_days": [3.0],
        }
    )
    assert compute_by_name(df, "gross_margin_pct") is None
