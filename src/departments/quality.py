"""quality_manager — evaluate acceptance; PASS/FAIL + defect report.

Pure department. Controlled via payload flags for first-slice tests:
  payload["force_quality"] = "PASS" | "FAIL"
  payload["fail_until_rework"] = N  → FAIL while rework_count < N, else PASS
  payload["llm_assist"] + injected LlmPort → optional short note (does not
    override force_quality / fail_until decisions).
"""

from __future__ import annotations

from typing import Optional

from src.domain.statuses import QualityResult, RoutingDecision, TravelerStatus
from src.domain.traveler import (
    AuditEvent,
    CriteriaResult,
    DefectReport,
    DigitalTraveler,
    QualityReport,
    utc_now,
)
from src.ports.id_generator import IdGenerator, UuidGenerator
from src.ports.llm import LlmPort
from src.policies.rework import next_status_after_fail


NODE_ID = "quality"
DEFAULT_REWORK_NODE = "assembly"


def _decide_result(traveler: DigitalTraveler) -> QualityResult:
    force = traveler.payload.get("force_quality")
    if force == "PASS":
        return QualityResult.PASS
    if force == "FAIL":
        return QualityResult.FAIL
    fail_until = traveler.payload.get("fail_until_rework")
    if fail_until is not None:
        # FAIL while rework_count < fail_until (before increment on this FAIL).
        if traveler.rework_count < int(fail_until):
            return QualityResult.FAIL
        return QualityResult.PASS
    # Default: PASS when assembled.
    if traveler.payload.get("assembled"):
        return QualityResult.PASS
    return QualityResult.FAIL


def run_quality(
    traveler: DigitalTraveler,
    *,
    id_generator: IdGenerator | None = None,
    llm: Optional[LlmPort] = None,
) -> DigitalTraveler:
    ids = id_generator or UuidGenerator()
    traveler.status = TravelerStatus.QUALITY_CHECK
    traveler.append_routing(
        node_id=NODE_ID,
        decision=RoutingDecision.ENTER,
        notes="quality entered",
    )

    if llm is not None and traveler.payload.get("llm_assist"):
        prompt = (
            f"Quality review traveler={traveler.traveler_id} "
            f"product={traveler.payload.get('product', 'widget')} "
            f"assembled={traveler.payload.get('assembled')}"
        )
        note = llm.complete(prompt)
        traveler.payload = {**traveler.payload, "quality_llm_note": note}
        traveler.audit = [
            *traveler.audit,
            AuditEvent(
                at=utc_now(),
                actor="quality",
                action="llm_assist",
                detail=(note[:200] if note else "(empty)"),
            ),
        ]

    result = _decide_result(traveler)
    report_id = ids.new_id("qr_")

    if result == QualityResult.PASS:
        report = QualityReport(
            report_id=report_id,
            at=traveler.updated_at,
            result=QualityResult.PASS,
            criteria_results=[
                CriteriaResult(ac_id="AC-default", passed=True, detail="assembled ok"),
            ],
        )
        traveler.quality_reports = [*traveler.quality_reports, report]
        traveler.last_defect = None
        traveler.append_routing(
            node_id=NODE_ID,
            decision=RoutingDecision.PASS,
            notes="quality PASS",
        )
        return traveler

    # FAIL path
    defect = DefectReport(
        code="QUALITY_FAIL",
        summary="Quality criteria not met",
        details=f"force={traveler.payload.get('force_quality')} "
        f"fail_until={traveler.payload.get('fail_until_rework')} "
        f"rework_count={traveler.rework_count}",
        suggested_rework_node=DEFAULT_REWORK_NODE,
    )
    report = QualityReport(
        report_id=report_id,
        at=traveler.updated_at,
        result=QualityResult.FAIL,
        criteria_results=[
            CriteriaResult(ac_id="AC-default", passed=False, detail="failed"),
        ],
        defect=defect,
    )
    traveler.quality_reports = [*traveler.quality_reports, report]
    traveler.last_defect = defect
    traveler.rework_count += 1
    traveler.append_routing(
        node_id=NODE_ID,
        decision=RoutingDecision.FAIL,
        notes=f"quality FAIL rework_count={traveler.rework_count}/{traveler.max_rework}",
    )

    new_status = next_status_after_fail(traveler)
    traveler.status = new_status
    if new_status == TravelerStatus.ESCALATED:
        traveler.append_routing(
            node_id=NODE_ID,
            decision=RoutingDecision.ESCALATE,
            notes=f"max_rework={traveler.max_rework} exceeded",
        )
    else:
        traveler.append_routing(
            node_id=NODE_ID,
            decision=RoutingDecision.REWORK,
            notes=f"route to {defect.suggested_rework_node or DEFAULT_REWORK_NODE}",
        )
    traveler.touch()
    return traveler
