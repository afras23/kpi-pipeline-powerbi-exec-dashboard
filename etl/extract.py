"""Extract: load raw data from CSV sources into DataFrames."""

from __future__ import annotations

import os

import pandas as pd

SOURCES = ("customers", "products", "order_lines")


def load_source(name: str, raw_dir: str) -> pd.DataFrame:
    """Load a named CSV source from raw_dir.

    Args:
        name: Source name without extension (e.g. 'customers').
        raw_dir: Directory containing the CSV files.
    """
    path = os.path.join(raw_dir, f"{name}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source not found: {path}")
    return pd.read_csv(path)


def extract_all(raw_dir: str) -> dict[str, pd.DataFrame]:
    """Extract all required sources and return as a keyed dict."""
    return {name: load_source(name, raw_dir) for name in SOURCES}
