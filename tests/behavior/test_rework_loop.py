"""Behavior: Quality FAIL rework and escalation (TEST-0015 / TEST-0016 / TEST-0017)."""

from __future__ import annotations

from src.domain.statuses import TravelerStatus
from src.gateway.request_gateway import RequestGateway
from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


def _gw(starter_registry) -> RequestGateway:
    return RequestGateway(
        gatekeeper=PolicyGatekeeper(FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})),
        registry=starter_registry,
    )


def test_given_fail_then_pass_when_run_then_rework_then_ship(starter_registry):
    """
    Given fail_until_rework=1 (first quality FAIL, then PASS)
    When the starter workflow runs
    Then rework_count increments, assembly is re-entered, and final status is shipped
    """
    # Given / When
    result = _gw(starter_registry).run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"fail_until_rework": 1, "product": "bolt"},
    )

    # Then
    t = result.traveler
    assert result.denied is False
    assert t.rework_count == 1
    assert t.status == TravelerStatus.SHIPPED
    assembly_enters = [
        e for e in t.routing_history if e.node_id == "assembly" and e.decision.value == "enter"
    ]
    assert len(assembly_enters) >= 2  # initial + rework
    assert any(e.decision.value == "rework" for e in t.routing_history)


def test_given_three_fails_when_fourth_would_be_needed_then_escalated(starter_registry):
    """
    Given force_quality=FAIL (always fail) and default max_rework=3
    When the starter workflow runs
    Then after 3 FAILs status=escalated and packaging never runs
    """
    # Given / When
    result = _gw(starter_registry).run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "FAIL", "product": "nail"},
    )

    # Then (TEST-0016)
    t = result.traveler
    assert t.rework_count == 3
    assert t.status == TravelerStatus.ESCALATED
    assert any(e.decision.value == "escalate" for e in t.routing_history)
    # TEST-0017: no packaging / ship
    assert all(e.node_id != "packaging" for e in t.routing_history)
    assert t.status != TravelerStatus.SHIPPED
    assert not any(a.kind == "ship_manifest" for a in t.artifact_refs)


def test_given_fail_path_when_inspecting_then_shipped_unreachable(starter_registry):
    """
    Given a run that ends in FAIL/escalated
    When we inspect terminal state
    Then shipped is unreachable
    """
    result = _gw(starter_registry).run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "FAIL"},
    )
    assert result.traveler.status == TravelerStatus.ESCALATED
    decisions = {e.decision.value for e in result.traveler.routing_history}
    assert "ship" not in decisions
