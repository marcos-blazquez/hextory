"""Rework policy defaults (DES-0002-H): max_rework=3 then escalate."""

from __future__ import annotations

from src.domain.statuses import TravelerStatus
from src.domain.traveler import DEFAULT_MAX_REWORK, DigitalTraveler


def should_escalate(traveler: DigitalTraveler) -> bool:
    """True when rework_count has reached/exceeded max_rework after a FAIL."""
    return traveler.rework_count >= traveler.max_rework


def next_status_after_fail(traveler: DigitalTraveler) -> TravelerStatus:
    if should_escalate(traveler):
        return TravelerStatus.ESCALATED
    return TravelerStatus.REWORK


def default_max_rework() -> int:
    return DEFAULT_MAX_REWORK
