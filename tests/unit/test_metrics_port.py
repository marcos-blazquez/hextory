"""TEST-OBS-01 / AC-01 — MetricsPort + src purity (no prometheus/otel in src)."""

from __future__ import annotations

import ast
from pathlib import Path

from src.ports.metrics import (
    FROZEN_METRIC_NAMES,
    FORBIDDEN_LABEL_KEYS,
    InMemoryMetrics,
    METRIC_GATE_DENIALS,
    NoOpMetrics,
    SafeMetrics,
    sanitize_labels,
)

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"

FORBIDDEN_SRC_IMPORTS = (
    "prometheus_client",
    "prometheus",
    "opentelemetry",
    "otel",
    "grafana_client",
)


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


def test_obs_01_metrics_port_exists_and_noop_safe():
    """
    TEST-OBS-01 / AC-01
    Given MetricsPort implementations in src/ports
    When increment/observe are called on NoOp and Safe+raising inner
    Then NoOp swallows; SafeMetrics never raises into the caller
    """
    # Given / When
    NoOpMetrics().increment(METRIC_GATE_DENIALS, labels={"workflow_id": "w"})
    NoOpMetrics().observe("hextory_run_duration_seconds", 1.5)

    class Boom:
        def increment(self, *a, **k):
            raise RuntimeError("sink down")

        def observe(self, *a, **k):
            raise RuntimeError("sink down")

    safe = SafeMetrics(Boom())  # type: ignore[arg-type]
    # Then — must not raise
    safe.increment(METRIC_GATE_DENIALS)
    safe.observe("x", 1.0)


def test_obs_01_src_has_no_prometheus_or_otel_imports():
    """
    TEST-OBS-01 / AC-01 (+ TEST-0010 family)
    Given all Python modules under src/
    When imports are scanned
    Then none import prometheus_client / OpenTelemetry / Grafana libs
    """
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        for mod in _imported_modules(path):
            root = mod.split(".", 1)[0]
            if root in FORBIDDEN_SRC_IMPORTS or mod in FORBIDDEN_SRC_IMPORTS:
                offenders.append(f"{path.relative_to(REPO)} imports {mod}")
    assert offenders == [], "src purity violated:\n" + "\n".join(offenders)


def test_obs_01_frozen_metric_names_stable():
    assert METRIC_GATE_DENIALS in FROZEN_METRIC_NAMES
    assert "hextory_runs_terminal_total" in FROZEN_METRIC_NAMES


def test_obs_08_sanitize_labels_forbids_traveler_and_pii():
    """
    TEST-OBS-08 / AC-08
    Given labels including traveler_id and email
    When sanitize_labels runs
    Then only workflow_id/status survive
    """
    # Given
    raw = {
        "workflow_id": "starter_factory",
        "status": "shipped",
        "traveler_id": "trv_secret",
        "email": "a@b.c",
        "sdd_id": "DES-0002",  # not in allow-list for first slice
    }
    # When
    clean = sanitize_labels(raw)
    # Then
    assert clean == {"workflow_id": "starter_factory", "status": "shipped"}
    assert "traveler_id" in FORBIDDEN_LABEL_KEYS

    mem = InMemoryMetrics()
    mem.increment(
        METRIC_GATE_DENIALS,
        labels={"workflow_id": "w", "traveler_id": "trv_x"},
    )
    assert mem.get(METRIC_GATE_DENIALS, {"workflow_id": "w"}) == 1.0
    # Forbidden key must not create a separate series
    assert mem.events[0][2] == {"workflow_id": "w"}
