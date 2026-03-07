"""Unified ingest CLI: python -m apps.worker.ingest --source reddit --date YYYY-MM-DD."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import date, datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from hypex_core import load_registry
from hypex_core.db import get_connection_string


def _load_registry_data():
    """Load titles and aliases from the registry."""
    root = Path(__file__).resolve().parent.parent.parent
    titles_path = root / "data" / "registry" / "titles.csv"
    aliases_path = root / "data" / "registry" / "aliases.json"
    return load_registry(str(titles_path), str(aliases_path))


def _check_existing_run(conn: psycopg.Connection, source: str, run_date: date) -> bool:
    """Check if a completed run already exists for this source+date."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT status FROM ingest_runs
            WHERE source = %s AND run_date = %s
            """,
            (source, run_date.isoformat()),
        )
        row = cur.fetchone()
        if row and row["status"] == "completed":
            return True
    return False


def _start_run(conn: psycopg.Connection, run_id: str, source: str, run_date: date) -> None:
    """Insert a new ingest run record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingest_runs (run_id, source, run_date, status)
            VALUES (%s, %s, %s, 'running')
            ON CONFLICT (source, run_date) DO UPDATE SET
                run_id = EXCLUDED.run_id,
                status = 'running',
                started_at = now(),
                finished_at = NULL,
                rows_ingested = 0,
                error_message = NULL
            """,
            (run_id, source, run_date.isoformat()),
        )
    conn.commit()


def _complete_run(conn: psycopg.Connection, run_id: str, rows: int) -> None:
    """Mark a run as completed."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingest_runs SET status = 'completed', finished_at = now(), rows_ingested = %s
            WHERE run_id = %s
            """,
            (rows, run_id),
        )
    conn.commit()


def _fail_run(conn: psycopg.Connection, run_id: str, error: str) -> None:
    """Mark a run as failed."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingest_runs SET status = 'failed', finished_at = now(), error_message = %s
            WHERE run_id = %s
            """,
            (error, run_id),
        )
    conn.commit()


def _upsert_metrics(conn: psycopg.Connection, metrics: list) -> int:
    """Upsert metric rows into daily_metrics. Returns number of rows affected."""
    count = 0
    with conn.cursor() as cur:
        for m in metrics:
            cur.execute(
                """
                INSERT INTO daily_metrics (metric_date, canonical_id, metric_name, value, confidence, raw_ref)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (metric_date, canonical_id, metric_name) DO UPDATE SET
                    value = EXCLUDED.value,
                    confidence = EXCLUDED.confidence,
                    raw_ref = EXCLUDED.raw_ref
                """,
                (
                    m.metric_date.isoformat(),
                    m.canonical_id,
                    m.metric_name,
                    m.value,
                    m.confidence,
                    json.dumps(m.raw_ref),
                ),
            )
            count += 1
    conn.commit()
    return count


def ingest_reddit(target_date: date) -> None:
    """Ingest Reddit data for a given date."""
    from hypex_reddit.fetcher import get_fetcher, DEFAULT_SUBREDDITS
    from hypex_reddit.aggregator import aggregate_posts

    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    run_id = str(uuid.uuid4())

    try:
        # Idempotency check
        if _check_existing_run(conn, "reddit", target_date):
            print(f"Reddit ingest for {target_date} already completed, skipping.")
            return

        _start_run(conn, run_id, "reddit", target_date)

        # Load registry
        titles, aliases = _load_registry_data()

        # Fetch posts from all subreddits
        fetcher = get_fetcher()
        all_posts = []
        for sub in DEFAULT_SUBREDDITS:
            posts = fetcher.fetch_posts_by_date(sub, target_date)
            all_posts.extend(posts)
            print(f"  Fetched {len(posts)} posts from r/{sub}")

        print(f"Total posts fetched: {len(all_posts)}")

        # Aggregate into metrics
        metrics = aggregate_posts(all_posts, titles, aliases, target_date)
        print(f"Aggregated into {len(metrics)} metric rows")

        # Upsert
        count = _upsert_metrics(conn, metrics)
        _complete_run(conn, run_id, count)
        print(f"Ingested {count} metrics for {target_date}")

    except Exception as e:
        _fail_run(conn, run_id, str(e))
        raise
    finally:
        conn.close()


SOURCES = {
    "reddit": ingest_reddit,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="HypeX ingest: fetch and store daily metrics")
    parser.add_argument("--source", required=True, choices=list(SOURCES.keys()), help="Data source")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    args = parser.parse_args()

    target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    ingest_fn = SOURCES[args.source]
    ingest_fn(target_date)


if __name__ == "__main__":
    main()
