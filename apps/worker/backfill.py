"""Backfill tool: populate N days of mock Reddit data + prices.

CLI: python -m apps.worker.backfill --days 30

For each day from (today - N) to today:
  1. Run mock Reddit ingest (skips if already completed)
  2. Run price pipeline for that day
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from apps.worker.ingest import ingest_reddit
from apps.worker.prices import run as run_prices


def backfill(days: int) -> None:
    """Run ingest + prices for the last N days."""
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    print(f"=== Backfilling {days} days: {start_date} → {today} ===\n")

    # Phase 1: Ingest all days
    d = start_date
    while d <= today:
        print(f"[Ingest] {d}")
        try:
            ingest_reddit(d)
        except Exception as e:
            print(f"  ⚠ Ingest failed for {d}: {e}")
        d += timedelta(days=1)

    # Phase 2: Compute prices for the full range
    print(f"\n[Prices] Computing {start_date} → {today}")
    try:
        run_prices(start_date.isoformat(), today.isoformat())
    except Exception as e:
        print(f"  ⚠ Price computation failed: {e}")

    print(f"\n=== Backfill complete ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill mock data for N days")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backfill (default: 30)")
    args = parser.parse_args()
    backfill(args.days)


if __name__ == "__main__":
    main()
