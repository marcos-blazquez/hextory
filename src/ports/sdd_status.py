"""SddStatusReader port (Q-GATE-1): resolve whether an SDD is Approved.

Fail closed: read/parse errors and unknown ids → not Approved.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Protocol


class SddStatus(str, Enum):
    APPROVED = "Approved"
    DRAFT = "Draft"
    UNKNOWN = "Unknown"
    ERROR = "Error"


class SddStatusReader(Protocol):
    def get_status(self, sdd_id: str) -> SddStatus:
        """Return status for sdd_id. Must never raise for missing ids — use UNKNOWN/ERROR."""
        ...

    def is_approved(self, sdd_id: str) -> bool:
        return self.get_status(sdd_id) == SddStatus.APPROVED
