"""TEST-OBS-02…07 / AC-02…07,09 — factory observability first slice (DES-0006).

BDD-style Given/When/Then in ordinary pytest — not Cucumber.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

from adapters.local.cli import build_gateway as build_local_gateway
from adapters.local.cli import main as cli_main
from adapters.local.metrics_dump import dump_metrics
from src.domain.statuses import TravelerStatus
from src.ports.metrics import (
    FROZEN_METRIC_NAMES,
    METRIC_GATE_DENIALS,
    METRIC_QUALITY_FAIL,
    METRIC_REWORK,
    METRIC_RUNS_ACCEPTED,
    METRIC_RUNS_TERMINAL,
    InMemoryMetrics,
)


# ---------------------------------------------------------------------------
# TEST-OBS-02 — gate denial increments (not auth 401)
# ---------------------------------------------------------------------------


def test_obs_02_given_draft_sdd_when_run_then_gate_denials_increments():
    """
    TEST-OBS-02 / AC-02
    Given a non-Approved sdd_id and InMemoryMetrics
    When gateway.run is called
    Then hextory_gate_denials_total increments and traveler is denied
    """
    # Given
    metrics = InMemoryMetrics()
    gateway, _ = build_local_gateway(root=REPO, use_memory=True, metrics=metrics)

    # When
    result = gateway.run(
        workflow_id="starter_factory",
        sdd_id="DES-9999",
        payload={},
    )

    # Then
    assert result.denied is True
    assert result.traveler.status == TravelerStatus.DENIED
    assert metrics.total(METRIC_GATE_DENIALS) == 1.0
    assert metrics.get(
        METRIC_GATE_DENIALS, {"workflow_id": "starter_factory"}
    ) == 1.0
    assert metrics.get(
        METRIC_RUNS_TERMINAL,
        {"workflow_id": "starter_factory", "status": "denied"},
    ) == 1.0
    assert metrics.total(METRIC_RUNS_ACCEPTED) == 0.0


def test_obs_02_given_missing_jwt_when_post_runs_then_401_not_gate_metric(jwt_env):
    """
    TEST-OBS-02 / AC-02
    Given on-prem app with Prometheus metrics
    When POST /runs without Authorization
    Then HTTP 401 and gate_denials_total stays 0
    """
    pytest.importorskip("fastapi")
    pytest.importorskip("prometheus_client")
    from fastapi.testclient import TestClient

    from adapters.onprem.app import create_app
    from adapters.onprem.prometheus_metrics import PrometheusMetrics
    from adapters.onprem.wiring import build_gateway as build_onprem_gateway

    # Given
    prom = PrometheusMetrics()
    gateway, _ = build_onprem_gateway(root=REPO, use_memory=True, metrics=prom)
    client = TestClient(create_app(gateway=gateway, metrics=prom))

    # When
    resp = client.post(
        "/runs",
        json={"sdd_id": "DES-0002", "workflow_id": "starter_factory", "payload": {}},
    )

    # Then
    assert resp.status_code == 401
    body, _ = prom.exposition()
    text = body.decode("utf-8")
    # Counter may appear with 0.0 after scrape; must not show a positive sample
    # from auth failure. Accept either absent series or explicit 0.
    assert "hextory_gate_denials_total{" not in text or (
        'hextory_gate_denials_total{workflow_id="starter_factory"}' not in text
    )


# ---------------------------------------------------------------------------
# TEST-OBS-03 — accept + shipped
# ---------------------------------------------------------------------------


def test_obs_03_given_approved_pass_when_run_then_accept_and_terminal_shipped():
    """
    TEST-OBS-03 / AC-03
    Given Approved SDD and force_quality=PASS
    When gateway.run completes
    Then runs_accepted and runs_terminal{status=shipped} increment
    """
    # Given
    metrics = InMemoryMetrics()
    gateway, _ = build_local_gateway(root=REPO, use_memory=True, metrics=metrics)

    # When
    result = gateway.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )

    # Then
    assert result.denied is False
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert metrics.total(METRIC_RUNS_ACCEPTED) == 1.0
    assert metrics.get(
        METRIC_RUNS_TERMINAL,
        {"workflow_id": "starter_factory", "status": "shipped"},
    ) == 1.0
    assert metrics.total(METRIC_GATE_DENIALS) == 0.0


# ---------------------------------------------------------------------------
# TEST-OBS-04 — quality FAIL + rework
# ---------------------------------------------------------------------------


def test_obs_04_given_fail_until_when_run_then_quality_fail_and_rework_increment():
    """
    TEST-OBS-04 / AC-04
    Given fail_until_rework=1 (one FAIL then PASS)
    When gateway.run completes
    Then quality_fail_total and rework_total increment; status shipped
    """
    # Given
    metrics = InMemoryMetrics()
    gateway, _ = build_local_gateway(root=REPO, use_memory=True, metrics=metrics)

    # When
    result = gateway.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"fail_until_rework": 1, "product": "bolt"},
    )

    # Then
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.rework_count == 1
    assert metrics.total(METRIC_QUALITY_FAIL) == 1.0
    assert metrics.total(METRIC_REWORK) == 1.0


def test_obs_04_given_always_fail_when_run_then_quality_fail_and_escalated():
    """
    TEST-OBS-04
    Given force_quality=FAIL (max_rework=3)
    When gateway.run completes
    Then quality_fail_total == 3, rework_total == 2 (third FAIL escalates),
         terminal escalated
    """
    metrics = InMemoryMetrics()
    gateway, _ = build_local_gateway(root=REPO, use_memory=True, metrics=metrics)
    result = gateway.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "FAIL"},
    )
    assert result.traveler.status == TravelerStatus.ESCALATED
    assert metrics.total(METRIC_QUALITY_FAIL) == 3.0
    # REWORK decisions fire while below max; last FAIL escalates without rework edge
    assert metrics.total(METRIC_REWORK) == 2.0
    assert metrics.get(
        METRIC_RUNS_TERMINAL,
        {"workflow_id": "starter_factory", "status": "escalated"},
    ) == 1.0


# ---------------------------------------------------------------------------
# TEST-OBS-05 — GET /metrics
# ---------------------------------------------------------------------------


def test_obs_05_given_onprem_when_scrape_metrics_then_frozen_series_present(jwt_env):
    """
    TEST-OBS-05 / AC-05
    Given on-prem app with PrometheusMetrics after a denial and a shipped run
    When GET /metrics
    Then response includes frozen metric names and updated counters
    """
    pytest.importorskip("fastapi")
    pytest.importorskip("prometheus_client")
    from fastapi.testclient import TestClient

    from adapters.onprem.app import create_app
    from adapters.onprem.auth import mint_token
    from adapters.onprem.prometheus_metrics import PrometheusMetrics
    from adapters.onprem.wiring import build_gateway as build_onprem_gateway

    # Given
    prom = PrometheusMetrics()
    gateway, _ = build_onprem_gateway(root=REPO, use_memory=True, metrics=prom)
    client = TestClient(create_app(gateway=gateway, metrics=prom))
    token = mint_token()
    headers = {"Authorization": f"Bearer {token}"}

    deny = client.post(
        "/runs",
        headers=headers,
        json={"sdd_id": "DES-9999", "workflow_id": "starter_factory", "payload": {}},
    )
    assert deny.status_code == 403

    ok = client.post(
        "/runs",
        headers=headers,
        json={
            "sdd_id": "DES-0002",
            "workflow_id": "starter_factory",
            "payload": {"force_quality": "PASS"},
        },
    )
    assert ok.status_code == 200

    # When
    scrape = client.get("/metrics")

    # Then
    assert scrape.status_code == 200
    body = scrape.text
    for name in FROZEN_METRIC_NAMES:
        assert name in body, f"missing series {name}"
    assert "hextory_gate_denials_total" in body
    assert 'status="shipped"' in body or 'status="shipped"' in body.replace("'", '"')
    # Counter values should reflect the runs
    assert "hextory_gate_denials_total{" in body
    assert "hextory_runs_accepted_total{" in body


# ---------------------------------------------------------------------------
# TEST-OBS-06 — Grafana dashboard-as-code
# ---------------------------------------------------------------------------


def test_obs_06_given_repo_when_dashboard_json_then_references_frozen_names():
    """
    TEST-OBS-06 / AC-06
    Given Grafana dashboard JSON as code
    When the file is loaded
    Then it references every frozen metric name
    """
    # Given
    path = (
        REPO
        / "adapters"
        / "onprem"
        / "observability"
        / "grafana-factory-observability.json"
    )
    assert path.is_file(), f"missing dashboard at {path}"

    # When
    data = json.loads(path.read_text(encoding="utf-8"))
    blob = json.dumps(data)

    # Then
    for name in FROZEN_METRIC_NAMES:
        assert name in blob, f"dashboard missing {name}"
    assert data.get("title")


# ---------------------------------------------------------------------------
# TEST-OBS-07 — local CLI metrics dump
# ---------------------------------------------------------------------------


def test_obs_07_given_cli_metrics_dump_when_denied_then_stdout_contains_counter(
    capsys, tmp_path
):
    """
    TEST-OBS-07 / AC-07
    Given local CLI with --metrics-dump
    When a Draft SDD run is denied
    Then stdout dump includes hextory_gate_denials_total
    """
    # When
    code = cli_main(
        [
            "run",
            "--sdd",
            "DES-9999",
            "--workflow",
            "starter_factory",
            "--memory",
            "--metrics-dump",
        ]
    )
    captured = capsys.readouterr()

    # Then
    assert code == 1
    assert METRIC_GATE_DENIALS in captured.out


def test_obs_07_given_metrics_file_when_shipped_then_file_has_accept_and_terminal(
    tmp_path,
):
    """
    TEST-OBS-07 / AC-07
    Given --metrics-file PATH
    When Approved PASS run completes
    Then file contains accepted + terminal shipped lines
    """
    out = tmp_path / "metrics.txt"
    code = cli_main(
        [
            "run",
            "--sdd",
            "DES-0002",
            "--workflow",
            "starter_factory",
            "--force-quality",
            "PASS",
            "--memory",
            "--metrics-file",
            str(out),
        ]
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert METRIC_RUNS_ACCEPTED in text
    assert METRIC_RUNS_TERMINAL in text
    assert "shipped" in text


def test_obs_07_dump_metrics_helper_writes_file(tmp_path):
    metrics = InMemoryMetrics()
    metrics.increment(METRIC_GATE_DENIALS, labels={"workflow_id": "w"})
    dest = tmp_path / "m.txt"
    dump_metrics(metrics, dest=dest)
    assert METRIC_GATE_DENIALS in dest.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "test-obs-secret-32bytes-minimum!!"
    monkeypatch.setenv("HEXTORY_JWT_SECRET", secret)
    monkeypatch.delenv("HEXTORY_JWT_ISSUER", raising=False)
    monkeypatch.delenv("HEXTORY_JWT_AUDIENCE", raising=False)
    return secret
