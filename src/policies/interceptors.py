"""Interceptor chain policy (DES-0002-H).

Default order: logging/trace → idempotency → quota/timeout → design-doc gate → handoff.

Idempotency uses ``IdempotencyStore`` (see ``src/ports/idempotency.py``) rather than
Checkpointer: the interceptor resolves key→traveler_id; the gateway loads and
returns that traveler (including prior denials).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from src.ports.clock import Clock, SystemClock
from src.ports.gatekeeper import GateDecision, Gatekeeper
from src.ports.idempotency import IdempotencyStore, InMemoryIdempotencyStore

# Generous defaults so existing tests / CLI smoke stay usable.
DEFAULT_MAX_REQUESTS = 10_000
DEFAULT_QUOTA_WINDOW_SECONDS = 3600.0


@dataclass
class RequestContext:
    """Mutable request context passed through the interceptor chain."""

    workflow_id: str
    sdd_id: Optional[str]
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    max_rework: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    denied: bool = False
    denial_reason: str = ""
    log: list[str] = field(default_factory=list)
    # Set by IdempotencyInterceptor when a prior result exists for the key.
    replay_traveler_id: Optional[str] = None


class Interceptor(Protocol):
    name: str

    def process(self, ctx: RequestContext) -> RequestContext:
        ...


class LoggingInterceptor:
    name = "logging"

    def process(self, ctx: RequestContext) -> RequestContext:
        ctx.log.append(
            f"logging: workflow={ctx.workflow_id} sdd={ctx.sdd_id}"
        )
        ctx.metadata["logged"] = True
        return ctx


class IdempotencyInterceptor:
    """Dedupe by idempotency_key when provided; replay prior traveler_id."""

    name = "idempotency"

    def __init__(self, store: Optional[IdempotencyStore] = None) -> None:
        self._store: IdempotencyStore = store or InMemoryIdempotencyStore()

    @property
    def store(self) -> IdempotencyStore:
        return self._store

    def process(self, ctx: RequestContext) -> RequestContext:
        key = ctx.idempotency_key
        ctx.log.append(f"idempotency: key={key}")
        if not key:
            return ctx
        prior = self._store.get(key)
        if prior:
            ctx.replay_traveler_id = prior
            ctx.metadata["idempotent_replay"] = True
            ctx.log.append(f"idempotency: replay traveler_id={prior}")
        return ctx


class QuotaTimeoutInterceptor:
    """Max requests per sliding window + optional per-request timeout metadata.

    Injectable ``clock`` keeps the policy unit-testable. Defaults are generous
    (``DEFAULT_MAX_REQUESTS`` / ``DEFAULT_QUOTA_WINDOW_SECONDS``) so the default
    interceptor chain does not break existing suites.
    """

    name = "quota_timeout"

    def __init__(
        self,
        *,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_QUOTA_WINDOW_SECONDS,
        clock: Optional[Clock] = None,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock: Clock = clock or SystemClock()
        self._hits: list[datetime] = []

    def process(self, ctx: RequestContext) -> RequestContext:
        now = self._clock.now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        cutoff = now - timedelta(seconds=self._window_seconds)
        self._hits = [t for t in self._hits if t >= cutoff]

        if len(self._hits) >= self._max_requests:
            ctx.denied = True
            ctx.denial_reason = (
                f"quota exceeded: max_requests={self._max_requests} "
                f"per {self._window_seconds}s window"
            )
            ctx.log.append(f"quota_timeout: deny {ctx.denial_reason}")
            return ctx

        self._hits.append(now)
        ctx.log.append(
            f"quota_timeout: ok count={len(self._hits)}/{self._max_requests}"
        )

        # Optional per-request timeout from payload → deadline in metadata.
        raw_timeout = ctx.payload.get("timeout_seconds")
        if raw_timeout is None:
            raw_timeout = ctx.metadata.get("timeout_seconds")
        if raw_timeout is not None:
            try:
                seconds = float(raw_timeout)
            except (TypeError, ValueError):
                seconds = None
            if seconds is not None and seconds > 0:
                deadline = now + timedelta(seconds=seconds)
                ctx.metadata["timeout_seconds"] = seconds
                ctx.metadata["deadline"] = deadline.isoformat()

        return ctx


class DesignDocGateInterceptor:
    name = "design_doc_gate"

    def __init__(self, gatekeeper: Gatekeeper) -> None:
        self._gatekeeper = gatekeeper

    def process(self, ctx: RequestContext) -> RequestContext:
        decision: GateDecision = self._gatekeeper.check(ctx.sdd_id)
        ctx.log.append(f"gate: allowed={decision.allowed} reason={decision.reason}")
        if not decision.allowed:
            ctx.denied = True
            ctx.denial_reason = decision.reason
        return ctx


def default_interceptor_chain(
    gatekeeper: Gatekeeper,
    *,
    idempotency_store: Optional[IdempotencyStore] = None,
    quota: Optional[QuotaTimeoutInterceptor] = None,
) -> list[Interceptor]:
    """Default order per DES-0002 §5.3."""
    store = idempotency_store or InMemoryIdempotencyStore()
    return [
        LoggingInterceptor(),
        IdempotencyInterceptor(store),
        quota or QuotaTimeoutInterceptor(),
        DesignDocGateInterceptor(gatekeeper),
    ]


def run_chain(
    ctx: RequestContext,
    interceptors: list[Interceptor],
) -> RequestContext:
    for interceptor in interceptors:
        ctx = interceptor.process(ctx)
        if ctx.denied or ctx.replay_traveler_id:
            break
    return ctx
