"""TEST-0013 — DigitalTraveler Draft fields + append-only routing_history."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.domain.statuses import RoutingDecision, TravelerStatus
from src.domain.traveler import DEFAULT_MAX_REWORK, DigitalTraveler, RoutingEvent


REQUIRED_FIELDS = {
    "traveler_id",
    "workflow_id",
    "sdd_id",
    "status",
    "payload",
    "artifact_refs",
    "quality_reports",
    "rework_count",
    "max_rework",
    "routing_history",
    "trace",
    "audit",
    "created_at",
    "updated_at",
}


def _make_traveler(**kwargs) -> DigitalTraveler:
    base = dict(
        traveler_id="trv_1",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.ACCEPTED,
    )
    base.update(kwargs)
    return DigitalTraveler(**base)


def test_test_0013_has_draft_fields():
    """TEST-0013: traveler includes DES-0002-G field set."""
    t = _make_traveler()
    for name in REQUIRED_FIELDS:
        assert hasattr(t, name), f"missing field {name}"
    assert t.max_rework == DEFAULT_MAX_REWORK
    assert t.rework_count == 0
    assert t.routing_history == []
    assert t.idempotency_key is None
    assert t.checkpoint_ref is None
    assert t.last_defect is None


def test_test_0013_routing_history_append_only():
    """TEST-0013: append never rewrites prior RoutingEvent entries."""
    t = _make_traveler()
    e1 = t.append_routing(node_id="gateway", decision=RoutingDecision.ACCEPT, notes="ok")
    snapshot = [e.model_copy(deep=True) for e in t.routing_history]
    e2 = t.append_routing(node_id="assembly", decision=RoutingDecision.ENTER)

    assert e1.seq == 1
    assert e2.seq == 2
    assert len(t.routing_history) == 2
    # Prior entry unchanged
    assert t.routing_history[0].model_dump() == snapshot[0].model_dump()
    assert t.routing_history[0].node_id == "gateway"
    assert t.routing_history[1].node_id == "assembly"
