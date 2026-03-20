from __future__ import annotations

import logging

from app.config import settings
from app.core.database import get_engine
from etl.pipeline import run

logger = logging.getLogger(__name__)


def run_etl() -> None:
    """Run the full ETL pipeline against the configured database."""
    engine = get_engine()
    run(settings.raw_data_dir, engine)
    logger.info("ETL complete.")
