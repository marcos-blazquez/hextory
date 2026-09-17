"""API Gateway HTTP API response helpers + traveler JSON (DES-0005 parity)."""

from __future__ import annotations

import json
from typing import Any, Optional

from src.domain.traveler import DigitalTraveler
from src.gateway.request_gateway import RunResult


def traveler_summary(
    traveler: DigitalTraveler, *, denied: bool = False, reason: str = ""
) -> dict[str, Any]:
    """JSON shape aligned with local CLI / on-prem traveler fields (parity)."""
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


def result_body(result: RunResult) -> dict[str, Any]:
    return traveler_summary(result.traveler, denied=result.denied, reason=result.reason)


def api_response(
    status_code: int,
    body: Any,
    *,
    headers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """API Gateway HTTP API (payload format 2.0) response shape."""
    hdrs = {"content-type": "application/json"}
    if headers:
        hdrs.update(headers)
    if isinstance(body, (dict, list)):
        payload = json.dumps(body)
    else:
        payload = str(body)
    return {
        "statusCode": status_code,
        "headers": hdrs,
        "body": payload,
    }
