"""Price pipeline: compute daily prices from ingested metrics.

CLI: python -m apps.worker.prices --start YYYY-MM-DD --end YYYY-MM-DD

Algorithm (v1 spec):
1. Rolling z-score per metric per title (window=28, min=7), winsorized to [-3, 3]
2. H_t = 0.7 * z(mentions_count) + 0.3 * z(engagement_score)
3. Hs_t = 0.7 * H_t + 0.3 * Hs_{t-1}  (exponential smoothing)
4. P_t = P_{t-1} * exp(0.02 * Hs_t),  P_0 = 100
5. Missing metrics => z = 0
"""

from __future__ import annotations

import argparse
import math
from datetime import date, datetime, timedelta
from statistics import mean, stdev

import psycopg
from psycopg.rows import dict_row

from hypex_core.db import get_connection_string


# ── Pure computation functions (no DB, fully testable) ───────────────────


def rolling_zscore(
    values: list[float],
    window: int = 28,
    min_periods: int = 7,
) -> list[float]:
    """Compute rolling z-scores, winsorized to [-3, 3].

    For positions with fewer than min_periods values in the lookback window,
    returns 0.0.
    """
    zscores: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_vals = values[start : i + 1]
        if len(window_vals) < min_periods:
            zscores.append(0.0)
            continue
        mu = mean(window_vals)
        sigma = stdev(window_vals) if len(window_vals) > 1 else 1.0
        if sigma == 0:
            sigma = 1.0
        z = (values[i] - mu) / sigma
        zscores.append(max(-3.0, min(3.0, z)))
    return zscores


def compute_hype_index(
    z_mentions: list[float],
    z_engagement: list[float],
    w_mentions: float = 0.7,
    w_engagement: float = 0.3,
) -> list[float]:
    """H_t = w_mentions * z(mentions) + w_engagement * z(engagement)."""
    return [
        w_mentions * zm + w_engagement * ze
        for zm, ze in zip(z_mentions, z_engagement)
    ]


def smooth_hype(h_values: list[float], alpha: float = 0.7) -> list[float]:
    """Exponential smoothing: Hs_t = alpha * H_t + (1 - alpha) * Hs_{t-1}."""
    if not h_values:
        return []
    smoothed: list[float] = [h_values[0]]
    for i in range(1, len(h_values)):
        smoothed.append(alpha * h_values[i] + (1 - alpha) * smoothed[i - 1])
    return smoothed


def compute_prices(
    hs_values: list[float],
    p0: float = 100.0,
    sensitivity: float = 0.02,
) -> list[float]:
    """P_t = P_{t-1} * exp(sensitivity * Hs_t), P_0 = p0."""
    if not hs_values:
        return []
    prices: list[float] = [p0 * math.exp(sensitivity * hs_values[0])]
    for i in range(1, len(hs_values)):
        prices.append(prices[i - 1] * math.exp(sensitivity * hs_values[i]))
    return prices


# ── DB-backed pipeline ────────────────────────────────────────────────────


def _get_metric_series(
    conn: psycopg.Connection,
    canonical_id: str,
    metric_name: str,
    start_date: date,
    end_date: date,
) -> dict[date, float]:
    """Query daily_metrics for a specific metric, returning {date: value}."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT metric_date, value FROM daily_metrics
            WHERE canonical_id = %s AND metric_name = %s
              AND metric_date >= %s AND metric_date <= %s
            ORDER BY metric_date
            """,
            (canonical_id, metric_name, start_date.isoformat(), end_date.isoformat()),
        )
        return {row["metric_date"]: row["value"] for row in cur.fetchall()}


def _get_last_price(conn: psycopg.Connection, canonical_id: str, before_date: date) -> float | None:
    """Get the most recent price before a date, for continuity."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT price FROM daily_prices
            WHERE canonical_id = %s AND date < %s
            ORDER BY date DESC LIMIT 1
            """,
            (canonical_id, before_date.isoformat()),
        )
        row = cur.fetchone()
        return row["price"] if row else None


def _get_all_title_ids(conn: psycopg.Connection) -> list[str]:
    """Get all canonical_ids from titles table."""
    with conn.cursor() as cur:
        cur.execute("SELECT canonical_id FROM titles ORDER BY canonical_id")
        return [row["canonical_id"] for row in cur.fetchall()]


def run(start_str: str, end_str: str) -> None:
    """Compute prices for all titles in the date range."""
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()

    # Extend lookback for z-score calculation (28-day window)
    lookback_start = start - timedelta(days=28)

    # Build full date range
    all_dates: list[date] = []
    d = lookback_start
    while d <= end:
        all_dates.append(d)
        d += timedelta(days=1)

    # Dates within the output range (the ones we actually write prices for)
    output_dates: list[date] = [d for d in all_dates if d >= start]

    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    try:
        title_ids = _get_all_title_ids(conn)
        processed = 0

        for cid in title_ids:
            # Get metric series (including lookback window)
            mentions_map = _get_metric_series(conn, cid, "mentions_count", lookback_start, end)
            engagement_map = _get_metric_series(conn, cid, "engagement_score", lookback_start, end)

            # Fill to aligned arrays (missing = 0)
            mentions_vals = [mentions_map.get(d, 0.0) for d in all_dates]
            engagement_vals = [engagement_map.get(d, 0.0) for d in all_dates]

            # Skip if no real data at all
            if not mentions_map and not engagement_map:
                continue

            # Compute z-scores
            z_mentions = rolling_zscore(mentions_vals)
            z_engagement = rolling_zscore(engagement_vals)

            # Compute hype index
            h_values = compute_hype_index(z_mentions, z_engagement)

            # Smooth
            hs_values = smooth_hype(h_values)

            # Get starting price
            prev_price = _get_last_price(conn, cid, lookback_start)
            p0 = prev_price if prev_price is not None else 100.0

            # Compute prices for full range (including lookback)
            prices = compute_prices(hs_values, p0=p0)

            # Only write the output range
            offset = len(all_dates) - len(output_dates)
            with conn.cursor() as cur:
                for i, d in enumerate(output_dates):
                    idx = offset + i
                    cur.execute(
                        """
                        INSERT INTO daily_prices (canonical_id, date, hype_index, price)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (canonical_id, date) DO UPDATE SET
                            hype_index = EXCLUDED.hype_index,
                            price = EXCLUDED.price
                        """,
                        (cid, d.isoformat(), round(hs_values[idx], 4), round(prices[idx], 4)),
                    )
            conn.commit()
            processed += 1

        print(f"Computed prices for {processed} titles from {start_str} to {end_str}")

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="HypeX price pipeline")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    args = parser.parse_args()
    run(args.start, args.end)


if __name__ == "__main__":
    main()
