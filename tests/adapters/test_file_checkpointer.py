"""FileCheckpointer — durable travelers + FAIL artifacts under .hextory/."""

from __future__ import annotations

import json
from pathlib import Path

from adapters.local.file_checkpointer import FileCheckpointer, DEFAULT_STORE_DIRNAME
from src.domain.statuses import QualityResult, TravelerStatus
from src.domain.traveler import (
    CriteriaResult,
    DefectReport,
    DigitalTraveler,
    QualityReport,
    utc_now,
)
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import GraphRegistry
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


def _traveler(**kwargs) -> DigitalTraveler:
    defaults = dict(
        traveler_id="trv_file_1",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.ACCEPTED,
        payload={"product": "widget"},
    )
    defaults.update(kwargs)
    return DigitalTraveler(**defaults)


def test_given_traveler_when_save_load_then_round_trip(tmp_path: Path):
    """
    Given a DigitalTraveler
    When FileCheckpointer saves then loads by key
    Then fields round-trip and checkpoint_ref is a file:// URI under the store
    """
    # Given
    store = tmp_path / DEFAULT_STORE_DIRNAME
    cp = FileCheckpointer(store_dir=store)
    t = _traveler(status=TravelerStatus.SHIPPED, payload={"assembled": True})

    # When
    ref = cp.save(t.traveler_id, t)
    loaded = cp.load(t.traveler_id)

    # Then
    assert loaded is not None
    assert loaded.traveler_id == t.traveler_id
    assert loaded.status == TravelerStatus.SHIPPED
    assert loaded.payload == {"assembled": True}
    assert ref.startswith("file://")
    assert loaded.checkpoint_ref == ref
    assert (store / "travelers" / f"{t.traveler_id}.json").is_file()


def test_given_missing_key_when_load_then_none(tmp_path: Path):
    cp = FileCheckpointer(store_dir=tmp_path / ".hextory")
    assert cp.load("trv_missing") is None


def test_given_quality_fail_when_save_then_artifact_file_and_ref(tmp_path: Path):
    """
    Given a traveler with a FAIL quality report + defect
    When FileCheckpointer saves
    Then a quality_fail JSON artifact is written and artifact_refs gains an entry
    """
    # Given
    store = tmp_path / ".hextory"
    cp = FileCheckpointer(store_dir=store)
    defect = DefectReport(
        code="QUALITY_FAIL",
        summary="Quality criteria not met",
        details="forced fail",
        suggested_rework_node="assembly",
    )
    report = QualityReport(
        report_id="qr_abc",
        at=utc_now(),
        result=QualityResult.FAIL,
        criteria_results=[CriteriaResult(ac_id="AC-default", passed=False, detail="failed")],
        defect=defect,
    )
    t = _traveler(
        traveler_id="trv_fail_1",
        status=TravelerStatus.REWORK,
        quality_reports=[report],
        last_defect=defect,
        rework_count=1,
    )

    # When
    cp.save(t.traveler_id, t)

    # Then
    fail_refs = [a for a in t.artifact_refs if a.kind == "quality_fail"]
    assert len(fail_refs) == 1
    assert fail_refs[0].uri.startswith("file://")

    art_path = store / "artifacts" / t.traveler_id / "quality_fail_qr_abc.json"
    assert art_path.is_file()
    data = json.loads(art_path.read_text(encoding="utf-8"))
    assert data["traveler_id"] == "trv_fail_1"
    assert data["defect"]["code"] == "QUALITY_FAIL"
    assert data["quality_report"]["report_id"] == "qr_abc"
    assert data["quality_report"]["result"] == "FAIL"


def test_given_fail_already_artifacted_when_resave_then_no_duplicate(tmp_path: Path):
    store = tmp_path / ".hextory"
    cp = FileCheckpointer(store_dir=store)
    defect = DefectReport(code="QUALITY_FAIL", summary="x")
    report = QualityReport(
        report_id="qr_once",
        at=utc_now(),
        result=QualityResult.FAIL,
        defect=defect,
    )
    t = _traveler(traveler_id="trv_dup", quality_reports=[report], last_defect=defect)
    cp.save(t.traveler_id, t)
    n1 = len([a for a in t.artifact_refs if a.kind == "quality_fail"])
    cp.save(t.traveler_id, t)
    n2 = len([a for a in t.artifact_refs if a.kind == "quality_fail"])
    assert n1 == 1
    assert n2 == 1


def test_given_escalated_run_when_gateway_uses_file_cp_then_fail_artifacts_on_disk(
    tmp_path: Path,
):
    """
    Given FileCheckpointer wired into RequestGateway and force_quality=FAIL
    When the starter workflow runs to escalated
    Then traveler JSON + at least one quality_fail artifact exist on disk
    """
    # Given
    store = tmp_path / ".hextory"
    cp = FileCheckpointer(store_dir=store)
    registry = GraphRegistry()
    register_starter(registry, sdd_id="DES-0002")
    gw = RequestGateway(
        gatekeeper=PolicyGatekeeper(FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})),
        registry=registry,
        checkpointer=cp,
    )

    # When
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "FAIL", "product": "nail"},
    )

    # Then
    t = result.traveler
    assert t.status == TravelerStatus.ESCALATED
    assert (store / "travelers" / f"{t.traveler_id}.json").is_file()
    art_dir = store / "artifacts" / t.traveler_id
    assert art_dir.is_dir()
    fail_files = list(art_dir.glob("quality_fail_*.json"))
    assert len(fail_files) >= 1
    assert any(a.kind == "quality_fail" for a in t.artifact_refs)
    # Cross-process style: fresh checkpointer instance
    cp2 = FileCheckpointer(store_dir=store)
    loaded = cp2.load(t.traveler_id)
    assert loaded is not None
    assert loaded.status == TravelerStatus.ESCALATED


def test_save_raw_round_trip(tmp_path: Path):
    cp = FileCheckpointer(store_dir=tmp_path / ".hextory")
    ref = cp.save_raw("raw_key", {"step": 1, "ok": True})
    assert ref.startswith("file://")
    assert cp.load_raw("raw_key") == {"step": 1, "ok": True}
