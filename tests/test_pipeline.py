"""Tests for ETL transform and data quality layers."""
from __future__ import annotations

import pandas as pd
import pytest

from etl.quality import check_duplicates, check_nulls, run_quality_checks
from etl.transform import coerce_dates, derive_fact_metrics, drop_invalid_rows

# ── Transform ─────────────────────────────────────────────────────────────────


def test_coerce_dates_converts_strings() -> None:
    df = pd.DataFrame({"order_date": ["2024-01-01", "2024-06-15"]})
    result = coerce_dates(df, ["order_date"])
    assert pd.api.types.is_datetime64_any_dtype(result["order_date"])


def test_coerce_dates_invalid_values_become_nat() -> None:
    df = pd.DataFrame({"order_date": ["2024-01-01", "not-a-date", None]})
    result = coerce_dates(df, ["order_date"])
    assert result["order_date"].isna().sum() == 2


def test_coerce_dates_ignores_missing_column() -> None:
    df = pd.DataFrame({"other_col": [1, 2, 3]})
    result = coerce_dates(df, ["order_date"])  # column absent — should not raise
    assert "other_col" in result.columns


def test_drop_invalid_rows_removes_nulls() -> None:
    df = pd.DataFrame(
        {"order_id": ["O1", None, "O3"], "customer_id": ["C1", "C2", "C3"]}
    )
    result = drop_invalid_rows(df, ["order_id"])
    assert len(result) == 2
    assert result["order_id"].notna().all()


def test_drop_invalid_rows_keeps_valid_rows() -> None:
    df = pd.DataFrame({"order_id": ["O1", "O2"], "product_id": ["P1", "P2"]})
    result = drop_invalid_rows(df, ["order_id", "product_id"])
    assert len(result) == 2


def test_derive_fact_revenue() -> None:
    orders = pd.DataFrame(
        {
            "order_id": ["O1"],
            "product_id": ["P1"],
            "quantity": [3],
            "ship_date": [pd.NaT],
            "target_ship_date": [pd.NaT],
            "delivery_date": [pd.NaT],
            "order_date": pd.to_datetime(["2024-01-01"]),
        }
    )
    products = pd.DataFrame(
        {"product_id": ["P1"], "unit_price": [10.0], "unit_cost": [6.0], "category": ["X"]}
    )
    fact = derive_fact_metrics(orders, products)
    assert fact.loc[0, "revenue"] == pytest.approx(30.0)


def test_derive_fact_cogs_and_gross_margin() -> None:
    orders = pd.DataFrame(
        {
            "order_id": ["O1"],
            "product_id": ["P1"],
            "quantity": [4],
            "ship_date": [pd.NaT],
            "target_ship_date": [pd.NaT],
            "delivery_date": [pd.NaT],
            "order_date": pd.to_datetime(["2024-01-01"]),
        }
    )
    products = pd.DataFrame(
        {"product_id": ["P1"], "unit_price": [20.0], "unit_cost": [12.0], "category": ["X"]}
    )
    fact = derive_fact_metrics(orders, products)
    assert fact.loc[0, "cogs"] == pytest.approx(48.0)
    assert fact.loc[0, "gross_margin"] == pytest.approx(32.0)


def test_derive_on_time_ship_flag_when_on_time() -> None:
    orders = pd.DataFrame(
        {
            "order_id": ["O1"],
            "product_id": ["P1"],
            "quantity": [1],
            "order_date": pd.to_datetime(["2024-01-01"]),
            "target_ship_date": pd.to_datetime(["2024-01-05"]),
            "ship_date": pd.to_datetime(["2024-01-04"]),
            "delivery_date": pd.to_datetime(["2024-01-07"]),
        }
    )
    products = pd.DataFrame(
        {"product_id": ["P1"], "unit_price": [1.0], "unit_cost": [0.5], "category": ["X"]}
    )
    fact = derive_fact_metrics(orders, products)
    assert fact.loc[0, "on_time_ship"] == 1


def test_derive_on_time_ship_flag_when_late() -> None:
    orders = pd.DataFrame(
        {
            "order_id": ["O1"],
            "product_id": ["P1"],
            "quantity": [1],
            "order_date": pd.to_datetime(["2024-01-01"]),
            "target_ship_date": pd.to_datetime(["2024-01-03"]),
            "ship_date": pd.to_datetime(["2024-01-06"]),
            "delivery_date": pd.to_datetime(["2024-01-08"]),
        }
    )
    products = pd.DataFrame(
        {"product_id": ["P1"], "unit_price": [1.0], "unit_cost": [0.5], "category": ["X"]}
    )
    fact = derive_fact_metrics(orders, products)
    assert fact.loc[0, "on_time_ship"] == 0


def test_derive_cycle_time_days() -> None:
    orders = pd.DataFrame(
        {
            "order_id": ["O1"],
            "product_id": ["P1"],
            "quantity": [1],
            "order_date": pd.to_datetime(["2024-01-01"]),
            "target_ship_date": pd.to_datetime(["2024-01-03"]),
            "ship_date": pd.to_datetime(["2024-01-03"]),
            "delivery_date": pd.to_datetime(["2024-01-06"]),
        }
    )
    products = pd.DataFrame(
        {"product_id": ["P1"], "unit_price": [1.0], "unit_cost": [0.5], "category": ["X"]}
    )
    fact = derive_fact_metrics(orders, products)
    assert fact.loc[0, "cycle_time_days"] == 5


# ── Data Quality ──────────────────────────────────────────────────────────────


def test_quality_null_check_passes() -> None:
    df = pd.DataFrame({"order_id": ["O1", "O2"], "product_id": ["P1", "P2"]})
    report = check_nulls(df, ["order_id", "product_id"])
    assert report.passed is True
    assert report.issues == []


def test_quality_null_check_detects_nulls() -> None:
    df = pd.DataFrame({"order_id": ["O1", None], "product_id": ["P1", "P2"]})
    report = check_nulls(df, ["order_id"])
    assert report.passed is False
    assert len(report.issues) == 1
    assert "order_id" in report.issues[0]


def test_quality_duplicate_check_passes() -> None:
    df = pd.DataFrame({"order_id": ["O1", "O2"], "product_id": ["P1", "P2"]})
    report = check_duplicates(df, ["order_id", "product_id"])
    assert report.passed is True


def test_quality_duplicate_check_detects_duplicates() -> None:
    df = pd.DataFrame({"order_id": ["O1", "O1"], "product_id": ["P1", "P1"]})
    report = check_duplicates(df, ["order_id", "product_id"])
    assert report.passed is False
    assert "1 duplicate" in report.issues[0]


def test_quality_run_all_fails_on_combined_issues() -> None:
    df = pd.DataFrame(
        {"order_id": [None, "O1", "O1"], "product_id": ["P1", "P2", "P2"]}
    )
    report = run_quality_checks(df, required_cols=["order_id"], key_cols=["order_id", "product_id"])
    assert report.passed is False
    assert len(report.issues) == 2
