"""Shared Postgres connection for HypeX."""

import os
from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg.rows import dict_row


def get_connection_string() -> str:
    """Build connection string from env. Normalizes postgresql+psycopg:// for psycopg."""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://hypex:hypex@localhost:5432/hypex",
    )
    return url.replace("postgresql+psycopg", "postgresql")


@contextmanager
def get_db() -> Generator[psycopg.Connection, None, None]:
    """Yield a DB connection with auto-commit/rollback."""
    conn = psycopg.connect(get_connection_string(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
