"""TEST-0017 related unit: packaging invariant; rework helpers."""

from __future__ import annotations

import pytest

from src.departments.packaging import PackagingInvariantError, run_packaging
from src.departments.quality import run_quality
from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.policies.rework import default_max_rework, should_escalate


def _traveler(**kwargs) -> DigitalTraveler:
    base = dict(
        traveler_id="trv_u",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.ACCEPTED,
        payload={"assembled": True, "force_quality": "FAIL"},
        max_rework=3,
    )
    base.update(kwargs)
    return DigitalTraveler(**base)


def test_test_0017_packaging_rejects_after_fail():
    """TEST-0017: packaging never runs on FAIL."""
    t = _traveler()
    t = run_quality(t)
    assert t.quality_reports[-1].result.value == "FAIL"
    with pytest.raises(PackagingInvariantError):
        run_packaging(t)


def test_default_max_rework_is_three():
    assert default_max_rework() == 3


def test_should_escalate_at_max():
    t = _traveler(rework_count=3, max_rework=3)
    assert should_escalate(t) is True
    t2 = _traveler(rework_count=2, max_rework=3)
    assert should_escalate(t2) is False
