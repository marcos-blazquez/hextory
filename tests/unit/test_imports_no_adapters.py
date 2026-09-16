"""TEST-0010 / AC-01: src/ must not import adapters/ or langgraph."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        yield path


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def test_test_0010_src_does_not_import_adapters():
    """TEST-0010: static check — nothing under src imports adapters."""
    offenders: list[str] = []
    for path in _iter_py_files(SRC):
        for mod in _imported_modules(path):
            if mod == "adapters" or mod.startswith("adapters."):
                offenders.append(f"{path.relative_to(REPO)} imports {mod}")
    assert offenders == [], "src must not import adapters:\n" + "\n".join(offenders)


def test_src_does_not_import_langgraph():
    """Hexagonal: src never imports langgraph (optional adapter only)."""
    offenders: list[str] = []
    for path in _iter_py_files(SRC):
        for mod in _imported_modules(path):
            if mod == "langgraph" or mod.startswith("langgraph."):
                offenders.append(f"{path.relative_to(REPO)} imports {mod}")
    assert offenders == [], "src must not import langgraph:\n" + "\n".join(offenders)
