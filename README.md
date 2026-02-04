# KPI Pipeline + Power BI Exec Dashboard

## Problem
Many teams still run weekly/monthly reporting in spreadsheets: manual exports, copy/paste, inconsistent KPI definitions, and low trust in numbers.

## Solution (Demo)
This repo shows an end-to-end reporting replacement:
- Synthetic operational dataset (CSV)
- Python ETL builds a refreshable SQLite mart
- A metric logic table defines KPIs as a single source of truth
- Power BI executive dashboard + drilldowns (screenshots)

## Repo Structure
- `/data/raw` synthetic CSV inputs  
- `/data/processed` SQLite mart (generated locally)
- `/etl` data generator + ETL scripts
- `/docs` KPI logic + acceptance checks + refresh runbook
- `/powerbi` exported dashboard screenshots

## How to Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python etl/generate_synthetic_data.py
python etl/etl_to_sqlite.py
pytest -q
