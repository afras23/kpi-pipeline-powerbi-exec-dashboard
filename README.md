# KPI Pipeline

A backend data pipeline that extracts raw operational data from CSV sources, runs quality checks, transforms it into a structured analytical mart, and exposes KPI metrics via a REST API. The mart is consumed by Power BI for executive reporting.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Problem Context](#2-problem-context)
3. [Pipeline Architecture](#3-pipeline-architecture)
4. [Data Processing Flow](#4-data-processing-flow)
5. [KPI Engine Design](#5-kpi-engine-design)
6. [Data Quality & Reliability](#6-data-quality--reliability)
7. [Failure Modes](#7-failure-modes)
8. [Running the Pipeline](#8-running-the-pipeline)
9. [Project Structure](#9-project-structure)
10. [CI](#10-ci)

---

## 1. System Overview

This system ingests raw operational data (customers, products, order lines) and produces a structured dimensional mart and a set of validated KPI metrics. The mart is the source of record for Power BI dashboards used in executive reporting.

**What it does:**

- Extracts CSV files from a configured raw data directory
- Validates required fields and checks for duplicate records before transformation
- Transforms order lines into a denormalised fact table with derived metrics
- Loads four mart tables into either SQLite (local) or Postgres (production) inside a single transaction
- Exposes aggregated KPI figures via `GET /metrics`
- Provides `/health` and `/health/ready` endpoints for operational monitoring

**What it does not do:**

- Schedule or trigger its own runs — no scheduler is embedded
- Send alerts on quality failures — issues are logged as warnings; the pipeline continues
- Maintain historical snapshots of the mart — each run replaces all four tables

---

## 2. Problem Context

The reporting workflow this system replaces relied on manually maintained spreadsheets. Analysts pulled data from source systems, applied transformations by hand, and forwarded files to stakeholders. This introduced recurring problems:

- **Inconsistent metric definitions.** Revenue, gross margin, and on-time delivery were calculated differently depending on who produced the report and when.
- **No auditability.** There was no record of which data version produced a given report. Recalculating historical figures required locating the right spreadsheet version.
- **Silent failures.** A change in the upstream data format would produce wrong numbers rather than an error.
- **Manual effort.** Preparing a weekly KPI pack required several hours of analyst time and was prone to copy-paste errors.

This pipeline addresses those problems by codifying all transformations as deterministic Python functions, defining every KPI in a single versioned registry, and making each run fully reproducible from the same input files.

---

## 3. Pipeline Architecture

```
CSV files (data/raw/)
        │
        ▼
  ┌─────────────┐
  │   Extract   │  etl/extract.py
  │             │  Loads customers.csv, products.csv, order_lines.csv
  │             │  into DataFrames. Raises FileNotFoundError if any
  │             │  source is absent.
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │   Quality   │  etl/quality.py
  │   Checks    │  Checks order_lines for nulls in required fields and
  │             │  duplicate (order_id, product_id) pairs. Issues are
  │             │  logged as warnings; the pipeline continues.
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Transform  │  etl/transform.py
  │             │  Coerces dates, drops rows with missing required keys,
  │             │  joins product cost/price, computes derived columns,
  │             │  builds dim_date.
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │    Load     │  etl/load.py
  │             │  Writes dim_customer, dim_product, dim_date,
  │             │  fact_order_line to the configured database in a
  │             │  single transaction (if_exists="replace").
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  KPI Layer  │  kpi/engine.py + app/services/mart.py
  │             │  Computes metrics from the fact table. Accessible
  │             │  as a Python function (compute_all) or via the API
  │             │  (GET /metrics).
  └─────────────┘
```

The pipeline entry point is `etl/pipeline.run(raw_dir, engine)`. The SQLAlchemy engine determines the target database — the pipeline itself is database-agnostic.

---

## 4. Data Processing Flow

### 4.1 Sources

Three CSV files are expected in `RAW_DATA_DIR` (default: `data/raw/`):

| File | Key columns |
|---|---|
| `customers.csv` | `customer_id`, `customer_name`, `segment`, `country`, `created_at` |
| `products.csv` | `product_id`, `product_name`, `category`, `unit_price`, `unit_cost`, `is_active` |
| `order_lines.csv` | `order_id`, `order_date`, `customer_id`, `product_id`, `quantity`, `channel`, `region`, `target_ship_date`, `ship_date`, `delivery_date`, `is_cancelled` |

`order_lines.csv` contains one row per product within an order. A single `order_id` appears across multiple rows.

`data/raw/` is populated by running `etl/generate_synthetic_data.py`, which produces deterministic data using `numpy` seed 42. In a production integration, this directory would be populated from source system exports.

### 4.2 Quality Checks

Run against the raw `order_lines` DataFrame before any transformation:

- **Null check** — `order_id`, `customer_id`, `product_id`, `order_date`
- **Duplicate check** — composite key `(order_id, product_id)`

Both checks return a `QualityReport(passed: bool, issues: list[str])`. If `passed` is `False`, issues are logged at WARNING level and execution continues. Rows failing the null check are dropped during the subsequent transform step. Duplicate rows are not automatically removed.

### 4.3 Transform

Applied in order:

**1. Date coercion**

`order_date`, `target_ship_date`, `ship_date`, and `delivery_date` are parsed to `datetime64` using `errors="coerce"`. Unparseable strings become `NaT`.

**2. Row filtering**

Rows with `NaT` or null in `order_id`, `customer_id`, `product_id`, or `order_date` are dropped. These rows are not loaded.

**3. Product join**

`unit_price`, `unit_cost`, and `category` are joined from `products` into the order lines using a left join on `product_id`. The merge is validated as many-to-one (`validate="m:1"`). Unmatched product IDs produce `NaN` in the cost and price columns.

**4. Derived columns**

| Column | Derivation | Notes |
|---|---|---|
| `revenue` | `quantity × unit_price` | `NaN` if product not matched |
| `cogs` | `quantity × unit_cost` | `NaN` if product not matched |
| `gross_margin` | `revenue − cogs` | |
| `on_time_ship` | `1` if `ship_date ≤ target_ship_date` and neither is `NaT`, else `0` | `0` for cancelled orders |
| `cycle_time_days` | `(delivery_date − order_date).days` | `NaN` for cancelled orders |

**5. Date dimension**

`dim_date` is generated spanning the minimum to maximum `order_date` in the fact table, one row per calendar day. Columns: `date`, `date_key` (YYYYMMDD integer), `year`, `quarter` (e.g. `Q1`), `month`, `month_name`, `week` (ISO week number), `day_name`.

### 4.4 Mart Schema

Four tables are written to the analytical store:

```
dim_customer          dim_product           dim_date
──────────────────    ──────────────────    ──────────────
customer_id           product_id            date
customer_name         product_name          date_key
segment               category              year
country               unit_price            quarter
created_at            unit_cost             month
                      is_active             month_name
                                            week
                                            day_name

fact_order_line
──────────────────────────
order_id               revenue
order_date             cogs
customer_id            gross_margin
product_id             on_time_ship
quantity               cycle_time_days
channel                ship_date
region                 delivery_date
unit_price             target_ship_date
unit_cost              is_cancelled
category
```

Each pipeline run replaces all four tables. There is no incremental or append mode.

### 4.5 KPI Computation

After load, KPIs are available two ways:

**Python** — `kpi/engine.py`: `compute_all(df)` accepts the `fact_order_line` DataFrame and returns `dict[str, float | None]`.

**HTTP** — `GET /metrics`: `app/services/mart.py` queries `fact_order_line` directly via SQL and returns a `KPISummary` JSON object.

---

## 5. KPI Engine Design

### 5.1 Registry

All KPIs are defined as frozen dataclasses in `kpi/definitions.py`. The engine (`kpi/engine.py`) contains no per-metric logic — it reads the registry and applies the specified aggregation.

```python
@dataclass(frozen=True)
class KPIDefinition:
    name: str
    label: str
    agg: Literal["sum", "mean", "count_distinct", "ratio"]
    column: str | None = None       # used by sum / mean / count_distinct
    numerator: str | None = None    # used by ratio
    denominator: str | None = None  # used by ratio; None = use filtered row count
    filter_expr: str | None = None  # pandas .query() string applied before aggregation
    scale: float = 1.0              # multiplier on the result (e.g. 100.0 for percentages)
```

### 5.2 Registered KPIs

| name | label | agg | filter | Notes |
|---|---|---|---|---|
| `total_revenue` | Total Revenue | `sum(revenue)` | `is_cancelled == 0` | |
| `total_cogs` | Total COGS | `sum(cogs)` | `is_cancelled == 0` | |
| `gross_margin` | Gross Margin | `sum(gross_margin)` | `is_cancelled == 0` | |
| `gross_margin_pct` | Gross Margin % | `sum(gross_margin) / sum(revenue) × 100` | `is_cancelled == 0` | `None` if revenue is 0 |
| `order_count` | Total Orders | `count_distinct(order_id)` | `is_cancelled == 0` | Counts distinct order IDs |
| `on_time_ship_rate` | On-Time Ship Rate % | `sum(on_time_ship) / row_count × 100` | `is_cancelled == 0` | Denominator is filtered row count |
| `avg_cycle_time` | Avg Cycle Time (days) | `mean(cycle_time_days)` | `is_cancelled == 0` | `NaN` rows excluded from mean automatically |
| `cancellation_rate` | Cancellation Rate % | `sum(is_cancelled) / row_count × 100` | none | Applied to full dataset |

### 5.3 Adding a KPI

Append a `KPIDefinition` to `REGISTRY` in `kpi/definitions.py`. `compute_all()` iterates the registry at call time — no changes to the engine or API are needed.

Example:

```python
KPIDefinition(
    name="avg_line_quantity",
    label="Avg Line Quantity",
    agg="mean",
    column="quantity",
    filter_expr="is_cancelled == 0",
),
```

### 5.4 Aggregation Semantics

| `agg` | Computation |
|---|---|
| `sum` | `df[column].sum()` on filtered rows |
| `mean` | `df[column].mean()` on filtered rows; `NaN` excluded by pandas. Returns `None` if all values are `NaN`. |
| `count_distinct` | `df[column].nunique()` on filtered rows |
| `ratio` | `sum(numerator) / sum(denominator) × scale` if `denominator` is set; otherwise `sum(numerator) / len(filtered) × scale`. Returns `None` if denominator resolves to 0. |

All aggregations return `None` if the filtered DataFrame is empty.

---

## 6. Data Quality & Reliability

### 6.1 Null Checks

`check_nulls(df, required_cols)` counts `df[col].isna()` for each required column. A column with any nulls contributes one issue string to the report in the form `"'column_name' has N null value(s)"`.

Required columns checked on `order_lines` pre-transform:
```
order_id, customer_id, product_id, order_date
```

Rows with nulls in these columns are dropped by `drop_invalid_rows()` during transform. They are not loaded into the mart.

### 6.2 Duplicate Detection

`check_duplicates(df, key_cols)` counts `df.duplicated(subset=key_cols)`. For `order_lines`, the key is `(order_id, product_id)`.

Duplicate rows are flagged in the quality report and logged. They are **not** automatically removed by the pipeline. If deduplication is required it should be applied upstream, before the pipeline runs.

### 6.3 Deterministic Transformations

Transform functions are pure: they take DataFrames as input, return new DataFrames, and do not mutate their arguments. Given the same input files, the pipeline produces identical output on every run.

### 6.4 Date Handling

All date fields are parsed with `errors="coerce"`. An unparseable value (empty string, non-ISO format, null) becomes `NaT` rather than raising an exception. The downstream behaviour depends on the field:

- `order_date` → row is dropped (required field)
- `ship_date` / `delivery_date` → kept; `on_time_ship` is set to `0`, `cycle_time_days` is `NaN`
- `target_ship_date` → kept; `on_time_ship` is set to `0`

### 6.5 Cancelled Orders

`is_cancelled` is a binary integer (`0` or `1`). Cancelled orders are retained in the fact table. Most KPIs filter them out via `filter_expr="is_cancelled == 0"`. `cancellation_rate` uses the full dataset.

---

## 7. Failure Modes

| Condition | Where it surfaces | Behaviour |
|---|---|---|
| CSV file missing | `etl/extract.py` `load_source()` | `FileNotFoundError`; pipeline halts |
| Required field null | `etl/quality.py` + `etl/transform.py` | Warning logged; row dropped in transform |
| Unparseable date | `etl/transform.py` `coerce_dates()` | Becomes `NaT`; row dropped if field is required |
| Duplicate `(order_id, product_id)` | `etl/quality.py` | Warning logged; duplicates loaded |
| `product_id` not in products table | `etl/transform.py` `derive_fact_metrics()` | Left join produces `NaN` for price/cost; `revenue` and `cogs` become `NaN` |
| Empty dataset after filtering | `kpi/engine.py` `compute()` | Returns `None` for all KPIs |
| Zero denominator in ratio KPI | `kpi/engine.py` `compute()` | Returns `None` |
| Unknown KPI name | `kpi/engine.py` `compute_by_name()` | Raises `KeyError` |
| Mart not built before API call | `app/routes/metrics.py` | HTTP 503 with detail "Mart not available — run ETL first" |
| Database unreachable | `app/routes/health.py` `ready()` | `GET /health/ready` returns HTTP 503 |

---

## 8. Running the Pipeline

### Prerequisites

- Python 3.12
- Docker + Docker Compose (for containerised execution)

### 8.1 Local Execution (SQLite)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Generate source data:

```bash
python etl/generate_synthetic_data.py
# Writes to: data/raw/customers.csv, products.csv, order_lines.csv
```

Run the ETL:

```bash
python etl/etl_to_sqlite.py
# Output: ✅ SQLite mart built at: data/processed/kpi_mart.db
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest -q
```

### 8.2 Docker Execution (Postgres)

Generate raw data locally first (the `data/raw/` directory is mounted read-only into the container):

```bash
python etl/generate_synthetic_data.py
```

Build and start:

```bash
docker-compose up --build
```

The app container waits for Postgres to pass its healthcheck, then runs the ETL pipeline on startup (`RUN_ETL_ON_STARTUP=true`). Logs from both stages appear in the app container output.

Endpoints are available at `http://localhost:8000`.

### 8.3 Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/processed/kpi_mart.db` | SQLAlchemy connection string |
| `RAW_DATA_DIR` | `data/raw` | Directory containing source CSV files |
| `ENV` | `development` | Runtime environment label |
| `RUN_ETL_ON_STARTUP` | `false` | Run the full ETL pipeline on app startup |

### 8.4 Triggering ETL Programmatically

```python
from sqlalchemy import create_engine
from etl.pipeline import run

engine = create_engine("postgresql://kpi:kpi@localhost:5432/kpi")
run("data/raw", engine)
```

---

## 9. Project Structure

```
.
├── app/                          FastAPI application
│   ├── main.py                   App factory, lifespan hook (optional ETL on startup)
│   ├── config.py                 Settings via pydantic-settings; reads .env
│   ├── core/
│   │   └── database.py           SQLAlchemy engine factory; check_db_ready()
│   ├── models/
│   │   └── kpi.py                Pydantic response models: KPISummary, RevenueMetric,
│   │                             OrderMetric
│   ├── routes/
│   │   ├── health.py             GET /health, GET /health/ready
│   │   └── metrics.py            GET /metrics → KPISummary JSON
│   └── services/
│       ├── etl.py                run_etl() — thin wrapper around etl.pipeline.run()
│       └── mart.py               get_kpi_summary() — SQL queries against fact_order_line
│
├── etl/                          ETL pipeline (database-agnostic)
│   ├── extract.py                load_source(), extract_all() — CSV ingestion
│   ├── transform.py              coerce_dates(), drop_invalid_rows(),
│   │                             derive_fact_metrics(), build_dim_date(), transform()
│   ├── quality.py                QualityReport dataclass; check_nulls(),
│   │                             check_duplicates(), run_quality_checks()
│   ├── load.py                   load_mart() — single-transaction write via SQLAlchemy
│   ├── pipeline.py               run(raw_dir, engine) — orchestrates all stages
│   ├── etl_to_sqlite.py          CLI entry point for local SQLite runs
│   └── generate_synthetic_data.py  Generates reproducible source data (seed=42)
│
├── kpi/                          KPI computation layer
│   ├── definitions.py            KPIDefinition dataclass + REGISTRY list + REGISTRY_MAP
│   └── engine.py                 compute(), compute_by_name(), compute_all()
│
├── tests/
│   ├── conftest.py               Shared fixtures (fact_df — 4 rows, 1 cancelled)
│   ├── test_mart_builds.py       Integration tests: mart tables exist, no negative revenue
│   ├── test_pipeline.py          Unit tests: transform functions, quality checks (15 tests)
│   ├── test_kpi_engine.py        Unit tests: KPI correctness, edge cases (13 tests)
│   └── test_health.py            Unit tests: /health and /health/ready endpoints (2 tests)
│
├── docs/
│   ├── acceptance_checks.sql     SQL queries for post-run validation
│   ├── metric_logic_table.csv    KPI definitions in tabular form (stakeholder reference)
│   └── runbook_refresh.md        Step-by-step local refresh procedure
│
├── data/
│   ├── raw/                      Source CSVs (not committed)
│   └── processed/                SQLite mart output (not committed)
│
├── Dockerfile                    Multi-stage build; non-root runtime user
├── docker-compose.yml            Services: app + postgres:16-alpine
├── .github/workflows/ci.yml      CI: lint (ruff) → typecheck (mypy) → test (pytest)
├── requirements.txt              Runtime dependencies (pinned)
├── requirements-dev.txt          Dev/test dependencies: pytest, httpx, ruff, mypy
├── pyproject.toml                Tool configuration: ruff, mypy, pytest
└── .env.example                  Environment variable reference
```

---

## 10. CI

Three jobs run on every push to `main` and on pull requests:

| Job | Tool | What runs |
|---|---|---|
| Lint | ruff 0.6.9 | `ruff check .` — E, F, I, UP rules across `app/`, `etl/`, `kpi/`, `tests/` |
| Type check | mypy 1.11.2 | `mypy app/` — checks the FastAPI application layer |
| Tests | pytest 8.3.2 | Generates synthetic data, builds SQLite mart, runs all 33 tests |

The test job seeds the mart before running so that the three integration tests in `test_mart_builds.py` have a populated database available. All other tests use in-memory DataFrames and do not require the mart.
