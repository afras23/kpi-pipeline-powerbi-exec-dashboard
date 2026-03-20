# Commit History

Ordered chronologically, earliest first.
Each entry reflects the actual build sequence of this repository.

---

```
commit 1  — 2024-11-04
chore: initialise project structure

Add top-level directories: etl/, kpi/, tests/, data/raw/, data/processed/,
docs/. Add .gitignore covering __pycache__, .venv, .env, data/processed/,
*.db, *.log.

---

commit 2  — 2024-11-04
chore: add requirements.txt with pinned runtime dependencies

pandas==2.2.2, numpy==2.0.1, faker==26.0.0, python-dateutil==2.9.0.post0.

---

commit 3  — 2024-11-05
feat(data): add synthetic data generator

etl/generate_synthetic_data.py produces deterministic CSV fixtures using
numpy seed 42. Generates 600 customers, 120 products, and up to ~88k order
lines with realistic segment weights, ship-date slip, and a 3% cancellation
rate. Output written to data/raw/.

---

commit 4  — 2024-11-06
feat(etl): add extract layer

etl/extract.py: load_source(name, raw_dir) loads a named CSV and raises
FileNotFoundError if the file is absent. extract_all(raw_dir) loads all
three required sources and returns a keyed dict of DataFrames.

---

commit 5  — 2024-11-06
test(etl): add test for extract source loading

Verify load_source raises FileNotFoundError on a missing file and returns
a DataFrame with the correct columns when the file exists.

---

commit 6  — 2024-11-07
feat(etl): add date coercion to transform layer

etl/transform.py: coerce_dates(df, cols) parses specified columns to
datetime64 using errors="coerce". Unparseable values become NaT rather than
raising. Returns a copy; does not mutate the input.

---

commit 7  — 2024-11-07
test(etl): test date coercion — valid strings, unparseable values, absent columns

Three cases: ISO strings parse correctly, invalid strings become NaT,
absent column names are silently skipped.

---

commit 8  — 2024-11-08
feat(etl): add row filtering for required fields

etl/transform.py: drop_invalid_rows(df, required_cols) drops rows with a
null in any listed column. Used to discard order lines missing order_id,
customer_id, product_id, or order_date before joining.

---

commit 9  — 2024-11-08
feat(etl): add fact table derivation

etl/transform.py: derive_fact_metrics(order_lines, products) joins
unit_price / unit_cost / category from products using a validated m:1 merge
on product_id, then derives revenue, cogs, gross_margin, on_time_ship, and
cycle_time_days. Transform functions remain pure.

---

commit 10 — 2024-11-11
test(etl): test derived metrics — revenue, COGS, gross margin, flags, cycle time

Unit tests for each derived column using minimal fixture DataFrames. Covers
on-time and late ship cases, and NaN cycle_time_days for orders with no
delivery date.

---

commit 11 — 2024-11-12
feat(etl): add dim_date builder

etl/transform.py: build_dim_date(min_date, max_date) generates one row per
calendar day with date_key (YYYYMMDD integer), year, quarter, month,
month_name, ISO week, and day_name.

---

commit 12 — 2024-11-12
feat(etl): add top-level transform() function

Composes coerce_dates, drop_invalid_rows, derive_fact_metrics, and
build_dim_date into a single call that returns
(dim_customer, dim_product, dim_date, fact_order_line).

---

commit 13 — 2024-11-13
feat(etl): add data quality checks

etl/quality.py: QualityReport dataclass with passed flag and issues list.
check_nulls(df, required_cols) reports per-column null counts.
check_duplicates(df, key_cols) reports duplicate row counts on a composite
key. run_quality_checks() composes both.

---

commit 14 — 2024-11-13
test(etl): test quality checks — pass cases, null detection, duplicate detection

Five tests: null check passes on clean data, fails and names the column on
dirty data; duplicate check passes and fails; combined run_quality_checks
returns both issues when both fail.

---

commit 15 — 2024-11-14
feat(etl): add load layer

etl/load.py: load_mart(engine, ...) writes all four mart tables inside a
single SQLAlchemy transaction using if_exists="replace". Logs row counts per
table at INFO level.

---

commit 16 — 2024-11-14
feat(etl): add pipeline orchestrator

etl/pipeline.py: run(raw_dir, engine) calls extract_all, run_quality_checks,
transform, and load_mart in sequence. Quality issues are logged as warnings;
the pipeline does not halt on non-passing quality reports.

---

commit 17 — 2024-11-15
feat(etl): add SQLite CLI runner

etl/etl_to_sqlite.py: thin entry point that creates a SQLite engine from a
hardcoded DB path and calls pipeline.run(). Intended for local development
and CI use.

---

commit 18 — 2024-11-18
feat(kpi): add KPI registry

kpi/definitions.py: frozen KPIDefinition dataclass with name, label, agg
type, column, numerator/denominator, filter_expr, and scale fields.
REGISTRY list defines eight KPIs: total_revenue, total_cogs, gross_margin,
gross_margin_pct, order_count, on_time_ship_rate, avg_cycle_time,
cancellation_rate. REGISTRY_MAP provides O(1) lookup by name.

---

commit 19 — 2024-11-18
feat(kpi): add KPI engine

kpi/engine.py: compute(df, kpi) applies filter_expr via df.query(), then
dispatches to sum / mean / count_distinct / ratio aggregation. Returns None
when the filtered DataFrame is empty or the denominator is zero.
compute_by_name() and compute_all() are convenience wrappers.

---

commit 20 — 2024-11-19
test(kpi): test KPI correctness against fixture fact table

Eight correctness tests — one per registered KPI — using a four-row fixture
(three active orders, one cancelled). Expected values are verified with
pytest.approx to handle floating-point comparisons.

---

commit 21 — 2024-11-19
test(kpi): test engine edge cases

Three edge-case tests: empty DataFrame returns None for all KPIs; fully
cancelled dataset returns None for revenue-filtered KPIs; zero-revenue
dataset returns None for gross_margin_pct. One error-path test: unknown
KPI name raises KeyError.

---

commit 22 — 2024-11-20
test(kpi): test compute_all returns every registered KPI

Verify that the keys in compute_all output match the set of names in
REGISTRY exactly. Catches any KPI added to the registry without a
corresponding engine path.

---

commit 23 — 2024-11-21
chore: add Dockerfile and docker-compose

Dockerfile: multi-stage build (builder installs deps, runtime is a clean
python:3.12-slim image running as a non-root user). docker-compose.yml:
postgres:16-alpine with a pg_isready healthcheck, app container depends on
healthy postgres, raw data directory mounted read-only.

---

commit 24 — 2024-11-22
feat(app): add FastAPI application skeleton

app/main.py: FastAPI instance with structured logging and a lifespan hook
that optionally runs the ETL pipeline on startup (RUN_ETL_ON_STARTUP env
var). app/config.py: Settings via pydantic-settings reading DATABASE_URL,
RAW_DATA_DIR, ENV, RUN_ETL_ON_STARTUP from environment or .env file.

---

commit 25 — 2024-11-22
feat(app): add database layer and health endpoints

app/core/database.py: get_engine() creates a SQLAlchemy engine from
DATABASE_URL; check_db_ready() executes SELECT 1 and returns a bool.
app/routes/health.py: GET /health returns {"status": "ok"};
GET /health/ready returns 200 or 503 based on DB connectivity.

---

commit 26 — 2024-11-25
feat(app): add KPI response models and metrics endpoint

app/models/kpi.py: Pydantic models KPISummary, RevenueMetric, OrderMetric.
app/services/mart.py: get_kpi_summary() runs two SQL aggregations against
fact_order_line and returns a typed KPISummary. Raises RuntimeError if the
table is empty or absent.
app/routes/metrics.py: GET /metrics returns KPISummary JSON or HTTP 503.

---

commit 27 — 2024-11-25
feat(app): add app/services/etl.py

run_etl() is a thin wrapper that calls etl.pipeline.run() with the engine
from app.core.database and the raw_data_dir from settings. Keeps the route
and service layers decoupled from pipeline internals.

---

commit 28 — 2024-11-26
test(app): add health endpoint tests

Two tests using FastAPI TestClient: GET /health always returns 200;
GET /health/ready returns 200 when the database is reachable (SQLite
pointed at a tmp_path fixture file).

---

commit 29 — 2024-11-27
chore: add GitHub Actions CI workflow

Three jobs: lint (ruff check .), typecheck (mypy app/), test (generate
synthetic data → build SQLite mart → pytest -q). Runs on push to main and
on pull requests.

---

commit 30 — 2024-11-27
chore: add pyproject.toml, requirements-dev.txt, .env.example

pyproject.toml: ruff config (line-length=100, E/F/I/UP rules,
per-file-ignores for generate_synthetic_data.py E501), mypy config
(ignore_missing_imports=true), pytest config (testpaths=tests,
pythonpath=.). requirements-dev.txt: pytest, httpx, ruff, mypy,
types-python-dateutil. .env.example: documents all environment variables
with defaults.
```
