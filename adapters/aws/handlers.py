"""Lambda handlers — API Gateway HTTP API bind (DES-0005-D).

Semantic ops match on-prem:
  POST /runs
  GET  /runs/{id}
  POST /runs/{id}/resume
  GET  /health   (optional; no JWT)

Auth: JWT bearer stub (401 ≠ Gatekeeper denial). Reuses RequestGateway — no core fork.
Optional MetricsPort via ``build_handler_context(..., metrics=...)``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from adapters.aws.auth import AuthError, AuthPrincipal, require_bearer
from adapters.aws.responses import api_response, result_body, traveler_summary
from adapters.aws.wiring import build_gateway
from src.gateway.request_gateway import RequestGateway
from src.ports.metrics import MetricsPort

_RUNS_RE = re.compile(r"^/runs/?$")
_RUN_ID_RE = re.compile(r"^/runs/([^/]+)/?$")
_RESUME_RE = re.compile(r"^/runs/([^/]+)/resume/?$")
_HEALTH_RE = re.compile(r"^/health/?$")


@dataclass
class HandlerContext:
    gateway: RequestGateway
    # Retained for optional metrics injection / future /metrics on AWS.
    metrics: Optional[MetricsPort] = None
    extras: dict[str, Any] = field(default_factory=dict)


_default_ctx: Optional[HandlerContext] = None


def build_handler_context(
    *,
    gateway: Optional[RequestGateway] = None,
    use_memory: bool = False,
    dynamodb_client: Any = None,
    table_name: Optional[str] = None,
    metrics: Optional[MetricsPort] = None,
    root: Any = None,
) -> HandlerContext:
    if gateway is None:
        gateway, _ = build_gateway(
            root=root,
            use_memory=use_memory,
            dynamodb_client=dynamodb_client,
            table_name=table_name,
            metrics=metrics,
        )
    return HandlerContext(gateway=gateway, metrics=metrics)


def set_default_context(ctx: HandlerContext) -> None:
    global _default_ctx
    _default_ctx = ctx


def get_default_context() -> HandlerContext:
    global _default_ctx
    if _default_ctx is None:
        _default_ctx = build_handler_context()
    return _default_ctx


def _header(event: dict[str, Any], name: str) -> Optional[str]:
    headers = event.get("headers") or {}
    # API GW may lower-case header names.
    lower = {str(k).lower(): v for k, v in headers.items()}
    return lower.get(name.lower())


def _path(event: dict[str, Any]) -> str:
    raw = event.get("rawPath") or event.get("path") or "/"
    # Strip stage prefix if present (e.g. /Prod/runs).
    stage = (event.get("requestContext") or {}).get("stage")
    if stage and raw.startswith(f"/{stage}/"):
        raw = raw[len(stage) + 1 :]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/") or "/"


def _method(event: dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    http = rc.get("http") or {}
    return str(
        http.get("method")
        or event.get("httpMethod")
        or rc.get("httpMethod")
        or "GET"
    ).upper()


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None or body == "":
        return {}
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, dict):
        return body
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _path_param(event: dict[str, Any], name: str) -> Optional[str]:
    params = event.get("pathParameters") or {}
    return params.get(name) or params.get("id")


def _require_auth(event: dict[str, Any]) -> AuthPrincipal:
    return require_bearer(_header(event, "authorization"))


def handle_event(
    event: dict[str, Any],
    context: Any = None,
    *,
    handler_context: Optional[HandlerContext] = None,
) -> dict[str, Any]:
    """Route one API Gateway HTTP API event to run / status / resume / health."""
    del context  # Lambda context unused in first slice.
    ctx = handler_context or get_default_context()
    path = _path(event)
    method = _method(event)

    if method == "GET" and _HEALTH_RE.match(path):
        return api_response(200, {"status": "ok"})

    # Workflow routes require JWT.
    try:
        _require_auth(event)
    except AuthError as exc:
        return api_response(
            401,
            {"detail": exc.detail},
            headers={"WWW-Authenticate": "Bearer"},
        )

    gateway = ctx.gateway

    if method == "POST" and _RUNS_RE.match(path):
        body = _parse_body(event)
        result = gateway.run(
            workflow_id=str(body.get("workflow_id") or "starter_factory"),
            sdd_id=body.get("sdd_id"),
            payload=body.get("payload") if isinstance(body.get("payload"), dict) else {},
            idempotency_key=body.get("idempotency_key"),
        )
        response = result_body(result)
        if result.denied:
            return api_response(403, response)
        return api_response(200, response)

    m_resume = _RESUME_RE.match(path)
    if method == "POST" and m_resume:
        traveler_id = _path_param(event, "id") or m_resume.group(1)
        result = gateway.resume(traveler_id)
        if result is None:
            return api_response(404, {"detail": f"traveler not found: {traveler_id}"})
        response = result_body(result)
        if result.denied:
            return api_response(403, response)
        return api_response(200, response)

    m_get = _RUN_ID_RE.match(path)
    if method == "GET" and m_get:
        traveler_id = _path_param(event, "id") or m_get.group(1)
        traveler = gateway.status(traveler_id)
        if traveler is None:
            return api_response(404, {"detail": f"traveler not found: {traveler_id}"})
        denied = traveler.status.value == "denied"
        return api_response(200, traveler_summary(traveler, denied=denied))

    return api_response(404, {"detail": f"route not found: {method} {path}"})


# Lambda entrypoints (SAM / LocalStack may target these by name).
def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return handle_event(event, context)


def runs_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return handle_event(event, context)


# Explicit aliases for route-specific SAM wiring (same router underneath).
create_run = runs_handler
get_run = runs_handler
resume_run = runs_handler
health = runs_handler
