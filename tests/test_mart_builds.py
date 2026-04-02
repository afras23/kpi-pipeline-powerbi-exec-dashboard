import os
import sqlite3


def test_sqlite_mart_exists():
    assert os.path.exists("data/processed/kpi_mart.db"), "Run etl/etl_to_sqlite.py first"


def test_tables_exist():
    with sqlite3.connect("data/processed/kpi_mart.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {r[0] for r in cur.fetchall()}
    expected = {"dim_customer", "dim_product", "dim_date", "fact_order_line"}
    assert expected.issubset(tables)


def test_no_negative_revenue():
    with sqlite3.connect("data/processed/kpi_mart.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fact_order_line WHERE revenue < 0;")
        n = cur.fetchone()[0]
    assert n == 0
