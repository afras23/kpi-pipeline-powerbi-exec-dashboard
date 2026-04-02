"""KPI engine: compute metrics from a fact DataFrame using the registry."""

from __future__ import annotations

import pandas as pd

from kpi.definitions import REGISTRY, REGISTRY_MAP, KPIDefinition


def _apply_filter(df: pd.DataFrame, filter_expr: str | None) -> pd.DataFrame:
    if filter_expr:
        return df.query(filter_expr)
    return df


def compute(df: pd.DataFrame, kpi: KPIDefinition) -> float | None:
    """Compute a single KPI against the fact DataFrame.

    Returns None when the filtered dataset is empty or the denominator is zero.
    """
    filtered = _apply_filter(df, kpi.filter_expr)
    if filtered.empty:
        return None

    if kpi.agg == "sum":
        assert kpi.column is not None
        return float(filtered[kpi.column].sum())

    if kpi.agg == "mean":
        assert kpi.column is not None
        val = filtered[kpi.column].mean()
        return None if pd.isna(val) else float(val)

    if kpi.agg == "count_distinct":
        assert kpi.column is not None
        return float(filtered[kpi.column].nunique())

    if kpi.agg == "ratio":
        assert kpi.numerator is not None
        num = float(filtered[kpi.numerator].sum())
        denom = float(filtered[kpi.denominator].sum()) if kpi.denominator else float(len(filtered))
        if denom == 0:
            return None
        return num / denom * kpi.scale

    raise ValueError(f"Unknown aggregation: '{kpi.agg}'")


def compute_by_name(df: pd.DataFrame, name: str) -> float | None:
    """Compute a single KPI by its registry name."""
    if name not in REGISTRY_MAP:
        raise KeyError(f"Unknown KPI: '{name}'. Available: {sorted(REGISTRY_MAP)}")
    return compute(df, REGISTRY_MAP[name])


def compute_all(df: pd.DataFrame) -> dict[str, float | None]:
    """Compute every registered KPI and return as a name → value dict."""
    return {kpi.name: compute(df, kpi) for kpi in REGISTRY}
