"""TDD: real IdempotencyInterceptor + QuotaTimeoutInterceptor (DES-0002-H)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.domain.statuses import TravelerStatus
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import GraphRegistry
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.policies.interceptors import (
    IdempotencyInterceptor,
    LoggingInterceptor,
    QuotaTimeoutInterceptor,
    RequestContext,
    DesignDocGateInterceptor,
    run_chain,
)
from src.ports.idempotency import InMemoryIdempotencyStore
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)


def _gw(**kwargs) -> RequestGateway:
    registry = GraphRegistry()
    register_starter(registry)
    reader = FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})
    return RequestGateway(
        gatekeeper=PolicyGatekeeper(reader),
        registry=registry,
        **kwargs,
    )


def test_same_idempotency_key_returns_same_traveler_id_and_status():
    store = InMemoryIdempotencyStore()
    gw = _gw(idempotency_store=store)

    r1 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS", "product": "a"},
        idempotency_key="key-1",
    )
    r2 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS", "product": "b"},
        idempotency_key="key-1",
    )

    assert r1.denied is False
    assert r2.denied is False
    assert r1.traveler.traveler_id == r2.traveler.traveler_id
    assert r1.traveler.status == r2.traveler.status == TravelerStatus.SHIPPED


def test_different_idempotency_keys_create_new_travelers():
    store = InMemoryIdempotencyStore()
    gw = _gw(idempotency_store=store)

    r1 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
        idempotency_key="alpha",
    )
    r2 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
        idempotency_key="beta",
    )

    assert r1.traveler.traveler_id != r2.traveler.traveler_id


def test_denied_run_with_key_is_replayable():
    store = InMemoryIdempotencyStore()
    gw = _gw(idempotency_store=store)

    r1 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-9999",  # unknown → deny
        idempotency_key="deny-key",
    )
    r2 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-9999",
        idempotency_key="deny-key",
    )

    assert r1.denied is True
    assert r2.denied is True
    assert r1.traveler.traveler_id == r2.traveler.traveler_id
    assert r1.traveler.status == r2.traveler.status == TravelerStatus.DENIED
    assert r1.reason == r2.reason


def test_no_key_skips_dedupe():
    store = InMemoryIdempotencyStore()
    gw = _gw(idempotency_store=store)

    r1 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    r2 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert r1.traveler.traveler_id != r2.traveler.traveler_id


def test_quota_denies_when_max_requests_exceeded():
    clock = FakeClock()
    quota = QuotaTimeoutInterceptor(max_requests=2, window_seconds=60.0, clock=clock)
    store = InMemoryIdempotencyStore()
    reader = FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})
    gk = PolicyGatekeeper(reader)
    interceptors = [
        LoggingInterceptor(),
        IdempotencyInterceptor(store),
        quota,
        DesignDocGateInterceptor(gk),
    ]
    registry = GraphRegistry()
    register_starter(registry)
    gw = RequestGateway(
        gatekeeper=gk,
        registry=registry,
        interceptors=interceptors,
        idempotency_store=store,
    )

    assert gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    ).denied is False
    assert gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    ).denied is False
    r3 = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert r3.denied is True
    assert "quota" in r3.reason.lower()


def test_quota_window_resets_with_clock():
    clock = FakeClock()
    quota = QuotaTimeoutInterceptor(max_requests=1, window_seconds=10.0, clock=clock)
    ctx = RequestContext(workflow_id="w", sdd_id="DES-0002")
    assert quota.process(ctx).denied is False
    denied_ctx = RequestContext(workflow_id="w", sdd_id="DES-0002")
    assert quota.process(denied_ctx).denied is True
    clock.advance(11)
    ok_ctx = RequestContext(workflow_id="w", sdd_id="DES-0002")
    assert quota.process(ok_ctx).denied is False


def test_optional_timeout_seconds_recorded_in_metadata():
    clock = FakeClock(datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc))
    quota = QuotaTimeoutInterceptor(max_requests=100, window_seconds=3600, clock=clock)
    ctx = RequestContext(
        workflow_id="w",
        sdd_id="DES-0002",
        payload={"timeout_seconds": 30},
    )
    out = quota.process(ctx)
    assert out.denied is False
    assert out.metadata.get("timeout_seconds") == 30
    assert "deadline" in out.metadata


def test_default_chain_quota_is_generous():
    """Existing suite must not trip default quota."""
    gw = _gw()
    for _ in range(5):
        r = gw.run(
            workflow_id="starter_factory",
            sdd_id="DES-0002",
            payload={"force_quality": "PASS"},
        )
        assert r.denied is False
