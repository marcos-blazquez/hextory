"""Q-GATE-1: LocalSddStatusReader fail-closed; manifest vs markdown agreement."""

from __future__ import annotations

import json
from pathlib import Path

from adapters.local.sdd_status_reader import LocalSddStatusReader, parse_markdown_status
from src.ports.sdd_status import SddStatus

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sdds"
REPO = Path(__file__).resolve().parents[2]


def test_parse_approved_stub():
    text = (FIXTURES / "0002-factory-engine-stub.md").read_text(encoding="utf-8")
    assert parse_markdown_status(text) == SddStatus.APPROVED


def test_parse_draft_stub():
    text = (FIXTURES / "9999-draft-stub.md").read_text(encoding="utf-8")
    assert parse_markdown_status(text) == SddStatus.DRAFT


def test_manifest_approved(tmp_path):
    manifest = tmp_path / "sdd_status.json"
    manifest.write_text(json.dumps({"DES-0002": "Approved"}), encoding="utf-8")
    reader = LocalSddStatusReader(manifest_path=manifest)
    assert reader.get_status("DES-0002") == SddStatus.APPROVED
    assert reader.is_approved("DES-0002")
    assert reader.get_status("DES-MISSING") == SddStatus.UNKNOWN


def test_disagree_fail_closed(tmp_path):
    manifest = tmp_path / "sdd_status.json"
    manifest.write_text(json.dumps({"DES-0002": "Draft"}), encoding="utf-8")
    reader = LocalSddStatusReader(
        manifest_path=manifest,
        docs_design_dir=FIXTURES,
    )
    # Fixture stub says Approved; manifest says Draft → ERROR
    assert reader.get_status("DES-0002") == SddStatus.ERROR


def test_agree_both_approved(tmp_path):
    manifest = tmp_path / "sdd_status.json"
    manifest.write_text(json.dumps({"DES-0002": "Approved"}), encoding="utf-8")
    reader = LocalSddStatusReader(
        manifest_path=manifest,
        docs_design_dir=FIXTURES,
    )
    assert reader.get_status("DES-0002") == SddStatus.APPROVED


def test_corrupt_manifest_fail_closed(tmp_path):
    manifest = tmp_path / "sdd_status.json"
    manifest.write_text("{not-json", encoding="utf-8")
    reader = LocalSddStatusReader(manifest_path=manifest)
    assert reader.get_status("DES-0002") == SddStatus.ERROR


def test_repo_manifest_and_docs_agree_for_des_0002():
    """Live repo: config + docs/design DES-0002 should both be Approved."""
    reader = LocalSddStatusReader(
        manifest_path=REPO / "config" / "sdd_status.json",
        docs_design_dir=REPO / "docs" / "design",
    )
    assert reader.get_status("DES-0002") == SddStatus.APPROVED
