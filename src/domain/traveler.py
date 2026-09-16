"""DigitalTraveler and related value objects (DES-0002-G).

routing_history is append-only: helpers never rewrite prior entries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.domain.statuses import QualityResult, RoutingDecision, TravelerStatus

DEFAULT_MAX_REWORK = 3


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactRef(BaseModel):
    kind: str
    uri: str
    digest: Optional[str] = None


class DefectReport(BaseModel):
    code: str
    summary: str
    details: str = ""
    suggested_rework_node: Optional[str] = None


class CriteriaResult(BaseModel):
    ac_id: str
    passed: bool
    detail: str = ""


class QualityReport(BaseModel):
    report_id: str
    at: datetime
    result: QualityResult
    criteria_results: list[CriteriaResult] = Field(default_factory=list)
    defect: Optional[DefectReport] = None


class RoutingEvent(BaseModel):
    seq: int
    at: datetime
    node_id: str
    decision: RoutingDecision
    notes: str = ""
    actor: str = "system"


class TraceEntry(BaseModel):
    req_id: Optional[str] = None
    des_id: Optional[str] = None
    test_id: Optional[str] = None
    note: Optional[str] = None


class AuditEvent(BaseModel):
    at: datetime
    actor: str
    action: str
    detail: str = ""


class DigitalTraveler(BaseModel):
    """Mutable state object that moves through factory nodes."""

    traveler_id: str
    workflow_id: str
    sdd_id: str
    status: TravelerStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    quality_reports: list[QualityReport] = Field(default_factory=list)
    rework_count: int = 0
    max_rework: int = DEFAULT_MAX_REWORK
    routing_history: list[RoutingEvent] = Field(default_factory=list)
    trace: list[TraceEntry] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)
    idempotency_key: Optional[str] = None
    checkpoint_ref: Optional[str] = None
    last_defect: Optional[DefectReport] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def append_routing(
        self,
        *,
        node_id: str,
        decision: RoutingDecision,
        notes: str = "",
        actor: str = "system",
        at: Optional[datetime] = None,
    ) -> RoutingEvent:
        """Append a RoutingEvent. Never mutates prior history entries."""
        seq = len(self.routing_history) + 1
        event = RoutingEvent(
            seq=seq,
            at=at or utc_now(),
            node_id=node_id,
            decision=decision,
            notes=notes,
            actor=actor,
        )
        # Copy-on-append keeps prior list identity-safe for tests that snapshot.
        self.routing_history = [*self.routing_history, event]
        self.updated_at = event.at
        return event

    def touch(self, at: Optional[datetime] = None) -> None:
        self.updated_at = at or utc_now()
