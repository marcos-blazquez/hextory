"""IdempotencyStore port — map idempotency_key → traveler_id (DES-0002-H).

Design choice
-------------
Use a dedicated ``IdempotencyStore`` Protocol rather than overloading Checkpointer
or gateway ``_store``:

* Checkpointer keys by ``traveler_id``; idempotency needs key→traveler_id lookup.
* The interceptor can resolve a prior key without knowing traveler serialization.
* Gateway loads the traveler from its in-process store / Checkpointer after the
  interceptor sets ``RequestContext.replay_traveler_id``.
* Denied runs are stored the same way so replays return the same denial.

Adapters: ``InMemoryIdempotencyStore`` (tests / default) and optional
``FileIdempotencyStore`` under ``.hextory/idempotency/`` in ``adapters/local``.
"""

from __future__ import annotations

from typing import Optional, Protocol


class IdempotencyStore(Protocol):
    def get(self, key: str) -> Optional[str]:
        """Return prior traveler_id for key, or None."""
        ...

    def put(self, key: str, traveler_id: str) -> None:
        """Remember traveler_id for key (first write wins for stability)."""
        ...

    def delete(self, key: str) -> None:
        """Drop a key (e.g. orphaned mapping whose traveler is gone)."""
        ...


class InMemoryIdempotencyStore:
    """Process-local map; suitable for tests and default CLI in-memory mode."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def put(self, key: str, traveler_id: str) -> None:
        # First write wins — replay must not overwrite with a newer id.
        if key not in self._data:
            self._data[key] = traveler_id

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
