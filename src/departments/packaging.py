"""packaging_manager — emit shippable bundle + manifest; never on FAIL."""

from __future__ import annotations

from src.domain.statuses import QualityResult, RoutingDecision, TravelerStatus
from src.domain.traveler import ArtifactRef, DigitalTraveler


NODE_ID = "packaging"


class PackagingInvariantError(RuntimeError):
    """Raised if packaging is invoked while last quality was FAIL (TEST-0017)."""


def _last_quality_failed(traveler: DigitalTraveler) -> bool:
    if not traveler.quality_reports:
        return False
    return traveler.quality_reports[-1].result == QualityResult.FAIL


def run_packaging(traveler: DigitalTraveler) -> DigitalTraveler:
    if _last_quality_failed(traveler) or traveler.status == TravelerStatus.ESCALATED:
        raise PackagingInvariantError(
            "packaging must not run after Quality FAIL or while escalated"
        )

    traveler.status = TravelerStatus.PACKAGING
    traveler.append_routing(
        node_id=NODE_ID,
        decision=RoutingDecision.ENTER,
        notes="packaging entered",
    )

    manifest_uri = f"memory://manifests/{traveler.traveler_id}.json"
    traveler.artifact_refs = [
        *traveler.artifact_refs,
        ArtifactRef(kind="ship_manifest", uri=manifest_uri),
    ]
    traveler.payload = {**traveler.payload, "packaged": True, "manifest_uri": manifest_uri}
    traveler.status = TravelerStatus.SHIPPED
    traveler.append_routing(
        node_id=NODE_ID,
        decision=RoutingDecision.SHIP,
        notes="shipped",
    )
    traveler.touch()
    return traveler
