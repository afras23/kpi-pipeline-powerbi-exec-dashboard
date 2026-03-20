from __future__ import annotations

from sqlalchemy import text

from app.core.database import get_engine
from app.models.kpi import KPISummary, OrderMetric, RevenueMetric


def get_kpi_summary() -> KPISummary:
    """Query the mart and return aggregated KPI figures."""
    engine = get_engine()

    with engine.connect() as conn:
        rev_row = conn.execute(
            text("""
                SELECT
                    SUM(revenue)      AS total_revenue,
                    SUM(cogs)         AS total_cogs,
                    SUM(gross_margin) AS gross_margin
                FROM fact_order_line
                WHERE is_cancelled = 0
            """)
        ).fetchone()
        if rev_row is None:
            raise RuntimeError("fact_order_line table is empty or missing")

        order_row = conn.execute(
            text("""
                SELECT
                    COUNT(DISTINCT order_id)             AS total_orders,
                    AVG(CAST(on_time_ship AS FLOAT))     AS on_time_rate,
                    AVG(cycle_time_days)                 AS avg_cycle_time
                FROM fact_order_line
                WHERE is_cancelled = 0
            """)
        ).fetchone()
        if order_row is None:
            raise RuntimeError("fact_order_line table is empty or missing")

    return KPISummary(
        revenue=RevenueMetric(
            total_revenue=round(rev_row.total_revenue or 0.0, 2),
            total_cogs=round(rev_row.total_cogs or 0.0, 2),
            gross_margin=round(rev_row.gross_margin or 0.0, 2),
        ),
        orders=OrderMetric(
            total_orders=order_row.total_orders or 0,
            on_time_ship_rate=round((order_row.on_time_rate or 0.0) * 100, 2),
            avg_cycle_time_days=(
                round(order_row.avg_cycle_time, 2) if order_row.avg_cycle_time is not None else None
            ),
        ),
    )
