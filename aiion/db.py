"""aiion/db.py — Capa de acceso a datos centralizada con schema versionado y migraciones.

Convenciones:
- Single source of truth para TODOS los accesos a SQLite.
- Schema versionado en tabla `schema_version`.
- Migraciones idempotentes: se ejecutan solo las pendientes.
- PRAGMAs de performance (WAL, synchronous NORMAL, foreign_keys ON).
- API simple: init_db(), run_migrations(), get_conn(), execute() / executemany() / query().
"""
from __future__ import annotations
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from aiion.config import AIION_HOME, SENSOR_DB

# ───────────────────────────────────────────────────────────────────────────
# Conexión thread-local (SQLite no comparte conexiones entre hilos)
# ───────────────────────────────────────────────────────────────────────────
_TLS = threading.local()
_LOCK = threading.RLock()

# Última versión del schema. Cuando se añada una migración nueva, incrementar.
CURRENT_SCHEMA_VERSION = 4


def get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    """Obtiene (o crea) una conexión SQLite para el hilo actual."""
    if db_path is None:
        db_path = SENSOR_DB
    conn = getattr(_TLS, "conns", None)
    if conn is None:
        conn = {}
        _TLS.conns = conn
    if db_path not in conn:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(
            str(db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
            timeout=30.0,
        )
        c.row_factory = sqlite3.Row
        # PRAGMAs
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        conn[str(db_path)] = c
    return conn[str(db_path)]


def close_all() -> None:
    """Cierra todas las conexiones del hilo actual (uso en tests/shutdown)."""
    conn = getattr(_TLS, "conns", None)
    if not conn:
        return
    for c in conn.values():
        try:
            c.close()
        except Exception:
            pass
    _TLS.conns = {}


# ───────────────────────────────────────────────────────────────────────────
# Migraciones
# ───────────────────────────────────────────────────────────────────────────
# Cada migración es un bloque SQL idempotente. Se ejecutan en orden.
# IMPORTANTE: añadir siempre al final, NUNCA modificar las ya aplicadas.
MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "init_readings_alerts",
        """
        CREATE TABLE IF NOT EXISTS readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            sensor TEXT NOT NULL,
            data TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_st ON readings(sensor, ts);

        CREATE TABLE IF NOT EXISTS sensor_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            level TEXT NOT NULL,
            sensor TEXT NOT NULL,
            message TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        "schema_metadata",
        """
        CREATE TABLE IF NOT EXISTS schema_version(
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_meta(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
    (
        3,
        "model_performance_kalman",
        """
        CREATE TABLE IF NOT EXISTS model_performance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prov_id TEXT NOT NULL,
            model TEXT NOT NULL,
            success INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            ts REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mp_ts ON model_performance(ts);
        CREATE INDEX IF NOT EXISTS idx_mp_prov_model ON model_performance(prov_id, model);
        """,
    ),
    (
        4,
        "circuit_breaker_state",
        """
        CREATE TABLE IF NOT EXISTS circuit_breaker_state(
            tool        TEXT PRIMARY KEY,
            fails       INTEGER NOT NULL DEFAULT 0,
            last_fail   REAL    NOT NULL DEFAULT 0,
            state       TEXT    NOT NULL DEFAULT 'CLOSED',
            updated_at  REAL    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cb_state ON circuit_breaker_state(state);
        """,
    ),
]


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    """Crea la tabla de control de versiones si no existe."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version(
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    try:
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
        return {int(r["version"]) for r in rows}
    except sqlite3.OperationalError:
        return set()


def run_migrations(db_path: Path | None = None) -> list[int]:
    """Ejecuta todas las migraciones pendientes. Devuelve las versiones aplicadas."""
    with _LOCK:
        conn = get_conn(db_path)
        _ensure_schema_version_table(conn)
        applied = _applied_versions(conn)
        newly_applied: list[int] = []
        for version, name, sql in MIGRATIONS:
            if version in applied:
                continue
            if version > CURRENT_SCHEMA_VERSION:
                # Defensa: no aplicar migraciones del "futuro"
                continue
            try:
                conn.executescript(sql)
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version(version, name, applied_at) VALUES (?,?,?)",
                    (version, name, datetime.now().isoformat()),
                )
                conn.commit()
                applied.add(version)
                newly_applied.append(version)
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Migración v{version} ({name}) falló: {e}") from e
        return newly_applied


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Inicializa DB + corre migraciones pendientes. Idempotente."""
    conn = get_conn(db_path)
    run_migrations(db_path)
    return conn


def current_version(db_path: Path | None = None) -> int:
    """Devuelve la versión actual del schema aplicada (0 si ninguna)."""
    conn = get_conn(db_path)
    _ensure_schema_version_table(conn)
    applied = _applied_versions(conn)
    return max(applied) if applied else 0


# ───────────────────────────────────────────────────────────────────────────
# Helpers de alto nivel
# ───────────────────────────────────────────────────────────────────────────
def execute(sql: str, params: Sequence[Any] = (), db_path: Path | None = None) -> int:
    """Ejecuta un INSERT/UPDATE/DELETE. Devuelve lastrowid o rowcount."""
    with _LOCK:
        conn = get_conn(db_path)
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid or cur.rowcount


def executemany(sql: str, params: Iterable[Sequence[Any]], db_path: Path | None = None) -> int:
    with _LOCK:
        conn = get_conn(db_path)
        cur = conn.executemany(sql, params)
        conn.commit()
        return cur.rowcount


def query(sql: str, params: Sequence[Any] = (), db_path: Path | None = None) -> list[sqlite3.Row]:
    with _LOCK:
        conn = get_conn(db_path)
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: Sequence[Any] = (), db_path: Path | None = None) -> sqlite3.Row | None:
    with _LOCK:
        conn = get_conn(db_path)
        return conn.execute(sql, params).fetchone()


# ───────────────────────────────────────────────────────────────────────────
# Backfill: si la DB ya existía con el schema v1 sin pasar por el runner,
# registramos la versión para que no se intente reaplicar.
# ───────────────────────────────────────────────────────────────────────────
def backfill_legacy_version(db_path: Path | None = None) -> None:
    """Marca como aplicadas las migraciones cuyo efecto ya está en la DB."""
    conn = get_conn(db_path)
    _ensure_schema_version_table(conn)
    applied = _applied_versions(conn)
    # Si la tabla `readings` existe (schema v1 legado) pero la versión no está
    # registrada, la registramos retroactivamente.
    if 1 not in applied:
        tables = {
            r["name"] for r in query("SELECT name FROM sqlite_master WHERE type='table'", (), db_path)
        }
        if {"readings", "sensor_alerts"}.issubset(tables):
            conn.execute(
                "INSERT OR REPLACE INTO schema_version(version, name, applied_at) VALUES (?,?,?)",
                (1, "init_readings_alerts (legacy backfill)", datetime.now().isoformat()),
            )
            conn.commit()


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "MIGRATIONS",
    "get_conn",
    "close_all",
    "init_db",
    "run_migrations",
    "current_version",
    "execute",
    "executemany",
    "query",
    "query_one",
    "backfill_legacy_version",
    "AIION_HOME",
]
