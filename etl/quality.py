"""Data quality checks: null detection and duplicate identification."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class QualityReport:
    passed: bool
    issues: list[str] = field(default_factory=list)


def check_nulls(df: pd.DataFrame, required_cols: list[str]) -> QualityReport:
    """Report any nulls in required_cols."""
    issues = []
    for col in required_cols:
        n = int(df[col].isna().sum())
        if n > 0:
            issues.append(f"'{col}' has {n} null value(s)")
    return QualityReport(passed=len(issues) == 0, issues=issues)


def check_duplicates(df: pd.DataFrame, key_cols: list[str]) -> QualityReport:
    """Report duplicate rows based on key_cols."""
    n_dupes = int(df.duplicated(subset=key_cols).sum())
    issues = []
    if n_dupes > 0:
        issues.append(f"{n_dupes} duplicate row(s) on key {key_cols}")
    return QualityReport(passed=n_dupes == 0, issues=issues)


def run_quality_checks(
    df: pd.DataFrame,
    required_cols: list[str],
    key_cols: list[str],
) -> QualityReport:
    """Run null and duplicate checks; return a combined QualityReport."""
    reports = [
        check_nulls(df, required_cols),
        check_duplicates(df, key_cols),
    ]
    all_issues = [issue for r in reports for issue in r.issues]
    return QualityReport(passed=all(r.passed for r in reports), issues=all_issues)
