"""Postgres-backed Checkpointer (DES-0004-C).

Implements the existing Checkpointer port — traveler snapshots + optional raw
graph-state blobs. Schema is created lazily on first use.

Requires ``psycopg`` (v3). ``src/`` never imports this module.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from src.domain.traveler import DigitalTraveler

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hextory_travelers (
    key TEXT PRIMARY KEY,
    snapshot JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS hextory_raw_state (
    key TEXT PRIMARY KEY,
    state JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def database_url_from_env() -> str:
    url = os.environ.get("HEXTORY_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "HEXTORY_DATABASE_URL is required for PostgresCheckpointer "
            "(example: postgresql://hextory:hextory@localhost:5432/hextory)"
        )
    return url


class PostgresCheckpointer:
    """Persist travelers as JSONB rows keyed by traveler_id / checkpoint key."""

    def __init__(self, dsn: Optional[str] = None, *, conn: Any = None) -> None:
        """
        Pass ``dsn`` for normal use, or an open ``conn`` (psycopg connection /
        test double) for unit tests that avoid a live database.
        """
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
                "psycopg is required for PostgresCheckpointer; "
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

    def save(self, key: str, traveler: DigitalTraveler) -> str:
        self.ensure_schema()
        snapshot = traveler.model_dump(mode="json")
        ref = f"postgres://travelers/{key}"
        traveler.checkpoint_ref = ref
        snapshot["checkpoint_ref"] = ref
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hextory_travelers (key, snapshot, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                  SET snapshot = EXCLUDED.snapshot,
                      updated_at = NOW()
                """,
                (key, json.dumps(snapshot)),
            )
        return ref

    def load(self, key: str) -> Optional[DigitalTraveler]:
        self.ensure_schema()
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT snapshot FROM hextory_travelers WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        return DigitalTraveler.model_validate(data)

    def save_raw(self, key: str, state: dict[str, Any]) -> str:
        self.ensure_schema()
        ref = f"postgres://raw/{key}"
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hextory_raw_state (key, state, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                  SET state = EXCLUDED.state,
                      updated_at = NOW()
                """,
                (key, json.dumps(state)),
            )
        return ref

    def load_raw(self, key: str) -> Optional[dict[str, Any]]:
        self.ensure_schema()
        conn = self._connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT state FROM hextory_raw_state WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        return dict(data) if isinstance(data, dict) else None
