"""TEST-0022 — optional checkpointer injectable at compile via port."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Optional

from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.graphs.runtime import run_workflow
from src.graphs.starter import build_starter_definition


class RecordingCheckpointer:
    def __init__(self) -> None:
        self.saved: list[str] = []
        self._data: dict[str, DigitalTraveler] = {}

    def save(self, key: str, traveler: DigitalTraveler) -> str:
        self.saved.append(key)
        self._data[key] = traveler.model_copy(deep=True)
        return f"rec://{key}"

    def load(self, key: str) -> Optional[DigitalTraveler]:
        return self._data.get(key)

    def save_raw(self, key: str, state: dict[str, Any]) -> str:
        return f"rec-raw://{key}"

    def load_raw(self, key: str) -> Optional[dict[str, Any]]:
        return None


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_test_0022_checkpointer_injectable_without_memorysaver_types():
    """TEST-0022: runtime accepts Checkpointer port; core has no adapter imports."""
    import src.graphs.runtime as runtime_mod

    path = Path(runtime_mod.__file__)
    imports = _imported_names(path)
    assert not any(m == "adapters" or m.startswith("adapters.") for m in imports)
    assert not any("langgraph" in m or "MemorySaver" in m for m in imports)

    cp = RecordingCheckpointer()
    definition = build_starter_definition()
    traveler = DigitalTraveler(
        traveler_id="trv_cp",
        workflow_id=definition.workflow_id,
        sdd_id="DES-0002",
        status=TravelerStatus.ACCEPTED,
        payload={"force_quality": "PASS", "product": "gizmo"},
    )
    out = run_workflow(definition, traveler, checkpointer=cp)
    assert out.status == TravelerStatus.SHIPPED
    assert len(cp.saved) >= 1
    assert out.checkpoint_ref and out.checkpoint_ref.startswith("rec://")
