"""Behavior: starter PASS path assembly → quality → packaging (TEST-0014)."""

from __future__ import annotations

from src.domain.statuses import TravelerStatus
from src.gateway.request_gateway import RequestGateway
from src.policies.gate import PolicyGatekeeper
from tests.conftest import FakeSddStatusReader
from src.ports.sdd_status import SddStatus


def test_given_approved_sdd_when_quality_passes_then_shipped(
    starter_registry,
):
    """
    Given an Approved SDD and starter_factory workflow
    When quality is forced to PASS
    Then the traveler reaches packaging and status=shipped
    """
    # Given
    gw = RequestGateway(
        gatekeeper=PolicyGatekeeper(FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})),
        registry=starter_registry,
    )

    # When
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"product": "widget", "force_quality": "PASS"},
    )

    # Then
    assert result.denied is False
    t = result.traveler
    assert t.status == TravelerStatus.SHIPPED
    node_seq = [e.node_id for e in t.routing_history]
    assert "gateway" in node_seq
    assert "assembly" in node_seq
    assert "quality" in node_seq
    assert "packaging" in node_seq
    assert any(a.kind == "ship_manifest" for a in t.artifact_refs)
