"""Postgres queries for HypeX API."""

import psycopg

from hypex_core.db import get_connection_string, get_db  # noqa: F401


def list_titles(
    conn: psycopg.Connection,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    medium: str | None = None,
) -> tuple[list[dict], int]:
    """List titles with pagination and optional filters."""
    offset = (page - 1) * limit
    where_clauses: list[str] = []
    params: list[object] = []
    if search:
        pattern = f"%{search}%"
        where_clauses.append(
            "(canonical_name ILIKE %s OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(aliases) a WHERE a ILIKE %s))"
        )
        params.extend([pattern, pattern])
    if medium:
        where_clauses.append("medium = %s")
        params.append(medium)
    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM titles WHERE {where_sql}", params)
        total = cur.fetchone()["count"]
        cur.execute(
            f"""
            SELECT canonical_id, canonical_name, medium, language, aliases, platform, year
            FROM titles
            WHERE {where_sql}
            ORDER BY canonical_name
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()
    return list(rows), total


def get_series(conn: psycopg.Connection, canonical_id: str) -> dict | None:
    """Get title by canonical_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT canonical_id, canonical_name, medium, language, aliases, platform, year
            FROM titles
            WHERE canonical_id = %s
            """,
            (canonical_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def get_price_series(conn: psycopg.Connection, canonical_id: str) -> list[dict]:
    """Get price series for a title."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date, hype_index, price
            FROM daily_prices
            WHERE canonical_id = %s
            ORDER BY date
            """,
            (canonical_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def _parse_period_days(period: str) -> int:
    """Convert period string like '7d', '30d' to number of days."""
    period = period.strip().lower()
    if period.endswith("d"):
        try:
            return int(period[:-1])
        except ValueError:
            pass
    return 7


def get_trending(conn: psycopg.Connection, period: str = "7d", limit: int = 10) -> list[dict]:
    """Get top titles by absolute hype index change over the period."""
    days = _parse_period_days(period)
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (canonical_id)
                    canonical_id, date, price, hype_index
                FROM daily_prices
                ORDER BY canonical_id, date DESC
            ),
            past AS (
                SELECT DISTINCT ON (dp.canonical_id)
                    dp.canonical_id, dp.date, dp.price, dp.hype_index
                FROM daily_prices dp
                JOIN latest l ON dp.canonical_id = l.canonical_id
                WHERE dp.date <= l.date - %s
                ORDER BY dp.canonical_id, dp.date DESC
            )
            SELECT
                l.canonical_id,
                t.canonical_name,
                t.medium,
                CASE WHEN p.price > 0 THEN round(((l.price - p.price) / p.price * 100)::numeric, 2) ELSE 0 END AS price_change_pct,
                round((l.hype_index - COALESCE(p.hype_index, 0))::numeric, 4) AS hype_change,
                round(l.price::numeric, 2) AS current_price,
                round(l.hype_index::numeric, 4) AS current_hype
            FROM latest l
            JOIN titles t ON t.canonical_id = l.canonical_id
            LEFT JOIN past p ON p.canonical_id = l.canonical_id
            ORDER BY ABS(l.hype_index - COALESCE(p.hype_index, 0)) DESC
            LIMIT %s
            """,
            (days, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_top_gainers(conn: psycopg.Connection, period: str = "7d", limit: int = 10) -> list[dict]:
    """Get top titles by price % increase."""
    days = _parse_period_days(period)
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (canonical_id)
                    canonical_id, date, price, hype_index
                FROM daily_prices
                ORDER BY canonical_id, date DESC
            ),
            past AS (
                SELECT DISTINCT ON (dp.canonical_id)
                    dp.canonical_id, dp.date, dp.price, dp.hype_index
                FROM daily_prices dp
                JOIN latest l ON dp.canonical_id = l.canonical_id
                WHERE dp.date <= l.date - %s
                ORDER BY dp.canonical_id, dp.date DESC
            )
            SELECT
                l.canonical_id,
                t.canonical_name,
                t.medium,
                CASE WHEN p.price > 0 THEN round(((l.price - p.price) / p.price * 100)::numeric, 2) ELSE 0 END AS price_change_pct,
                round((l.hype_index - COALESCE(p.hype_index, 0))::numeric, 4) AS hype_change,
                round(l.price::numeric, 2) AS current_price,
                round(l.hype_index::numeric, 4) AS current_hype
            FROM latest l
            JOIN titles t ON t.canonical_id = l.canonical_id
            LEFT JOIN past p ON p.canonical_id = l.canonical_id
            WHERE p.price IS NOT NULL AND p.price > 0
            ORDER BY (l.price - p.price) / p.price DESC
            LIMIT %s
            """,
            (days, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_top_losers(conn: psycopg.Connection, period: str = "7d", limit: int = 10) -> list[dict]:
    """Get top titles by price % decrease."""
    days = _parse_period_days(period)
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (canonical_id)
                    canonical_id, date, price, hype_index
                FROM daily_prices
                ORDER BY canonical_id, date DESC
            ),
            past AS (
                SELECT DISTINCT ON (dp.canonical_id)
                    dp.canonical_id, dp.date, dp.price, dp.hype_index
                FROM daily_prices dp
                JOIN latest l ON dp.canonical_id = l.canonical_id
                WHERE dp.date <= l.date - %s
                ORDER BY dp.canonical_id, dp.date DESC
            )
            SELECT
                l.canonical_id,
                t.canonical_name,
                t.medium,
                CASE WHEN p.price > 0 THEN round(((l.price - p.price) / p.price * 100)::numeric, 2) ELSE 0 END AS price_change_pct,
                round((l.hype_index - COALESCE(p.hype_index, 0))::numeric, 4) AS hype_change,
                round(l.price::numeric, 2) AS current_price,
                round(l.hype_index::numeric, 4) AS current_hype
            FROM latest l
            JOIN titles t ON t.canonical_id = l.canonical_id
            LEFT JOIN past p ON p.canonical_id = l.canonical_id
            WHERE p.price IS NOT NULL AND p.price > 0
            ORDER BY (l.price - p.price) / p.price ASC
            LIMIT %s
            """,
            (days, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_metrics_series(conn: psycopg.Connection, canonical_id: str) -> list[dict]:
    """Get daily metric values (mentions_count, engagement_score) for a title."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT metric_date AS date, metric_name, value
            FROM daily_metrics
            WHERE canonical_id = %s
              AND metric_name IN ('mentions_count', 'engagement_score')
            ORDER BY metric_date
            """,
            (canonical_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def list_titles_sorted(
    conn: psycopg.Connection,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    medium: str | None = None,
    sort: str = "name",
) -> tuple[list[dict], int]:
    """List titles with pagination, filters, and sorting by metrics."""
    offset = (page - 1) * limit
    where_clauses: list[str] = []
    params: list[object] = []
    if search:
        pattern = f"%{search}%"
        where_clauses.append(
            "(t.canonical_name ILIKE %s OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(t.aliases) a WHERE a ILIKE %s))"
        )
        params.extend([pattern, pattern])
    if medium:
        where_clauses.append("t.medium = %s")
        params.append(medium)
    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

    # Determine sort clause
    sort_map = {
        "name": "t.canonical_name ASC",
        "hype": "COALESCE(dp.hype_index, 0) DESC",
        "price": "COALESCE(dp.price, 0) DESC",
    }
    order_sql = sort_map.get(sort, "t.canonical_name ASC")

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM titles t WHERE {where_sql}", params)
        total = cur.fetchone()["count"]
        cur.execute(
            f"""
            SELECT t.canonical_id, t.canonical_name, t.medium, t.language,
                   t.aliases, t.platform, t.year,
                   dp.price AS latest_price, dp.hype_index AS latest_hype,
                   dp_prev.price AS prev_price
            FROM titles t
            LEFT JOIN LATERAL (
                SELECT price, hype_index FROM daily_prices
                WHERE canonical_id = t.canonical_id
                ORDER BY date DESC LIMIT 1
            ) dp ON TRUE
            LEFT JOIN LATERAL (
                SELECT price FROM daily_prices
                WHERE canonical_id = t.canonical_id
                ORDER BY date DESC OFFSET 1 LIMIT 1
            ) dp_prev ON TRUE
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows], total
