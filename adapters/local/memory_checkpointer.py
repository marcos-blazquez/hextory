"""In-memory checkpointer (MemorySaver-style) behind the Checkpointer port."""

from __future__ import annotations

from typing import Any, Optional

from src.domain.traveler import DigitalTraveler


class MemoryCheckpointer:
    """Process-local traveler + raw state store. Core never sees this type name."""

    def __init__(self) -> None:
        self._travelers: dict[str, DigitalTraveler] = {}
        self._raw: dict[str, dict[str, Any]] = {}

    def save(self, key: str, traveler: DigitalTraveler) -> str:
        # Store a deep copy via model_copy to avoid accidental shared mutation.
        self._travelers[key] = traveler.model_copy(deep=True)
        return f"mem://{key}"

    def load(self, key: str) -> Optional[DigitalTraveler]:
        t = self._travelers.get(key)
        return t.model_copy(deep=True) if t is not None else None

    def save_raw(self, key: str, state: dict[str, Any]) -> str:
        self._raw[key] = dict(state)
        return f"mem-raw://{key}"

    def load_raw(self, key: str) -> Optional[dict[str, Any]]:
        raw = self._raw.get(key)
        return dict(raw) if raw is not None else None
