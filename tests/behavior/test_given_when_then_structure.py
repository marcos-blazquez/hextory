"""TEST-0021 — behavior modules use readable Given/When/Then structure."""

from __future__ import annotations

from pathlib import Path

BEHAVIOR = Path(__file__).resolve().parent


def test_test_0021_behavior_modules_contain_given_when_then():
    """TEST-0021: ordinary pytest modules document Given/When/Then (not Cucumber)."""
    py_files = [p for p in BEHAVIOR.glob("test_*.py") if p.name != Path(__file__).name]
    assert py_files, "expected behavior test modules"
    missing = []
    for path in py_files:
        text = path.read_text(encoding="utf-8").lower()
        if "given" not in text or "when" not in text or "then" not in text:
            missing.append(path.name)
    assert missing == [], f"behavior modules missing Given/When/Then markers: {missing}"
