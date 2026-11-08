"""SQLite storage for AI results. Step 6 will add decisions to the audit_log table."""
import os
import sqlite3

DB_PATH = os.environ.get("MEDAI_DB", "service/data/medai.db")


def conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS results (
            study_id TEXT PRIMARY KEY,       -- Orthanc study ID
            probability REAL NOT NULL,       -- model confidence for pneumonia
            predicted_positive INTEGER NOT NULL,
            threshold REAL NOT NULL,
            model_version TEXT NOT NULL,
            heatmap_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending / approved / rejected
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);  -- worker's last Orthanc change sequence
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            decision TEXT NOT NULL,
            model_version TEXT NOT NULL,
            probability REAL NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)


def get_state(key, default="0"):
    with conn() as c:
        r = c.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_state(key, value):
    with conn() as c:
        c.execute("INSERT INTO state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))
