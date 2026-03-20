from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routes import health, metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.run_etl_on_startup:
        logger.info("RUN_ETL_ON_STARTUP=true — running ETL pipeline...")
        from app.services.etl import run_etl

        run_etl()
        logger.info("ETL complete.")
    yield


app = FastAPI(
    title="KPI Pipeline API",
    description="Operational endpoints for the KPI data mart.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(metrics.router)
