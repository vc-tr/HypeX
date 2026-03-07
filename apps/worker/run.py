"""CLI entrypoint: python -m apps.worker.run --date YYYY-MM-DD."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from hypex_core import load_registry
from hypex_core.db import get_connection_string


def ensure_schema(conn: psycopg.Connection) -> None:
    """Create tables if not exist (multi-metric schema)."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS titles (
                canonical_id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                medium TEXT NOT NULL,
                language TEXT NOT NULL,
                aliases JSONB DEFAULT '[]',
                platform TEXT,
                year INT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                metric_date DATE NOT NULL,
                canonical_id TEXT NOT NULL REFERENCES titles(canonical_id) ON DELETE CASCADE,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                confidence REAL DEFAULT 1.0,
                raw_ref JSONB,
                PRIMARY KEY (metric_date, canonical_id, metric_name)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_metrics_cid
            ON daily_metrics(canonical_id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                canonical_id TEXT NOT NULL REFERENCES titles(canonical_id) ON DELETE CASCADE,
                date DATE NOT NULL,
                hype_index REAL NOT NULL,
                price REAL NOT NULL,
                PRIMARY KEY (canonical_id, date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ingest_runs (
                run_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                run_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                started_at TIMESTAMPTZ DEFAULT now(),
                finished_at TIMESTAMPTZ,
                rows_ingested INT DEFAULT 0,
                error_message TEXT,
                UNIQUE (source, run_date)
            )
        """)
    conn.commit()


def _synthetic_h_t(canonical_id: str, date_str: str) -> float:
    """Generate synthetic hype index H_t (0-100) for a title on a date."""
    seed = f"{canonical_id}:{date_str}"
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 10000
    base = 30.0 + (h % 50)  # 30-80 range
    d = datetime.strptime(date_str, "%Y-%m-%d")
    day_factor = (d.day % 7) / 7.0 * 10
    return round(base + day_factor, 2)


def _synthetic_p_t(canonical_id: str, date_str: str) -> float:
    """Generate synthetic price P_t for paper trading."""
    h_t = _synthetic_h_t(canonical_id, date_str)
    base_price = 10.0 + h_t / 10.0
    seed = f"price:{canonical_id}:{date_str}"
    noise = (int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 100) / 100.0 - 0.5
    return round(max(1.0, base_price + noise), 2)


def run(date_str: str) -> None:
    """Load registry, ensure schema, upsert titles, compute and store metrics/prices."""
    root = Path(__file__).resolve().parent.parent.parent
    titles_path = root / "data" / "registry" / "titles.csv"
    aliases_path = root / "data" / "registry" / "aliases.json"
    titles, _ = load_registry(str(titles_path), str(aliases_path))

    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            for t in titles:
                cur.execute(
                    """
                    INSERT INTO titles (canonical_id, canonical_name, medium, language, aliases, platform, year)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (canonical_id) DO UPDATE SET
                        canonical_name = EXCLUDED.canonical_name,
                        medium = EXCLUDED.medium,
                        language = EXCLUDED.language,
                        aliases = EXCLUDED.aliases,
                        platform = EXCLUDED.platform,
                        year = EXCLUDED.year
                    """,
                    (
                        t.canonical_id,
                        t.canonical_name,
                        t.medium,
                        t.language,
                        json.dumps(t.aliases),
                        t.platform,
                        t.year,
                    ),
                )

                # Check if real metrics exist for this title+date
                cur.execute(
                    """
                    SELECT 1 FROM daily_metrics
                    WHERE canonical_id = %s AND metric_date = %s
                    LIMIT 1
                    """,
                    (t.canonical_id, date_str),
                )
                has_real_metrics = cur.fetchone() is not None

                h_t = _synthetic_h_t(t.canonical_id, date_str)
                p_t = _synthetic_p_t(t.canonical_id, date_str)

                # Only insert synthetic metrics if no real data exists
                if not has_real_metrics:
                    cur.execute(
                        """
                        INSERT INTO daily_metrics (metric_date, canonical_id, metric_name, value, confidence)
                        VALUES (%s, %s, 'synthetic_hype', %s, 0.5)
                        ON CONFLICT (metric_date, canonical_id, metric_name) DO UPDATE SET
                            value = EXCLUDED.value
                        """,
                        (date_str, t.canonical_id, h_t),
                    )

                cur.execute(
                    """
                    INSERT INTO daily_prices (canonical_id, date, hype_index, price)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (canonical_id, date) DO UPDATE SET
                        hype_index = EXCLUDED.hype_index,
                        price = EXCLUDED.price
                    """,
                    (t.canonical_id, date_str, h_t, p_t),
                )
        conn.commit()
        print(f"Processed {len(titles)} titles for {date_str}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="HypeX worker: compute daily hype metrics")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    args = parser.parse_args()
    run(args.date)


if __name__ == "__main__":
    main()
