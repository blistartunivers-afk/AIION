import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "aiion.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            action TEXT,
            result TEXT,
            status TEXT,
            step INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_episode(task: str, action: str, result: str, status: str, step: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO episodes (task, action, result, status, step, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (task, action, result, status, step, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_recent_episodes(limit: int = 5):
    conn = get_connection()
    cur = conn.execute(
        "SELECT task, action, result, status, step, created_at FROM episodes ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
