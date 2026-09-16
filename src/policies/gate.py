"""Pure gate policy + default Gatekeeper implementation (DES-0002-I)."""

from __future__ import annotations

from typing import Optional

from src.ports.gatekeeper import GateDecision
from src.ports.sdd_status import SddStatus, SddStatusReader


class PolicyGatekeeper:
    """Refuse when sdd_id missing OR status ≠ Approved. Fail closed on ERROR/UNKNOWN."""

    def __init__(self, status_reader: SddStatusReader) -> None:
        self._reader = status_reader

    def check(self, sdd_id: Optional[str]) -> GateDecision:
        if not sdd_id or not str(sdd_id).strip():
            return GateDecision(
                allowed=False,
                reason="missing sdd_id",
                sdd_id=sdd_id,
            )
        status = self._reader.get_status(sdd_id)
        if status == SddStatus.APPROVED:
            return GateDecision(allowed=True, reason="Approved", sdd_id=sdd_id)
        return GateDecision(
            allowed=False,
            reason=f"sdd_id {sdd_id} status is {status.value}, not Approved",
            sdd_id=sdd_id,
        )
