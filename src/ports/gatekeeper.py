"""Gatekeeper port — refuse runs without Approved SDD (DES-0002-I)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str = ""
    sdd_id: Optional[str] = None


class Gatekeeper(Protocol):
    def check(self, sdd_id: Optional[str]) -> GateDecision:
        ...
