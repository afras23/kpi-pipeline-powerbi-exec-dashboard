"""KPI registry — single source of truth for all metric definitions.

Each KPIDefinition specifies *what* to compute; the engine handles *how*.
To add a KPI, append an entry to REGISTRY — no engine changes needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class KPIDefinition:
    name: str
    label: str
    agg: Literal["sum", "mean", "count_distinct", "ratio"]
    # For sum / mean / count_distinct
    column: str | None = None
    # For ratio: numerator column (summed), denominator column (summed) or None = row count
    numerator: str | None = None
    denominator: str | None = None
    # Optional pandas query string applied before aggregation
    filter_expr: str | None = None
    # Multiply the result (e.g. 100.0 for percentage ratios)
    scale: float = field(default=1.0, compare=False)


REGISTRY: list[KPIDefinition] = [
    KPIDefinition(
        name="total_revenue",
        label="Total Revenue",
        agg="sum",
        column="revenue",
        filter_expr="is_cancelled == 0",
    ),
    KPIDefinition(
        name="total_cogs",
        label="Total COGS",
        agg="sum",
        column="cogs",
        filter_expr="is_cancelled == 0",
    ),
    KPIDefinition(
        name="gross_margin",
        label="Gross Margin",
        agg="sum",
        column="gross_margin",
        filter_expr="is_cancelled == 0",
    ),
    KPIDefinition(
        name="gross_margin_pct",
        label="Gross Margin %",
        agg="ratio",
        numerator="gross_margin",
        denominator="revenue",
        filter_expr="is_cancelled == 0",
        scale=100.0,
    ),
    KPIDefinition(
        name="order_count",
        label="Total Orders",
        agg="count_distinct",
        column="order_id",
        filter_expr="is_cancelled == 0",
    ),
    KPIDefinition(
        name="on_time_ship_rate",
        label="On-Time Ship Rate %",
        agg="ratio",
        numerator="on_time_ship",
        denominator=None,  # use filtered row count as denominator
        filter_expr="is_cancelled == 0",
        scale=100.0,
    ),
    KPIDefinition(
        name="avg_cycle_time",
        label="Avg Cycle Time (days)",
        agg="mean",
        column="cycle_time_days",
        filter_expr="is_cancelled == 0",
    ),
    KPIDefinition(
        name="cancellation_rate",
        label="Cancellation Rate %",
        agg="ratio",
        numerator="is_cancelled",
        denominator=None,
        filter_expr=None,
        scale=100.0,
    ),
]

REGISTRY_MAP: dict[str, KPIDefinition] = {kpi.name: kpi for kpi in REGISTRY}
