from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Paths:
    raw_dir: str = "data/raw"
    db_path: str = "data/processed/kpi_mart.db"


def read_csv(name: str, raw_dir: str) -> pd.DataFrame:
    path = os.path.join(raw_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def coerce_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce")
    return out


def build_dim_date(min_date: pd.Timestamp, max_date: pd.Timestamp) -> pd.DataFrame:
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


def main() -> None:
    paths = Paths()
    os.makedirs(os.path.dirname(paths.db_path), exist_ok=True)

    customers = read_csv("customers.csv", paths.raw_dir)
    products = read_csv("products.csv", paths.raw_dir)
    order_lines = read_csv("order_lines.csv", paths.raw_dir)

    # Clean / types
    order_lines = coerce_dates(order_lines, ["order_date", "target_ship_date", "ship_date", "delivery_date"])
    customers["created_at"] = pd.to_datetime(customers["created_at"], errors="coerce")

    # Drop cancelled rows? No: keep flag, filter in measures. But ensure keys are valid.
    order_lines = order_lines.dropna(subset=["order_id", "customer_id", "product_id", "order_date"])

    # Join product price/cost into fact to simplify Power BI (denormalised fact is fine for portfolio demo)
    products_small = products[["product_id", "unit_price", "unit_cost", "category"]].copy()
    fact = order_lines.merge(products_small, on="product_id", how="left", validate="m:1")

    # Add derived columns
    fact["revenue"] = fact["quantity"] * fact["unit_price"]
    fact["cogs"] = fact["quantity"] * fact["unit_cost"]
    fact["gross_margin"] = fact["revenue"] - fact["cogs"]

    # On-time shipping flag (exclude cancelled later)
    fact["on_time_ship"] = (
        (fact["ship_date"].notna())
        & (fact["target_ship_date"].notna())
        & (fact["ship_date"] <= fact["target_ship_date"])
    ).astype(int)

    # Cycle time in days (requires delivery)
    fact["cycle_time_days"] = (fact["delivery_date"] - fact["order_date"]).dt.days

    # Dim date range from order_date
    min_d = fact["order_date"].min()
    max_d = fact["order_date"].max()
    dim_date = build_dim_date(min_d.normalize(), max_d.normalize())

    # Persist to SQLite
    if os.path.exists(paths.db_path):
        os.remove(paths.db_path)

    with sqlite3.connect(paths.db_path) as conn:
        customers.to_sql("dim_customer", conn, index=False)
        products.to_sql("dim_product", conn, index=False)
        dim_date.to_sql("dim_date", conn, index=False)
        fact.to_sql("fact_order_line", conn, index=False)

    print("✅ SQLite mart built at:", paths.db_path)
    print("Tables: dim_customer, dim_product, dim_date, fact_order_line")


if __name__ == "__main__":
    main()
