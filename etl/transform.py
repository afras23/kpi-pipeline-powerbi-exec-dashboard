"""Transform: clean, normalise, and derive columns from raw sources."""

from __future__ import annotations

import pandas as pd


def coerce_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Parse string columns to datetime64; unparseable values become NaT."""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce")
    return out


def drop_invalid_rows(df: pd.DataFrame, required_cols: list[str]) -> pd.DataFrame:
    """Drop rows that have a null in any of required_cols."""
    return df.dropna(subset=required_cols).copy()


def derive_fact_metrics(order_lines: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Join product cost/price into the fact table and compute derived columns.

    Derived columns:
        revenue         = quantity × unit_price
        cogs            = quantity × unit_cost
        gross_margin    = revenue − cogs
        on_time_ship    = 1 if shipped on or before target, else 0 (0 for cancelled)
        cycle_time_days = delivery_date − order_date in days (NaN for cancelled)
    """
    products_slim = products[["product_id", "unit_price", "unit_cost", "category"]].copy()
    fact = order_lines.merge(products_slim, on="product_id", how="left", validate="m:1")

    fact["revenue"] = fact["quantity"] * fact["unit_price"]
    fact["cogs"] = fact["quantity"] * fact["unit_cost"]
    fact["gross_margin"] = fact["revenue"] - fact["cogs"]
    fact["on_time_ship"] = (
        fact["ship_date"].notna()
        & fact["target_ship_date"].notna()
        & (fact["ship_date"] <= fact["target_ship_date"])
    ).astype(int)
    fact["cycle_time_days"] = (fact["delivery_date"] - fact["order_date"]).dt.days
    return fact


def build_dim_date(min_date: pd.Timestamp, max_date: pd.Timestamp) -> pd.DataFrame:
    """Build a date dimension spanning min_date to max_date (inclusive)."""
    days = pd.date_range(min_date, max_date, freq="D")
    d = pd.DataFrame({"date": days})
    d["date_key"] = d["date"].dt.strftime("%Y%m%d").astype(int)
    d["year"] = d["date"].dt.year
    d["quarter"] = "Q" + d["date"].dt.quarter.astype(str)
    d["month"] = d["date"].dt.month
    d["month_name"] = d["date"].dt.strftime("%b")
    d["week"] = d["date"].dt.isocalendar().week.astype(int)
    d["day_name"] = d["date"].dt.strftime("%a")
    return d


def transform(
    customers: pd.DataFrame,
    products: pd.DataFrame,
    order_lines: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Full transform pipeline.

    Returns:
        (dim_customer, dim_product, dim_date, fact_order_line)
    """
    order_lines = coerce_dates(
        order_lines, ["order_date", "target_ship_date", "ship_date", "delivery_date"]
    )
    customers = customers.copy()
    customers["created_at"] = pd.to_datetime(customers["created_at"], errors="coerce")

    order_lines = drop_invalid_rows(
        order_lines, ["order_id", "customer_id", "product_id", "order_date"]
    )

    fact = derive_fact_metrics(order_lines, products)

    min_date = fact["order_date"].min().normalize()
    max_date = fact["order_date"].max().normalize()
    dim_date = build_dim_date(min_date, max_date)

    return customers, products, dim_date, fact
