"""TEST-0020 / TEST-0023 — layout + merge policy cites design-doc readiness."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_test_0020_tests_layout_and_no_cucumber():
    """TEST-0020: tests/{unit,behavior,adapters} exist; no Cucumber dependency."""
    assert (REPO / "tests" / "unit").is_dir()
    assert (REPO / "tests" / "behavior").is_dir()
    assert (REPO / "tests" / "adapters").is_dir()

    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "cucumber" not in pyproject
    assert "behave" not in pyproject  # also not adopting Gherkin runners

    # No cucumber-ish files
    for pattern in ("*.feature", "*cucumber*"):
        assert list(REPO.rglob(pattern)) == []


def test_test_0023_merge_policy_cites_design_doc_readiness():
    """TEST-0023: docs/comments cite design-doc readiness, not code walkthrough."""
    readme = (REPO / "README.md").read_text(encoding="utf-8").lower()
    sdd = (REPO / "docs" / "design" / "0002-factory-engine.md").read_text(encoding="utf-8").lower()
    blob = readme + "\n" + sdd
    assert "design-doc" in blob or "design doc" in blob
    assert "approved" in blob
    # Must not require line-by-line code review as merge prerequisite
    assert "not required" in readme or "not a code walkthrough" in readme or "design-doc readiness" in readme
