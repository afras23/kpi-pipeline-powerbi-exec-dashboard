"""Pipeline: orchestrates extract → quality check → transform → load."""
from __future__ import annotations

import logging

from sqlalchemy.engine import Engine

from etl.extract import extract_all
from etl.load import load_mart
from etl.quality import run_quality_checks
from etl.transform import transform

logger = logging.getLogger(__name__)

_ORDER_LINE_REQUIRED = ["order_id", "customer_id", "product_id", "order_date"]
_ORDER_LINE_KEYS = ["order_id", "product_id"]


def run(raw_dir: str, engine: Engine) -> None:
    """Full ETL pipeline: extract → quality check → transform → load."""
    sources = extract_all(raw_dir)

    report = run_quality_checks(
        sources["order_lines"],
        required_cols=_ORDER_LINE_REQUIRED,
        key_cols=_ORDER_LINE_KEYS,
    )
    if not report.passed:
        logger.warning("Data quality issues detected: %s", report.issues)

    dim_customer, dim_product, dim_date, fact = transform(
        sources["customers"],
        sources["products"],
        sources["order_lines"],
    )

    load_mart(engine, dim_customer, dim_product, dim_date, fact)
    logger.info("Pipeline complete.")
