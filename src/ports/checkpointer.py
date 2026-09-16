"""Checkpointer port — optional persistence at graph compile (DES-0002-J).

Core never imports MemorySaver or other adapter types.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

from src.domain.traveler import DigitalTraveler


class Checkpointer(Protocol):
    def save(self, key: str, traveler: DigitalTraveler) -> str:
        """Persist traveler state; return checkpoint_ref."""
        ...

    def load(self, key: str) -> Optional[DigitalTraveler]:
        """Load traveler by key, or None if missing."""
        ...

    def save_raw(self, key: str, state: dict[str, Any]) -> str:
        """Optional raw graph-state blob for adapter-specific engines."""
        ...

    def load_raw(self, key: str) -> Optional[dict[str, Any]]:
        ...
