"""CLI: python -m apps.worker.sync_titles — sync registry to Postgres titles table."""

import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from hypex_core import load_registry
from hypex_core.db import get_connection_string
from hypex_core.utils import merge_aliases, slugify


def ensure_schema(conn: psycopg.Connection) -> None:
    """Ensure titles table exists with updated_at."""
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
        # Add updated_at if table existed without it
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'titles' AND column_name = 'updated_at'
                ) THEN
                    ALTER TABLE titles ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();
                END IF;
            END $$;
        """)
    conn.commit()


def run() -> None:
    """Read registry, merge aliases, upsert into Postgres."""
    root = Path(__file__).resolve().parent.parent.parent
    titles_path = root / "data" / "registry" / "titles.csv"
    aliases_path = root / "data" / "registry" / "aliases.json"
    titles, alias_entries = load_registry(str(titles_path), str(aliases_path))

    # Build alias map: canonical_id -> list of aliases from aliases.json
    alias_by_cid: dict[str, list[str]] = {}
    for ae in alias_entries:
        lst = alias_by_cid.setdefault(ae.canonical_id, [])
        lst.append(ae.alias)

    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            for t in titles:
                cid = t.canonical_id.strip() or slugify(t.canonical_name)
                if not cid:
                    continue
                json_aliases = alias_by_cid.get(cid, [])
                merged = merge_aliases(t.aliases, json_aliases)
                cur.execute(
                    """
                    INSERT INTO titles (canonical_id, canonical_name, medium, language, aliases, platform, year, updated_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, now())
                    ON CONFLICT (canonical_id) DO UPDATE SET
                        canonical_name = EXCLUDED.canonical_name,
                        medium = EXCLUDED.medium,
                        language = EXCLUDED.language,
                        aliases = COALESCE(
                            (SELECT jsonb_agg(DISTINCT elem ORDER BY elem)
                             FROM jsonb_array_elements_text(
                                 COALESCE(titles.aliases, '[]'::jsonb) || COALESCE(EXCLUDED.aliases, '[]'::jsonb)
                             ) AS elem),
                            '[]'::jsonb
                        ),
                        platform = EXCLUDED.platform,
                        year = EXCLUDED.year,
                        updated_at = now()
                    """,
                    (
                        cid,
                        t.canonical_name,
                        t.medium,
                        t.language,
                        json.dumps(merged),
                        t.platform,
                        t.year,
                    ),
                )
        conn.commit()
        print(f"Synced {len(titles)} titles")
    finally:
        conn.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
