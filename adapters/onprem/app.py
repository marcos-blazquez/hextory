"""FastAPI application — on-prem HTTP bind (DES-0004-E).

Routes:
  POST /runs
  GET  /runs/{id}
  POST /runs/{id}/resume
  GET  /health   (optional; no JWT)
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from adapters.onprem.auth import AuthPrincipal, require_jwt
from adapters.onprem.wiring import build_gateway
from src.domain.traveler import DigitalTraveler
from src.gateway.request_gateway import RequestGateway, RunResult


class RunRequestBody(BaseModel):
    sdd_id: Optional[str] = None
    workflow_id: str = "starter_factory"
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


def traveler_summary(traveler: DigitalTraveler, *, denied: bool = False, reason: str = "") -> dict[str, Any]:
    """JSON shape aligned with local CLI traveler fields (parity)."""
    deny_reason = reason
    if not deny_reason and traveler.status.value == "denied":
        for ev in reversed(traveler.routing_history):
            if ev.decision.value == "deny":
                deny_reason = ev.notes
                break
    return {
        "traveler_id": traveler.traveler_id,
        "status": traveler.status.value,
        "sdd_id": traveler.sdd_id,
        "workflow_id": traveler.workflow_id,
        "rework_count": traveler.rework_count,
        "max_rework": traveler.max_rework,
        "checkpoint_ref": traveler.checkpoint_ref,
        "denied": denied or traveler.status.value == "denied",
        "reason": deny_reason,
        "routing_history": [
            {
                "seq": e.seq,
                "node_id": e.node_id,
                "decision": e.decision.value,
                "notes": e.notes,
            }
            for e in traveler.routing_history
        ],
        "payload": traveler.payload,
    }


def _result_response(result: RunResult) -> dict[str, Any]:
    body = traveler_summary(result.traveler, denied=result.denied, reason=result.reason)
    return body


def get_gateway(request: Request) -> RequestGateway:
    gateway = getattr(request.app.state, "gateway", None)
    if gateway is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="gateway not configured",
        )
    return gateway


def create_app(
    *,
    gateway: Optional[RequestGateway] = None,
    use_memory: bool = False,
) -> FastAPI:
    """Application factory.

    Pass an explicit ``gateway`` for tests. Otherwise wire from env
    (Postgres when ``HEXTORY_DATABASE_URL`` is set; memory otherwise).
    """
    app = FastAPI(title="Hextory on-prem", version="0.1.0")
    if gateway is None:
        gateway, _ = build_gateway(use_memory=use_memory)
    app.state.gateway = gateway

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs")
    def create_run(
        body: RunRequestBody,
        gateway: RequestGateway = Depends(get_gateway),
        _principal: AuthPrincipal = Depends(require_jwt),
    ) -> dict[str, Any]:
        result = gateway.run(
            workflow_id=body.workflow_id,
            sdd_id=body.sdd_id,
            payload=body.payload,
            idempotency_key=body.idempotency_key,
        )
        # Gatekeeper denials are structured 403 (not 401 — that is JWT only).
        response = _result_response(result)
        if result.denied:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=response)
        return response

    @app.get("/runs/{traveler_id}")
    def get_run(
        traveler_id: str,
        gateway: RequestGateway = Depends(get_gateway),
        _principal: AuthPrincipal = Depends(require_jwt),
    ) -> dict[str, Any]:
        traveler = gateway.status(traveler_id)
        if traveler is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"traveler not found: {traveler_id}",
            )
        denied = traveler.status.value == "denied"
        return traveler_summary(traveler, denied=denied)

    @app.post("/runs/{traveler_id}/resume")
    def resume_run(
        traveler_id: str,
        gateway: RequestGateway = Depends(get_gateway),
        _principal: AuthPrincipal = Depends(require_jwt),
    ) -> dict[str, Any]:
        result = gateway.resume(traveler_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"traveler not found: {traveler_id}",
            )
        response = _result_response(result)
        if result.denied:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=response)
        return response

    return app


# Uvicorn / ``python -m adapters.onprem`` target.
# Without HEXTORY_DATABASE_URL this uses MemoryCheckpointer (tests / local smoke).
app = create_app()
