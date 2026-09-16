"""Behavior: open-ended registry — custom node/edge without editing departments (TEST-0018)."""

from __future__ import annotations

from src.domain.statuses import RoutingDecision, TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import Edge, GraphRegistry, WorkflowDefinition
from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


def _stamp_node(traveler: DigitalTraveler) -> DigitalTraveler:
    traveler.append_routing(
        node_id="stamp",
        decision=RoutingDecision.ENTER,
        notes="custom stamp",
    )
    traveler.payload = {**traveler.payload, "stamped": True}
    traveler.status = TravelerStatus.SHIPPED
    traveler.append_routing(
        node_id="stamp",
        decision=RoutingDecision.SHIP,
        notes="custom ship",
    )
    return traveler


def _prep_node(traveler: DigitalTraveler) -> DigitalTraveler:
    traveler.append_routing(node_id="prep", decision=RoutingDecision.ENTER)
    traveler.payload = {**traveler.payload, "prepared": True}
    traveler.append_routing(node_id="prep", decision=RoutingDecision.PASS)
    return traveler


def test_given_custom_workflow_when_registered_then_runs_without_editing_departments():
    """
    Given a new workflow with custom prep → stamp nodes registered at runtime
    When the gateway runs that workflow_id
    Then custom nodes execute and departments/ core files are untouched
    """
    # Given
    registry = GraphRegistry()
    wf = WorkflowDefinition(
        workflow_id="custom_stamp_line",
        sdd_id="DES-0002",
        entry_node="prep",
    )
    wf.register_node("prep", _prep_node)
    wf.register_node("stamp", _stamp_node)
    wf.register_edge(Edge(source="prep", target="stamp", label="to_stamp"))
    registry.register(wf)

    gw = RequestGateway(
        gatekeeper=PolicyGatekeeper(FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})),
        registry=registry,
    )

    # When
    result = gw.run(
        workflow_id="custom_stamp_line",
        sdd_id="DES-0002",
        payload={"sku": "X1"},
    )

    # Then
    assert result.denied is False
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.payload.get("stamped") is True
    assert result.traveler.payload.get("prepared") is True
    nodes = [e.node_id for e in result.traveler.routing_history]
    assert "prep" in nodes and "stamp" in nodes
