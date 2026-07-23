"""tests/test_db.py — Tests para aiion/db.py (schema versionado + migraciones)."""
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from aiion import db


@pytest.fixture
def tmp_db(monkeypatch):
    """DB temporal por test (limpia thread-local)."""
    tmpdir = tempfile.mkdtemp(prefix="aiion_db_")
    dbpath = Path(tmpdir) / "test.db"
    db.close_all()
    yield dbpath
    db.close_all()
    try:
        dbpath.unlink(missing_ok=True)
    except Exception:
        pass


# ── init_db & migraciones ─────────────────────────────────────────────────
def test_init_db_creates_tables(tmp_db):
    conn = db.init_db(tmp_db)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r[0] for r in rows}
    assert "readings" in names
    assert "sensor_alerts" in names
    assert "schema_version" in names
    assert "app_meta" in names


def test_init_db_idempotent(tmp_db):
    """Llamar init_db() 5 veces no debe romper nada ni duplicar."""
    for _ in range(5):
        db.init_db(tmp_db)
    version = db.current_version(tmp_db)
    assert version == db.CURRENT_SCHEMA_VERSION


def test_current_version_zero_on_empty(tmp_db):
    """En DB vacía sin migrar, current_version debe ser 0."""
    # No llamar init_db; crear solo el archivo
    tmp_db.touch()
    assert db.current_version(tmp_db) == 0


def test_run_migrations_records_versions(tmp_db):
    applied = db.run_migrations(tmp_db)
    assert len(applied) >= 2
    # Segunda ejecución: no debe reaplicar
    applied2 = db.run_migrations(tmp_db)
    assert applied2 == []


def test_schema_version_metadata(tmp_db):
    db.init_db(tmp_db)
    rows = db.query(
        "SELECT version, name FROM schema_version ORDER BY version", (), tmp_db
    )
    versions = [r["version"] for r in rows]
    assert versions == [1, 2]
    assert all(r["name"] for r in rows)


# ── PRAGMAs ───────────────────────────────────────────────────────────────
def test_wal_mode_enabled(tmp_db):
    conn = db.init_db(tmp_db)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_foreign_keys_enabled(tmp_db):
    conn = db.init_db(tmp_db)
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


# ── Helpers de alto nivel ─────────────────────────────────────────────────
def test_execute_insert_and_query(tmp_db):
    db.init_db(tmp_db)
    new_id = db.execute(
        "INSERT INTO readings(ts, sensor, data) VALUES (?,?,?)",
        ("2026-01-01T00:00:00", "battery", '{"level":50}'),
        tmp_db,
    )
    assert new_id > 0
    rows = db.query("SELECT * FROM readings WHERE id=?", (new_id,), tmp_db)
    assert len(rows) == 1
    assert rows[0]["sensor"] == "battery"


def test_query_one_returns_none_when_empty(tmp_db):
    db.init_db(tmp_db)
    row = db.query_one("SELECT * FROM readings WHERE id=?", (99999,), tmp_db)
    assert row is None


def test_executemany_bulk_insert(tmp_db):
    db.init_db(tmp_db)
    params = [
        ("2026-01-01T00:00:00", "wifi", "{}"),
        ("2026-01-01T00:00:01", "wifi", "{}"),
        ("2026-01-01T00:00:02", "wifi", "{}"),
    ]
    n = db.executemany(
        "INSERT INTO readings(ts, sensor, data) VALUES (?,?,?)",
        params,
        tmp_db,
    )
    assert n == 3
    rows = db.query("SELECT COUNT(*) AS c FROM readings", (), tmp_db)
    assert rows[0]["c"] == 3


# ── Thread-safety: conexiones por hilo ────────────────────────────────────
def test_concurrent_writes(tmp_db):
    import threading

    db.init_db(tmp_db)

    def writer(sensor_name, n):
        for i in range(n):
            db.execute(
                "INSERT INTO readings(ts, sensor, data) VALUES (?,?,?)",
                (f"2026-01-01T00:00:{i:02d}", sensor_name, "{}"),
                tmp_db,
            )

    threads = [threading.Thread(target=writer, args=(f"sensor_{i}", 20)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = db.query_one("SELECT COUNT(*) AS c FROM readings", (), tmp_db)
    assert total["c"] == 80


# ── Backfill de DB legada ────────────────────────────────────────────────
def test_backfill_legacy_db(tmp_db):
    """Simula una DB creada con el schema v1 ANTES de existir db.py."""
    con = sqlite3.connect(str(tmp_db))
    con.executescript("""
        CREATE TABLE readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, sensor TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE sensor_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, level TEXT NOT NULL,
            sensor TEXT NOT NULL, message TEXT NOT NULL);
        CREATE INDEX idx_st ON readings(sensor, ts);
    """)
    con.commit()
    con.close()

    db.backfill_legacy_version(tmp_db)
    version = db.current_version(tmp_db)
    assert version == 1
    # run_migrations NO debe reaplicar la v1
    applied = db.run_migrations(tmp_db)
    assert 1 not in applied
    # Pero sí debe aplicar la v2 (schema_metadata)
    assert 2 in applied


# ── Migración: añadir nueva versión no debe romper nada ──────────────────
def test_migrations_are_ordered_and_unique():
    versions = [v for v, _, _ in db.MIGRATIONS]
    assert versions == sorted(versions)
    assert len(versions) == len(set(versions))
