"""Behavior: Gatekeeper denial — no assembly entry (AC-02 / TEST-0011 / TEST-0012)."""

from __future__ import annotations

from src.domain.statuses import TravelerStatus
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import GraphRegistry
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


def _gateway(mapping: dict[str, SddStatus]) -> RequestGateway:
    registry = GraphRegistry()
    register_starter(registry)
    return RequestGateway(
        gatekeeper=PolicyGatekeeper(FakeSddStatusReader(mapping)),
        registry=registry,
    )


def test_given_missing_sdd_when_run_then_denied_without_assembly():
    """
    Given a run request with no sdd_id
    When the gateway processes the request
    Then the traveler is denied and routing_history has no assembly entry
    """
    # Given
    gw = _gateway({"DES-0002": SddStatus.APPROVED})

    # When
    result = gw.run(workflow_id="starter_factory", sdd_id=None, payload={"product": "x"})

    # Then
    assert result.denied is True
    assert result.traveler.status == TravelerStatus.DENIED
    nodes = [e.node_id for e in result.traveler.routing_history]
    assert "assembly" not in nodes
    assert any(e.decision.value == "deny" for e in result.traveler.routing_history)


def test_given_draft_sdd_when_run_then_denied_without_assembly():
    """
    Given an sdd_id whose status is Draft
    When the gateway processes the request
    Then the run is denied and assembly never runs
    """
    # Given
    gw = _gateway({"DES-9999": SddStatus.DRAFT, "DES-0002": SddStatus.APPROVED})

    # When
    result = gw.run(workflow_id="starter_factory", sdd_id="DES-9999")

    # Then
    assert result.denied is True
    assert result.traveler.status == TravelerStatus.DENIED
    assert all(e.node_id != "assembly" for e in result.traveler.routing_history)
