"""One-time schema migration: daily_metrics v1 → v2 (multi-metric) + ingest_runs.

Run: python -m apps.worker.migrate
"""

import psycopg
from psycopg.rows import dict_row

from hypex_core.db import get_connection_string


def migrate(conn: psycopg.Connection) -> None:
    """Migrate daily_metrics to multi-metric schema and add ingest_runs."""
    with conn.cursor() as cur:
        # Check if migration is needed (old schema has 'hype_index' column)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'daily_metrics' AND column_name = 'hype_index'
            )
        """)
        old_schema_exists = cur.fetchone()[0]

        if old_schema_exists:
            print("Migrating daily_metrics to multi-metric schema...")

            # Create new table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics_v2 (
                    metric_date DATE NOT NULL,
                    canonical_id TEXT NOT NULL REFERENCES titles(canonical_id) ON DELETE CASCADE,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    raw_ref JSONB,
                    PRIMARY KEY (metric_date, canonical_id, metric_name)
                )
            """)

            # Migrate old data
            cur.execute("""
                INSERT INTO daily_metrics_v2 (metric_date, canonical_id, metric_name, value, confidence)
                SELECT date, canonical_id, 'hype_index_legacy', hype_index, 1.0
                FROM daily_metrics
                ON CONFLICT DO NOTHING
            """)
            migrated = cur.rowcount

            # Swap tables
            cur.execute("DROP TABLE daily_metrics")
            cur.execute("ALTER TABLE daily_metrics_v2 RENAME TO daily_metrics")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_metrics_cid
                ON daily_metrics(canonical_id)
            """)
            print(f"  Migrated {migrated} rows from old schema.")
        else:
            # Check if table exists at all
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'daily_metrics'
                )
            """)
            table_exists = cur.fetchone()[0]

            if not table_exists:
                print("Creating daily_metrics table (multi-metric schema)...")
                cur.execute("""
                    CREATE TABLE daily_metrics (
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
            else:
                print("daily_metrics already in multi-metric schema, skipping.")

        # Create ingest_runs table
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
        print("ingest_runs table ensured.")

    conn.commit()
    print("Migration complete.")


def main() -> None:
    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    try:
        migrate(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
