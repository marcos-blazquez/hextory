"""TEST-0011 / TEST-0012 — Gatekeeper denies missing / non-Approved sdd_id."""

from __future__ import annotations

from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


def test_test_0011_denies_missing_sdd_id():
    """TEST-0011: missing sdd_id → deny."""
    gk = PolicyGatekeeper(FakeSddStatusReader({"DES-0002": SddStatus.APPROVED}))
    decision = gk.check(None)
    assert decision.allowed is False
    assert "missing" in decision.reason.lower()

    decision2 = gk.check("")
    assert decision2.allowed is False


def test_test_0012_denies_non_approved_sdd():
    """TEST-0012: Draft / Unknown → deny."""
    gk = PolicyGatekeeper(
        FakeSddStatusReader(
            {
                "DES-0002": SddStatus.APPROVED,
                "DES-9999": SddStatus.DRAFT,
            }
        )
    )
    assert gk.check("DES-0002").allowed is True
    draft = gk.check("DES-9999")
    assert draft.allowed is False
    assert "Approved" in draft.reason

    unknown = gk.check("DES-404")
    assert unknown.allowed is False
