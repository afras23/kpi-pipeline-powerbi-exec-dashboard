from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.database import check_db_ready

router = APIRouter(tags=["ops"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict:
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="Database not ready")
    return {"status": "ready"}
