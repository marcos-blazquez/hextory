"""RequestGateway — accept run/resume; interceptor chain; create traveler; invoke graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.domain.statuses import RoutingDecision, TravelerStatus
from src.domain.traveler import DEFAULT_MAX_REWORK, DigitalTraveler
from src.graphs.registry import GraphRegistry
from src.graphs.runtime import PureGraphRunner
from src.policies.interceptors import (
    IdempotencyInterceptor,
    Interceptor,
    RequestContext,
    default_interceptor_chain,
    run_chain,
)
from src.ports.checkpointer import Checkpointer
from src.ports.clock import Clock, SystemClock
from src.ports.gatekeeper import Gatekeeper
from src.ports.graph_runner import GraphRunner
from src.ports.id_generator import IdGenerator, UuidGenerator
from src.ports.idempotency import IdempotencyStore, InMemoryIdempotencyStore


@dataclass
class RunResult:
    traveler: DigitalTraveler
    denied: bool
    reason: str = ""


class RequestGateway:
    def __init__(
        self,
        *,
        gatekeeper: Gatekeeper,
        registry: GraphRegistry,
        id_generator: Optional[IdGenerator] = None,
        clock: Optional[Clock] = None,
        checkpointer: Optional[Checkpointer] = None,
        interceptors: Optional[list[Interceptor]] = None,
        traveler_store: Optional[dict[str, DigitalTraveler]] = None,
        runner: Optional[GraphRunner] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
    ) -> None:
        self._gatekeeper = gatekeeper
        self._registry = registry
        self._ids = id_generator or UuidGenerator()
        self._clock = clock or SystemClock()
        self._checkpointer = checkpointer
        self._idempotency: IdempotencyStore = (
            idempotency_store or InMemoryIdempotencyStore()
        )
        if interceptors is not None:
            self._interceptors = interceptors
        else:
            self._interceptors = default_interceptor_chain(
                gatekeeper,
                idempotency_store=self._idempotency,
            )
        # Keep gateway store and interceptor store aligned when chain is custom.
        for it in self._interceptors:
            if isinstance(it, IdempotencyInterceptor):
                self._idempotency = it.store
                break
        # In-process store for status lookups (local slice / tests).
        self._store: dict[str, DigitalTraveler] = (
            traveler_store if traveler_store is not None else {}
        )
        # Default remains pure registry walker for stability (DES-0002-B optional LangGraph).
        self._runner: GraphRunner = runner if runner is not None else PureGraphRunner()

    def _remember_idempotency(self, key: Optional[str], traveler_id: str) -> None:
        if key:
            self._idempotency.put(key, traveler_id)

    def _persist(self, traveler: DigitalTraveler) -> None:
        self._store[traveler.traveler_id] = traveler
        if self._checkpointer is not None:
            traveler.checkpoint_ref = self._checkpointer.save(
                traveler.traveler_id, traveler
            )

    def _load_traveler(self, traveler_id: str) -> Optional[DigitalTraveler]:
        if traveler_id in self._store:
            return self._store[traveler_id]
        if self._checkpointer is not None:
            return self._checkpointer.load(traveler_id)
        return None

    def _deny_reason_from(self, traveler: DigitalTraveler) -> str:
        for ev in reversed(traveler.routing_history):
            if ev.decision == RoutingDecision.DENY:
                return ev.notes
        return ""

    def run(
        self,
        *,
        workflow_id: str,
        sdd_id: Optional[str],
        payload: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        max_rework: Optional[int] = None,
    ) -> RunResult:
        ctx = RequestContext(
            workflow_id=workflow_id,
            sdd_id=sdd_id,
            payload=payload or {},
            idempotency_key=idempotency_key,
            max_rework=max_rework,
        )
        ctx = run_chain(ctx, self._interceptors)

        # Idempotent replay: return the same traveler / prior result (incl. denial).
        if ctx.replay_traveler_id:
            prior = self._load_traveler(ctx.replay_traveler_id)
            if prior is not None:
                denied = prior.status == TravelerStatus.DENIED
                reason = self._deny_reason_from(prior) if denied else ""
                return RunResult(traveler=prior, denied=denied, reason=reason)
            # Orphaned key (store hit, traveler missing): reclaim key and continue.
            if idempotency_key:
                self._idempotency.delete(idempotency_key)
            ctx.replay_traveler_id = None
            ctx.metadata.pop("idempotent_replay", None)

        now = self._clock.now()
        traveler_id = self._ids.new_id("trv_")

        if ctx.denied:
            traveler = DigitalTraveler(
                traveler_id=traveler_id,
                workflow_id=workflow_id,
                sdd_id=sdd_id or "",
                status=TravelerStatus.DENIED,
                payload=ctx.payload,
                idempotency_key=idempotency_key,
                max_rework=max_rework or DEFAULT_MAX_REWORK,
                created_at=now,
                updated_at=now,
            )
            traveler.append_routing(
                node_id="gateway",
                decision=RoutingDecision.DENY,
                notes=ctx.denial_reason,
                at=now,
            )
            self._persist(traveler)
            self._remember_idempotency(idempotency_key, traveler.traveler_id)
            return RunResult(traveler=traveler, denied=True, reason=ctx.denial_reason)

        if not self._registry.has(workflow_id):
            traveler = DigitalTraveler(
                traveler_id=traveler_id,
                workflow_id=workflow_id,
                sdd_id=sdd_id or "",
                status=TravelerStatus.DENIED,
                payload=ctx.payload,
                idempotency_key=idempotency_key,
                max_rework=max_rework or DEFAULT_MAX_REWORK,
                created_at=now,
                updated_at=now,
            )
            reason = f"unknown workflow_id={workflow_id}"
            traveler.append_routing(
                node_id="gateway",
                decision=RoutingDecision.DENY,
                notes=reason,
                at=now,
            )
            self._persist(traveler)
            self._remember_idempotency(idempotency_key, traveler.traveler_id)
            return RunResult(traveler=traveler, denied=True, reason=reason)

        definition = self._registry.get(workflow_id)
        assert definition is not None

        traveler = DigitalTraveler(
            traveler_id=traveler_id,
            workflow_id=workflow_id,
            sdd_id=sdd_id or "",
            status=TravelerStatus.ACCEPTED,
            payload=ctx.payload,
            idempotency_key=idempotency_key,
            max_rework=max_rework or DEFAULT_MAX_REWORK,
            created_at=now,
            updated_at=now,
        )
        # Carry interceptor timeout deadline into traveler metadata via payload note.
        if "deadline" in ctx.metadata:
            traveler.payload = {
                **traveler.payload,
                "_deadline": ctx.metadata["deadline"],
                "_timeout_seconds": ctx.metadata.get("timeout_seconds"),
            }
        traveler.append_routing(
            node_id="gateway",
            decision=RoutingDecision.ACCEPT,
            notes="run accepted",
            at=now,
        )

        traveler = self._runner.run(
            definition,
            traveler,
            checkpointer=self._checkpointer,
        )
        self._persist(traveler)
        self._remember_idempotency(idempotency_key, traveler.traveler_id)
        return RunResult(traveler=traveler, denied=False)

    def status(self, traveler_id: str) -> Optional[DigitalTraveler]:
        return self._load_traveler(traveler_id)

    def resume(self, traveler_id: str) -> Optional[RunResult]:
        """Resume a prior run from checkpointer / in-process store.

        First-slice semantics (DES-0002 / DES-0004):
        - Missing traveler → None (adapter maps to HTTP 404).
        - Terminal travelers (shipped / escalated / denied) → return as-is
          (idempotent resume after process restart).
        - Non-terminal → re-invoke GraphRunner with the loaded traveler and
          persist the result.
        """
        traveler = self._load_traveler(traveler_id)
        if traveler is None:
            return None

        terminal = {
            TravelerStatus.SHIPPED,
            TravelerStatus.ESCALATED,
            TravelerStatus.DENIED,
        }
        if traveler.status in terminal:
            denied = traveler.status == TravelerStatus.DENIED
            reason = self._deny_reason_from(traveler) if denied else ""
            return RunResult(traveler=traveler, denied=denied, reason=reason)

        if not self._registry.has(traveler.workflow_id):
            reason = f"unknown workflow_id={traveler.workflow_id}"
            now = self._clock.now()
            traveler.append_routing(
                node_id="gateway",
                decision=RoutingDecision.DENY,
                notes=reason,
                at=now,
            )
            traveler.status = TravelerStatus.DENIED
            traveler.updated_at = now
            self._persist(traveler)
            return RunResult(traveler=traveler, denied=True, reason=reason)

        definition = self._registry.get(traveler.workflow_id)
        assert definition is not None
        traveler = self._runner.run(
            definition,
            traveler,
            checkpointer=self._checkpointer,
        )
        self._persist(traveler)
        denied = traveler.status == TravelerStatus.DENIED
        reason = self._deny_reason_from(traveler) if denied else ""
        return RunResult(traveler=traveler, denied=denied, reason=reason)
