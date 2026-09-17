"""Postgres-backed IdempotencyStore (DES-0004 adapter concern)."""

from __future__ import annotations

import os
from typing import Any, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hextory_idempotency (
    key TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def database_url_from_env() -> str:
    url = os.environ.get("HEXTORY_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("HEXTORY_DATABASE_URL is required for PostgresIdempotencyStore")
    return url


class PostgresIdempotencyStore:
    """Persist idempotency_key → traveler_id in Postgres (first write wins)."""

    def __init__(self, dsn: Optional[str] = None, *, conn: Any = None) -> None:
        if conn is not None:
            self._conn = conn
            self._owns_conn = False
            self._dsn = None
        else:
            self._dsn = dsn or database_url_from_env()
            self._conn = None
            self._owns_conn = True
        self._schema_ready = False

    def _connect(self) -> Any:
        if self._conn is not None and not self._owns_conn:
            return self._conn
        if self._conn is not None and not getattr(self._conn, "closed", False):
            return self._conn
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "psycopg is required for PostgresIdempotencyStore; "
                'install with: pip install -e ".[onprem]"'
            ) from exc
        self._conn = psycopg.connect(self._dsn, autocommit=True)
        return self._conn

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        self._schema_ready = True

    def close(self) -> None:
        if self._owns_conn and self._conn is not None:
            self._conn.close()
            self._conn = None

    def get(self, key: str) -> Optional[str]:
        self.ensure_schema()
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT traveler_id FROM hextory_idempotency WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()
        return str(row[0]) if row else None

    def put(self, key: str, traveler_id: str) -> None:
        self.ensure_schema()
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hextory_idempotency (key, traveler_id)
                VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
                """,
                (key, traveler_id),
            )

    def delete(self, key: str) -> None:
        self.ensure_schema()
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hextory_idempotency WHERE key = %s", (key,))
