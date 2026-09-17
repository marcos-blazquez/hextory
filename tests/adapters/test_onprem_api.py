"""TEST-ONP-01…07 — on-prem FastAPI adapter (DES-0004).

BDD-style Given/When/Then in ordinary pytest (not Cucumber).
Default suite uses in-memory fakes — no Docker/Postgres required for CI.
Optional Postgres integration runs only when HEXTORY_DATABASE_URL is set.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]

pytest.importorskip("fastapi")
pytest.importorskip("jwt")

from fastapi.testclient import TestClient

from adapters.local.cli import build_gateway as build_local_gateway
from adapters.onprem.app import create_app, traveler_summary
from adapters.onprem.auth import mint_token
from adapters.onprem.postgres_checkpointer import PostgresCheckpointer, SCHEMA_SQL
from adapters.onprem.wiring import build_gateway as build_onprem_gateway
from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.ports.idempotency import InMemoryIdempotencyStore


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "test-onprem-secret-32bytes-min!!"
    monkeypatch.setenv("HEXTORY_JWT_SECRET", secret)
    monkeypatch.delenv("HEXTORY_JWT_ISSUER", raising=False)
    monkeypatch.delenv("HEXTORY_JWT_AUDIENCE", raising=False)
    return secret


@pytest.fixture
def auth_header(jwt_secret: str) -> dict[str, str]:
    token = mint_token(secret=jwt_secret)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(jwt_secret: str) -> TestClient:
    gateway, _ = build_onprem_gateway(root=REPO, use_memory=True)
    app = create_app(gateway=gateway)
    return TestClient(app)


# ---------------------------------------------------------------------------
# TEST-ONP-01 — HTTP routes
# ---------------------------------------------------------------------------


def test_onp_01_given_app_when_routes_hit_then_run_status_resume_exist(
    client: TestClient, auth_header: dict[str, str]
):
    """
    TEST-ONP-01 / AC-01
    Given an on-prem FastAPI app
    When POST /runs, GET /runs/{id}, POST /runs/{id}/resume are called with JWT
    Then each route responds (create → status → resume)
    """
    # Given / When — create
    create = client.post(
        "/runs",
        headers=auth_header,
        json={
            "sdd_id": "DES-0002",
            "workflow_id": "starter_factory",
            "payload": {"force_quality": "PASS"},
        },
    )
    # Then
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["status"] == "shipped"
    tid = body["traveler_id"]

    status_resp = client.get(f"/runs/{tid}", headers=auth_header)
    assert status_resp.status_code == 200
    assert status_resp.json()["traveler_id"] == tid
    assert status_resp.json()["status"] == "shipped"

    resume = client.post(f"/runs/{tid}/resume", headers=auth_header)
    assert resume.status_code == 200
    assert resume.json()["status"] == "shipped"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# TEST-ONP-02 — Gatekeeper denial
# ---------------------------------------------------------------------------


def test_onp_02_given_draft_sdd_when_post_runs_then_403_without_assembly(
    client: TestClient, auth_header: dict[str, str]
):
    """
    TEST-ONP-02 / AC-02
    Given a non-Approved sdd_id
    When POST /runs
    Then HTTP 403 structured denial and routing_history has no assembly entry
    """
    # When
    resp = client.post(
        "/runs",
        headers=auth_header,
        json={"sdd_id": "DES-9999", "workflow_id": "starter_factory", "payload": {}},
    )
    # Then
    assert resp.status_code == 403
    body = resp.json()
    assert body["denied"] is True
    assert body["status"] == "denied"
    nodes = [e["node_id"] for e in body["routing_history"]]
    assert "assembly" not in nodes


def test_onp_02_given_missing_sdd_when_post_runs_then_403(
    client: TestClient, auth_header: dict[str, str]
):
    """
    TEST-ONP-02
    Given missing sdd_id
    When POST /runs
    Then Gatekeeper denial (403), no assembly
    """
    resp = client.post(
        "/runs",
        headers=auth_header,
        json={"workflow_id": "starter_factory", "payload": {}},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["denied"] is True
    assert all(e["node_id"] != "assembly" for e in body["routing_history"])


# ---------------------------------------------------------------------------
# TEST-ONP-03 — Parity vs local CLI fixtures
# ---------------------------------------------------------------------------


def test_onp_03_given_pass_fixture_when_http_and_local_then_same_terminal_status(
    jwt_secret: str,
):
    """
    TEST-ONP-03 / AC-03 / AC-08
    Given equivalent PASS fixtures
    When local gateway and on-prem HTTP both run starter_factory
    Then both reach status=shipped with assembly in routing_history
    """
    # Given
    local_gw, _ = build_local_gateway(root=REPO, use_memory=True)
    onprem_gw, _ = build_onprem_gateway(root=REPO, use_memory=True)
    app = create_app(gateway=onprem_gw)
    client = TestClient(app)
    token = mint_token(secret=jwt_secret)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"force_quality": "PASS"}

    # When
    local = local_gw.run(
        workflow_id="starter_factory", sdd_id="DES-0002", payload=payload
    )
    http = client.post(
        "/runs",
        headers=headers,
        json={
            "sdd_id": "DES-0002",
            "workflow_id": "starter_factory",
            "payload": payload,
        },
    )

    # Then
    assert local.traveler.status == TravelerStatus.SHIPPED
    assert http.status_code == 200
    assert http.json()["status"] == "shipped"
    local_nodes = [e.node_id for e in local.traveler.routing_history]
    http_nodes = [e["node_id"] for e in http.json()["routing_history"]]
    assert "assembly" in local_nodes and "assembly" in http_nodes
    assert "quality" in local_nodes and "quality" in http_nodes
    assert "packaging" in local_nodes and "packaging" in http_nodes


def test_onp_03_given_fail_fixture_when_http_then_escalated_like_local(jwt_secret: str):
    """
    TEST-ONP-03 parity — force_quality FAIL → escalated on both paths
    """
    local_gw, _ = build_local_gateway(root=REPO, use_memory=True)
    onprem_gw, _ = build_onprem_gateway(root=REPO, use_memory=True)
    client = TestClient(create_app(gateway=onprem_gw))
    headers = {"Authorization": f"Bearer {mint_token(secret=jwt_secret)}"}
    payload = {"force_quality": "FAIL"}

    local = local_gw.run(
        workflow_id="starter_factory", sdd_id="DES-0002", payload=payload
    )
    http = client.post(
        "/runs",
        headers=headers,
        json={
            "sdd_id": "DES-0002",
            "workflow_id": "starter_factory",
            "payload": payload,
        },
    )
    assert local.traveler.status == TravelerStatus.ESCALATED
    assert http.status_code == 200
    assert http.json()["status"] == "escalated"


# ---------------------------------------------------------------------------
# TEST-ONP-04 — Checkpointer restart + resume (fake conn + optional DSN)
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, store: dict[str, Any]) -> None:
        self._store = store
        self._rows: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        text = " ".join(sql.split()).lower()
        params = params or ()
        if text.startswith("create table"):
            return
        if "insert into hextory_travelers" in text:
            key, snapshot = params[0], params[1]
            data = json.loads(snapshot) if isinstance(snapshot, str) else snapshot
            self._store.setdefault("travelers", {})[key] = data
            return
        if "select snapshot from hextory_travelers" in text:
            key = params[0]
            data = self._store.get("travelers", {}).get(key)
            self._rows = [(data,)] if data is not None else []
            return
        if "insert into hextory_raw_state" in text:
            key, state = params[0], params[1]
            data = json.loads(state) if isinstance(state, str) else state
            self._store.setdefault("raw", {})[key] = data
            return
        if "select state from hextory_raw_state" in text:
            key = params[0]
            data = self._store.get("raw", {}).get(key)
            self._rows = [(data,)] if data is not None else []
            return

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None


class _FakeConn:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.closed = False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.store)

    def close(self) -> None:
        self.closed = True


def test_onp_04_given_fake_postgres_when_new_instance_loads_then_resume_works():
    """
    TEST-ONP-04 / AC-04
    Given a PostgresCheckpointer backed by a shared fake connection
    When a traveler is saved and a fresh checkpointer instance loads it
    Then resume via gateway returns the same terminal traveler
    """
    # Given
    shared = _FakeConn()
    cp1 = PostgresCheckpointer(conn=shared)
    assert "hextory_travelers" in SCHEMA_SQL

    traveler = DigitalTraveler(
        traveler_id="trv_onp04",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.SHIPPED,
    )
    ref = cp1.save("trv_onp04", traveler)
    assert ref.startswith("postgres://")

    # When — "process restart": new checkpointer, same store
    cp2 = PostgresCheckpointer(conn=shared)
    loaded = cp2.load("trv_onp04")
    assert loaded is not None
    assert loaded.status == TravelerStatus.SHIPPED

    gw, _ = build_onprem_gateway(
        root=REPO,
        checkpointer=cp2,
        idempotency_store=InMemoryIdempotencyStore(),
    )
    # Seed gateway path via checkpointer only (empty in-process store)
    result = gw.resume("trv_onp04")

    # Then
    assert result is not None
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.traveler_id == "trv_onp04"


@pytest.mark.skipif(
    not os.environ.get("HEXTORY_DATABASE_URL", "").strip(),
    reason="optional Postgres integration — set HEXTORY_DATABASE_URL to run",
)
def test_onp_04_optional_live_postgres_roundtrip():
    """Optional live Postgres path (Compose / operator DSN)."""
    pytest.importorskip("psycopg")
    dsn = os.environ["HEXTORY_DATABASE_URL"]
    cp = PostgresCheckpointer(dsn)
    try:
        t = DigitalTraveler(
            traveler_id="trv_live_pg",
            workflow_id="starter_factory",
            sdd_id="DES-0002",
            status=TravelerStatus.ACCEPTED,
        )
        cp.save("trv_live_pg", t)
        loaded = cp.load("trv_live_pg")
        assert loaded is not None
        assert loaded.traveler_id == "trv_live_pg"
    finally:
        cp.close()


# ---------------------------------------------------------------------------
# TEST-ONP-05 — Compose + docs
# ---------------------------------------------------------------------------


def test_onp_05_given_repo_when_inspect_then_compose_and_operator_docs_exist():
    """
    TEST-ONP-05 / AC-05
    Given the repo tree
    When operator artifacts are inspected
    Then docker-compose.yml defines api + postgres and README documents smoke
    """
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres:" in compose
    assert "api:" in compose
    assert "postgres:16" in compose

    onprem_readme = (REPO / "adapters" / "onprem" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "docker compose" in onprem_readme.lower() or "compose" in onprem_readme.lower()
    assert "HEXTORY_JWT_SECRET" in onprem_readme
    assert "/health" in onprem_readme

    root_readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "onprem" in root_readme.lower() or "on-prem" in root_readme.lower()


# ---------------------------------------------------------------------------
# TEST-ONP-06 — JWT 401
# ---------------------------------------------------------------------------


def test_onp_06_given_no_token_when_post_runs_then_401(client: TestClient):
    """
    TEST-ONP-06 / AC-06
    Given no Authorization header
    When POST /runs
    Then 401 (not gate denial)
    """
    resp = client.post(
        "/runs",
        json={"sdd_id": "DES-0002", "workflow_id": "starter_factory", "payload": {}},
    )
    assert resp.status_code == 401


def test_onp_06_given_invalid_token_when_get_runs_then_401(client: TestClient):
    """
    TEST-ONP-06
    Given an invalid bearer token
    When GET /runs/{id}
    Then 401
    """
    resp = client.get(
        "/runs/trv_missing",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert resp.status_code == 401


def test_onp_06_health_does_not_require_jwt(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TEST-ONP-07 — no src leaks of FastAPI / Postgres / adapters
# ---------------------------------------------------------------------------


def test_onp_07_src_does_not_import_fastapi_postgres_or_adapters():
    """
    TEST-ONP-07 / AC-07 (+ TEST-0010)
    Given all Python files under src/
    When imports are scanned statically
    Then none reference fastapi, starlette, uvicorn, psycopg, adapters
    """
    banned_prefixes = (
        "fastapi",
        "starlette",
        "uvicorn",
        "psycopg",
        "psycopg2",
        "adapters",
        "jwt",
    )
    offenders: list[str] = []
    src = REPO / "src"
    for path in src.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        for mod in names:
            for banned in banned_prefixes:
                if mod == banned or mod.startswith(banned + "."):
                    offenders.append(f"{path.relative_to(REPO)} imports {mod}")
    assert offenders == [], "src leak:\n" + "\n".join(offenders)


def test_onp_traveler_summary_shape_stable():
    """Helper shape used by HTTP responses stays walkable."""
    t = DigitalTraveler(
        traveler_id="trv_shape",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.SHIPPED,
    )
    summary = traveler_summary(t)
    assert set(summary) >= {
        "traveler_id",
        "status",
        "sdd_id",
        "workflow_id",
        "routing_history",
        "denied",
    }
