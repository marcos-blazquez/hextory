"""Parity: pure vs LangGraph runners (skip cleanly if langgraph missing)."""

from __future__ import annotations

import pytest

from src.domain.statuses import RoutingDecision, TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import Edge, GraphRegistry, WorkflowDefinition
from src.graphs.runtime import PureGraphRunner
from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader

langgraph = pytest.importorskip("langgraph")  # noqa: F841 — skip module if missing

from adapters.local.langgraph_runtime import LangGraphRunner  # noqa: E402
from adapters.local.memory_checkpointer import MemoryCheckpointer  # noqa: E402


def _gate() -> PolicyGatekeeper:
    return PolicyGatekeeper(FakeSddStatusReader({"DES-0002": SddStatus.APPROVED}))


def _gw(registry: GraphRegistry, runner) -> RequestGateway:
    return RequestGateway(gatekeeper=_gate(), registry=registry, runner=runner)


def _stamp_node(traveler: DigitalTraveler) -> DigitalTraveler:
    traveler.append_routing(node_id="stamp", decision=RoutingDecision.ENTER, notes="custom stamp")
    traveler.payload = {**traveler.payload, "stamped": True}
    traveler.status = TravelerStatus.SHIPPED
    traveler.append_routing(node_id="stamp", decision=RoutingDecision.SHIP, notes="custom ship")
    return traveler


def _prep_node(traveler: DigitalTraveler) -> DigitalTraveler:
    traveler.append_routing(node_id="prep", decision=RoutingDecision.ENTER)
    traveler.payload = {**traveler.payload, "prepared": True}
    traveler.append_routing(node_id="prep", decision=RoutingDecision.PASS)
    return traveler


def _custom_registry() -> GraphRegistry:
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
    return registry


@pytest.mark.parametrize(
    "payload,expected_status,expected_rework",
    [
        ({"force_quality": "PASS", "product": "widget"}, TravelerStatus.SHIPPED, 0),
        ({"force_quality": "FAIL", "product": "nail"}, TravelerStatus.ESCALATED, 3),
        ({"fail_until_rework": 1, "product": "bolt"}, TravelerStatus.SHIPPED, 1),
    ],
)
def test_parity_starter_terminal_and_rework(
    starter_registry,
    payload,
    expected_status,
    expected_rework,
):
    """Pure and LangGraph paths agree on terminal status / rework_count."""
    pure = _gw(starter_registry, PureGraphRunner()).run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload=dict(payload),
    )
    lg = _gw(starter_registry, LangGraphRunner()).run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload=dict(payload),
    )
    assert pure.denied is False and lg.denied is False
    assert pure.traveler.status == expected_status
    assert lg.traveler.status == expected_status
    assert pure.traveler.rework_count == expected_rework
    assert lg.traveler.rework_count == expected_rework
    assert pure.traveler.status == lg.traveler.status
    assert pure.traveler.rework_count == lg.traveler.rework_count


def test_parity_custom_registry_node():
    """Open-ended custom node works under both runners without editing departments."""
    registry = _custom_registry()
    pure = _gw(registry, PureGraphRunner()).run(
        workflow_id="custom_stamp_line",
        sdd_id="DES-0002",
        payload={"sku": "X1"},
    )
    lg = _gw(registry, LangGraphRunner()).run(
        workflow_id="custom_stamp_line",
        sdd_id="DES-0002",
        payload={"sku": "X1"},
    )
    assert pure.traveler.status == TravelerStatus.SHIPPED
    assert lg.traveler.status == TravelerStatus.SHIPPED
    assert pure.traveler.payload.get("stamped") is True
    assert lg.traveler.payload.get("stamped") is True
    assert pure.traveler.rework_count == lg.traveler.rework_count == 0


def test_langgraph_uses_checkpointer_port(starter_registry):
    """Traveler saves go through our Checkpointer port (not LangGraph MemorySaver)."""
    cp = MemoryCheckpointer()
    gw = RequestGateway(
        gatekeeper=_gate(),
        registry=starter_registry,
        checkpointer=cp,
        runner=LangGraphRunner(),
    )
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.checkpoint_ref and result.traveler.checkpoint_ref.startswith("mem://")
    loaded = cp.load(result.traveler.traveler_id)
    assert loaded is not None
    assert loaded.status == TravelerStatus.SHIPPED
