from __future__ import annotations

import logging

import pandas as pd

from app.config import settings
from app.core.database import get_engine
from etl.etl_to_sqlite import build_dim_date, coerce_dates, read_csv

logger = logging.getLogger(__name__)


def run_etl() -> None:
    """Load raw CSVs, transform, and write to the configured database."""
    raw_dir = settings.raw_data_dir
    engine = get_engine()

    customers = read_csv("customers.csv", raw_dir)
    products = read_csv("products.csv", raw_dir)
    order_lines = read_csv("order_lines.csv", raw_dir)

    order_lines = coerce_dates(
        order_lines, ["order_date", "target_ship_date", "ship_date", "delivery_date"]
    )
    customers["created_at"] = pd.to_datetime(customers["created_at"], errors="coerce")
    order_lines = order_lines.dropna(
        subset=["order_id", "customer_id", "product_id", "order_date"]
    )

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

    min_date = fact["order_date"].min().normalize()
    max_date = fact["order_date"].max().normalize()
    dim_date = build_dim_date(min_date, max_date)

    with engine.begin() as conn:
        customers.to_sql("dim_customer", conn, index=False, if_exists="replace")
        products.to_sql("dim_product", conn, index=False, if_exists="replace")
        dim_date.to_sql("dim_date", conn, index=False, if_exists="replace")
        fact.to_sql("fact_order_line", conn, index=False, if_exists="replace")

    logger.info(
        "ETL complete — dim_customer=%d dim_product=%d fact_order_line=%d",
        len(customers),
        len(products),
        len(fact),
    )
