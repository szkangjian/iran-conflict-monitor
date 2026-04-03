import sqlite3
import os
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

from config import DB_PATH

logger = logging.getLogger(__name__)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guid        TEXT    UNIQUE NOT NULL,
                title       TEXT    NOT NULL,
                summary     TEXT,
                url         TEXT,
                source      TEXT,
                published   TEXT,
                fetched_at  TEXT    NOT NULL,
                severity    TEXT    NOT NULL DEFAULT 'low',
                tags        TEXT,
                alerted     INTEGER NOT NULL DEFAULT 0,
                event_score REAL    DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_published  ON events(published DESC);
            CREATE INDEX IF NOT EXISTS idx_events_severity   ON events(severity);
            CREATE INDEX IF NOT EXISTS idx_events_fetched_at ON events(fetched_at DESC);

            CREATE TABLE IF NOT EXISTS daily_scores (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                date             TEXT    UNIQUE NOT NULL,
                score            REAL    NOT NULL,
                d1               REAL,
                d2               REAL,
                d3               REAL,
                d4               REAL,
                d5               REAL,
                nuclear_override INTEGER NOT NULL DEFAULT 0,
                computed_at      TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_daily_scores_date ON daily_scores(date DESC);
        """)
    # Migrate existing DB: add event_score column if not present
    try:
        with _conn() as conn:
            conn.execute("ALTER TABLE events ADD COLUMN event_score REAL DEFAULT NULL")
        logger.info("Migrated: added event_score column")
    except sqlite3.OperationalError:
        pass  # column already exists
    logger.info("Database initialised at %s", DB_PATH)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_event(event: dict) -> bool:
    """Insert event; return True if new, False if already existed."""
    with _conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO events
                    (guid, title, summary, url, source, published, fetched_at,
                     severity, tags, event_score)
                VALUES
                    (:guid, :title, :summary, :url, :source, :published, :fetched_at,
                     :severity, :tags, :event_score)
                """,
                event,
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_events(limit: int = 100, severity: str = None, source: str = None) -> list[dict]:
    clauses, params = [], []
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if source:
        clauses.append("source = ?")
        params.append(source)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    with _conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM events {where} ORDER BY published DESC LIMIT ?", params
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_in_window(hours: int, offset_hours: int = 0) -> list[dict]:
    """Return events published within [now - offset - hours, now - offset]."""
    now   = datetime.now(timezone.utc)
    end   = now - timedelta(hours=offset_hours)
    start = end  - timedelta(hours=hours)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE published >= ? AND published < ? ORDER BY published DESC",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def get_unalerted_events() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE alerted = 0 AND severity IN ('high','critical') "
            "ORDER BY published DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def mark_alerted(event_id: int):
    with _conn() as conn:
        conn.execute("UPDATE events SET alerted = 1 WHERE id = ?", (event_id,))


def upsert_daily_score(data: dict):
    """Insert or replace today's score record."""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_scores
                (date, score, d1, d2, d3, d4, d5, nuclear_override, computed_at)
            VALUES
                (:date, :score, :d1, :d2, :d3, :d4, :d5, :nuclear_override, :computed_at)
            ON CONFLICT(date) DO UPDATE SET
                score            = excluded.score,
                d1               = excluded.d1,
                d2               = excluded.d2,
                d3               = excluded.d3,
                d4               = excluded.d4,
                d5               = excluded.d5,
                nuclear_override = excluded.nuclear_override,
                computed_at      = excluded.computed_at
            """,
            data,
        )


def get_latest_score() -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_scores ORDER BY date DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def get_score_history(days: int = 30) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_scores ORDER BY date DESC LIMIT ?", (days,)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_stats() -> dict:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        by_severity = {
            row["severity"]: row["cnt"]
            for row in conn.execute(
                "SELECT severity, COUNT(*) AS cnt FROM events GROUP BY severity"
            ).fetchall()
        }
        by_source = {
            row["source"]: row["cnt"]
            for row in conn.execute(
                "SELECT source, COUNT(*) AS cnt FROM events GROUP BY source "
                "ORDER BY cnt DESC LIMIT 10"
            ).fetchall()
        }
        latest = conn.execute(
            "SELECT fetched_at FROM events ORDER BY fetched_at DESC LIMIT 1"
        ).fetchone()
    return {
        "total":       total,
        "by_severity": by_severity,
        "by_source":   by_source,
        "last_fetch":  latest["fetched_at"] if latest else None,
    }
