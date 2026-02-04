# Refresh Runbook (Local)

## Purpose
Rebuild the dataset and SQLite mart, then refresh Power BI visuals.

## Steps
1) Activate environment:
   - macOS/Linux: `source .venv/bin/activate`
2) Regenerate raw CSVs:
   - `python etl/generate_synthetic_data.py`
3) Rebuild SQLite mart:
   - `python etl/etl_to_sqlite.py`
4) Run checks:
   - `pytest -q`
5) In Power BI Desktop:
   - Click **Refresh**.

## Notes
- The SQLite file is located at `data/processed/kpi_mart.db`.
- If you change the path, update the Power BI data source settings accordingly.
