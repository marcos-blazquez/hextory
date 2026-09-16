"""assembly_manager — produce/transform artifacts per Approved SDD.

Pure department: takes traveler (+ optional ports), returns updated traveler.
No I/O; adapters inject concrete ``LlmPort`` implementations.
"""

from __future__ import annotations

from typing import Optional

from src.domain.statuses import RoutingDecision, TravelerStatus
from src.domain.traveler import ArtifactRef, AuditEvent, DigitalTraveler, utc_now
from src.ports.llm import LlmPort


NODE_ID = "assembly"


def run_assembly(
    traveler: DigitalTraveler,
    *,
    llm: Optional[LlmPort] = None,
) -> DigitalTraveler:
    """Assemble payload into a simple artifact ref and mark assembling→ready for quality.

    When ``llm`` is injected and ``payload["llm_assist"]`` is truthy, call the LLM
    port and record a short note on the traveler (payload + audit). Existing
    ``force_quality`` paths remain unchanged when assist is not requested.
    """
    traveler.status = TravelerStatus.ASSEMBLING
    traveler.append_routing(
        node_id=NODE_ID,
        decision=RoutingDecision.ENTER,
        notes="assembly entered",
    )

    # Synthetic assembly: stamp an artifact from payload.
    product = traveler.payload.get("product", "widget")
    attempt = traveler.rework_count
    uri = f"memory://artifacts/{traveler.traveler_id}/assembly-{attempt}"
    traveler.artifact_refs = [
        *traveler.artifact_refs,
        ArtifactRef(kind="assembly_output", uri=uri, digest=f"asm-{product}-{attempt}"),
    ]
    new_payload = {
        **traveler.payload,
        "assembled": True,
        "assembly_attempt": attempt,
    }

    if llm is not None and traveler.payload.get("llm_assist"):
        prompt = (
            f"Assemble product={product} for traveler={traveler.traveler_id} "
            f"sdd={traveler.sdd_id} attempt={attempt}"
        )
        note = llm.complete(prompt)
        new_payload["llm_note"] = note
        traveler.audit = [
            *traveler.audit,
            AuditEvent(
                at=utc_now(),
                actor="assembly",
                action="llm_assist",
                detail=(note[:200] if note else "(empty)"),
            ),
        ]
        traveler.append_routing(
            node_id=NODE_ID,
            decision=RoutingDecision.PASS,
            notes=f"assembly complete (llm_assist: {note[:80] if note else 'empty'})",
        )
    else:
        traveler.append_routing(
            node_id=NODE_ID,
            decision=RoutingDecision.PASS,
            notes="assembly complete",
        )

    traveler.payload = new_payload
    traveler.touch()
    return traveler
