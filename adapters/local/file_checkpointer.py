"""File-backed Checkpointer — durable travelers + quality FAIL artifacts.

Layout under ``store_dir`` (default ``.hextory`` at repo/workspace root):

    .hextory/
      travelers/{traveler_id}.json   # full DigitalTraveler snapshot
      artifacts/{traveler_id}/
        quality_fail_{report_id}.json
      raw/{key}.json                 # optional graph-state blobs

Why a local helper here (not a new ArtifactStore port): FAIL artifact files are
an adapters/local concern for this slice; core already carries ArtifactRef on the
traveler. File I/O stays out of ``src/``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from src.domain.statuses import QualityResult
from src.domain.traveler import ArtifactRef, DigitalTraveler

DEFAULT_STORE_DIRNAME = ".hextory"
_SAFE_KEY = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(key: str) -> str:
    cleaned = _SAFE_KEY.sub("_", key.strip())
    return cleaned or "unnamed"


class FileCheckpointer:
    """Persist travelers as JSON under a workspace store directory."""

    def __init__(self, store_dir: Path | str) -> None:
        self.store_dir = Path(store_dir)
        self.travelers_dir = self.store_dir / "travelers"
        self.artifacts_dir = self.store_dir / "artifacts"
        self.raw_dir = self.store_dir / "raw"
        self.travelers_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _traveler_path(self, key: str) -> Path:
        return self.travelers_dir / f"{_safe_segment(key)}.json"

    def _raw_path(self, key: str) -> Path:
        return self.raw_dir / f"{_safe_segment(key)}.json"

    def _ensure_fail_artifacts(self, traveler: DigitalTraveler) -> None:
        """Write durable FAIL (and escalated) quality artifacts; append ArtifactRefs."""
        existing_report_ids = {
            a.uri.rsplit("quality_fail_", 1)[-1].removesuffix(".json")
            for a in traveler.artifact_refs
            if a.kind in ("quality_fail", "defect") and "quality_fail_" in a.uri
        }
        # Also match by kind+digest if digest holds report_id
        for a in traveler.artifact_refs:
            if a.kind in ("quality_fail", "defect") and a.digest:
                existing_report_ids.add(a.digest)

        new_refs: list[ArtifactRef] = []
        for report in traveler.quality_reports:
            if report.result != QualityResult.FAIL:
                continue
            if report.report_id in existing_report_ids:
                continue

            art_dir = self.artifacts_dir / _safe_segment(traveler.traveler_id)
            art_dir.mkdir(parents=True, exist_ok=True)
            filename = f"quality_fail_{_safe_segment(report.report_id)}.json"
            art_path = art_dir / filename
            payload = {
                "traveler_id": traveler.traveler_id,
                "kind": "quality_fail",
                "status": traveler.status.value,
                "defect": report.defect.model_dump(mode="json") if report.defect else None,
                "quality_report": {
                    "report_id": report.report_id,
                    "at": report.at.isoformat(),
                    "result": report.result.value,
                    "criteria_results": [
                        c.model_dump(mode="json") for c in report.criteria_results
                    ],
                },
            }
            art_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            uri = art_path.resolve().as_uri()
            new_refs.append(
                ArtifactRef(kind="quality_fail", uri=uri, digest=report.report_id)
            )
            existing_report_ids.add(report.report_id)

        if new_refs:
            traveler.artifact_refs = [*traveler.artifact_refs, *new_refs]

    def save(self, key: str, traveler: DigitalTraveler) -> str:
        self._ensure_fail_artifacts(traveler)
        path = self._traveler_path(key)
        ref = path.resolve().as_uri()
        traveler.checkpoint_ref = ref
        # model_dump(mode="json") keeps datetimes/enums JSON-serializable.
        snapshot = traveler.model_dump(mode="json")
        path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return ref

    def load(self, key: str) -> Optional[DigitalTraveler]:
        path = self._traveler_path(key)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return DigitalTraveler.model_validate(data)

    def save_raw(self, key: str, state: dict[str, Any]) -> str:
        path = self._raw_path(key)
        path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path.resolve().as_uri()

    def load_raw(self, key: str) -> Optional[dict[str, Any]]:
        path = self._raw_path(key)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data) if isinstance(data, dict) else None
