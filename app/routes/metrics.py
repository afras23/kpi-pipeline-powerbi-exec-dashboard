from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.kpi import KPISummary
from app.services.mart import get_kpi_summary

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=KPISummary)
def metrics() -> KPISummary:
    try:
        return get_kpi_summary()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Mart not available — run ETL first") from exc
