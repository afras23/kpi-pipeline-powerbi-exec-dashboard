"""Load: persist transformed mart tables to the configured database."""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def load_mart(
    engine: Engine,
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_date: pd.DataFrame,
    fact_order_line: pd.DataFrame,
    if_exists: str = "replace",
) -> None:
    """Write all mart tables inside a single transaction."""
    tables: dict[str, pd.DataFrame] = {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_date": dim_date,
        "fact_order_line": fact_order_line,
    }
    with engine.begin() as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, index=False, if_exists=if_exists)
            logger.info("Loaded %s: %d rows", name, len(df))
