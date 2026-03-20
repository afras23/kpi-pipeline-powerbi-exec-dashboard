from __future__ import annotations

from pydantic import BaseModel


class RevenueMetric(BaseModel):
    total_revenue: float
    total_cogs: float
    gross_margin: float


class OrderMetric(BaseModel):
    total_orders: int
    on_time_ship_rate: float  # percentage, e.g. 87.4
    avg_cycle_time_days: float | None


class KPISummary(BaseModel):
    revenue: RevenueMetric
    orders: OrderMetric
