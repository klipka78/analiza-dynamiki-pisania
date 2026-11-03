"""Proste ALTER TABLE dla SQLite (istniejące wolumeny produkcyjne)."""

from sqlalchemy import text
from sqlalchemy.engine import Engine


NEW_SESSION_COLUMNS = [
    ("environment", "VARCHAR(32) DEFAULT 'web'"),
    ("keyboard_type", "VARCHAR(32) DEFAULT ''"),
    ("dominant_hand", "VARCHAR(16) DEFAULT ''"),
    ("fatigue", "INTEGER DEFAULT 0"),
    ("duration_ms", "FLOAT DEFAULT 0"),
]


def migrate_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(sessions)")).fetchall()
        existing = {r[1] for r in rows}
        for name, decl in NEW_SESSION_COLUMNS:
            if name not in existing:
                conn.execute(text(f"ALTER TABLE sessions ADD COLUMN {name} {decl}"))
