"""TEST-0019 — Local CLI + checkpointer smoke (memory + file)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.local.cli import build_gateway, main
from adapters.local.file_checkpointer import FileCheckpointer
from adapters.local.memory_checkpointer import MemoryCheckpointer
from src.domain.statuses import TravelerStatus


REPO = Path(__file__).resolve().parents[2]


def test_test_0019_cli_run_approved_synthetic(capsys, monkeypatch, tmp_path):
    """TEST-0019: CLI can start an Approved synthetic run and print status/routing."""
    monkeypatch.chdir(REPO)
    store = tmp_path / ".hextory"
    code = main(
        [
            "run",
            "--sdd",
            "DES-0002",
            "--workflow",
            "starter_factory",
            "--force-quality",
            "PASS",
            "--store-dir",
            str(store),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "status=shipped" in out
    assert "routing_history" in out
    assert "assembly" in out
    assert "checkpoint_ref=file://" in out


def test_test_0019_cli_denies_draft(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(REPO)
    store = tmp_path / ".hextory"
    code = main(
        ["run", "--sdd", "DES-9999", "--workflow", "starter_factory", "--store-dir", str(store)]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "denied=True" in out or "status=denied" in out


def test_test_0019_cli_denies_missing_sdd(monkeypatch):
    monkeypatch.chdir(REPO)
    with pytest.raises(SystemExit):
        # --sdd required by argparse
        main(["run", "--workflow", "starter_factory"])


def test_memory_checkpointer_roundtrip():
    from src.domain.traveler import DigitalTraveler

    cp = MemoryCheckpointer()
    t = DigitalTraveler(
        traveler_id="trv_mem",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.ACCEPTED,
    )
    ref = cp.save("trv_mem", t)
    assert ref.startswith("mem://")
    loaded = cp.load("trv_mem")
    assert loaded is not None
    assert loaded.traveler_id == "trv_mem"


def test_build_gateway_defaults_to_file_checkpointer(tmp_path):
    store = tmp_path / ".hextory"
    gw, cp = build_gateway(root=REPO, store_dir=store)
    assert isinstance(cp, FileCheckpointer)
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert gw.status(result.traveler.traveler_id) is not None
    assert (store / "travelers" / f"{result.traveler.traveler_id}.json").is_file()


def test_build_gateway_use_memory_flag():
    gw, cp = build_gateway(root=REPO, use_memory=True)
    assert isinstance(cp, MemoryCheckpointer)
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert gw.status(result.traveler.traveler_id) is not None


def test_given_prior_run_when_status_cli_then_loads_from_disk(capsys, monkeypatch, tmp_path):
    """
    Given a FAIL run that persisted under --store-dir
    When status --traveler is invoked (new process / fresh gateway)
    Then status is printed without --from-json
    """
    monkeypatch.chdir(REPO)
    store = tmp_path / "store"
    code = main(
        [
            "run",
            "--sdd",
            "DES-0002",
            "--force-quality",
            "FAIL",
            "--store-dir",
            str(store),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "status=escalated" in out
    traveler_id = None
    for line in out.splitlines():
        if line.startswith("traveler_id="):
            traveler_id = line.split("=", 1)[1].strip()
            break
    assert traveler_id

    # When — fresh CLI invocation (no in-process store)
    code2 = main(["status", "--traveler", traveler_id, "--store-dir", str(store)])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert traveler_id in out2
    assert "status=escalated" in out2
    assert "quality_fail_artifacts=" in out2

    # And FAIL artifact files exist
    art_dir = store / "artifacts" / traveler_id
    assert art_dir.is_dir()
    assert list(art_dir.glob("quality_fail_*.json"))


def test_status_from_json_still_works(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(REPO)
    from src.domain.traveler import DigitalTraveler

    t = DigitalTraveler(
        traveler_id="trv_snap",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.SHIPPED,
    )
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(t.model_dump(mode="json")), encoding="utf-8")
    code = main(["status", "--traveler", "ignored", "--from-json", str(snap)])
    out = capsys.readouterr().out
    assert code == 0
    assert "trv_snap" in out
    assert "status=shipped" in out


def test_cli_runtime_pure_default_ships(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(REPO)
    store = tmp_path / ".hextory"
    code = main(
        [
            "run",
            "--sdd",
            "DES-0002",
            "--force-quality",
            "PASS",
            "--runtime",
            "pure",
            "--store-dir",
            str(store),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "status=shipped" in out


def test_cli_runtime_langgraph_ships(capsys, monkeypatch, tmp_path):
    pytest.importorskip("langgraph")
    monkeypatch.chdir(REPO)
    store = tmp_path / ".hextory-lg"
    code = main(
        [
            "run",
            "--sdd",
            "DES-0002",
            "--force-quality",
            "PASS",
            "--runtime",
            "langgraph",
            "--store-dir",
            str(store),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "status=shipped" in out


def test_build_gateway_runtime_langgraph():
    pytest.importorskip("langgraph")
    from adapters.local.langgraph_runtime import LangGraphRunner

    gw, _ = build_gateway(root=REPO, use_memory=True, runtime="langgraph")
    assert isinstance(gw._runner, LangGraphRunner)
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert result.traveler.status == TravelerStatus.SHIPPED
