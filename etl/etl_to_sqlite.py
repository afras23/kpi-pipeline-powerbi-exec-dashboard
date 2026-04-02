"""Standalone SQLite ETL runner — thin CLI wrapper around etl.pipeline."""

from __future__ import annotations

import os

from sqlalchemy import create_engine

from etl.pipeline import run

DB_PATH = "data/processed/kpi_mart.db"
RAW_DIR = "data/raw"


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}")
    run(RAW_DIR, engine)
    print(f"✅ SQLite mart built at: {DB_PATH}")
    print("Tables: dim_customer, dim_product, dim_date, fact_order_line")


if __name__ == "__main__":
    main()
