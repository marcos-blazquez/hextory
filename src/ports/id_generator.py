"""ID generation port — opaque string ids for travelers/reports."""

from __future__ import annotations

import uuid
from typing import Protocol


class IdGenerator(Protocol):
    def new_id(self, prefix: str = "") -> str:
        ...


class UuidGenerator:
    def new_id(self, prefix: str = "") -> str:
        uid = str(uuid.uuid4())
        return f"{prefix}{uid}" if prefix else uid
