from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_ready_with_sqlite(tmp_path, monkeypatch) -> None:
    """Ready endpoint returns 200 when the SQLite DB is reachable."""
    db = tmp_path / "test.db"
    import sqlite3

    sqlite3.connect(str(db)).close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")

    # Re-import settings so it picks up the monkeypatched env var
    import importlib

    import app.config as cfg_module
    import app.core.database as db_module

    cfg_module.settings = cfg_module.Settings()
    importlib.reload(db_module)

    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}
