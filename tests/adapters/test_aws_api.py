"""TEST-AWS-01…08 — AWS Lambda / DynamoDB adapter (DES-0005).

BDD-style Given/When/Then in ordinary pytest (not Cucumber).
Default suite uses moto — no real AWS account and no LocalStack required for CI.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]

pytest.importorskip("boto3")
pytest.importorskip("moto")
pytest.importorskip("jwt")

import boto3
from moto import mock_aws

from adapters.aws.auth import mint_token
from adapters.aws.dynamodb_checkpointer import DynamoDbCheckpointer
from adapters.aws.handlers import build_handler_context, handle_event
from adapters.aws.responses import traveler_summary
from adapters.aws.wiring import build_gateway as build_aws_gateway
from adapters.local.cli import build_gateway as build_local_gateway
from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.ports.idempotency import InMemoryIdempotencyStore
from src.ports.metrics import InMemoryMetrics


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "test-aws-secret-32bytes-minimum!!"
    monkeypatch.setenv("HEXTORY_JWT_SECRET", secret)
    monkeypatch.delenv("HEXTORY_JWT_ISSUER", raising=False)
    monkeypatch.delenv("HEXTORY_JWT_AUDIENCE", raising=False)
    return secret


@pytest.fixture
def dynamodb_client():
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        yield client


@pytest.fixture
def handler_ctx(jwt_secret: str, dynamodb_client: Any):
    metrics = InMemoryMetrics()
    return build_handler_context(
        root=REPO,
        dynamodb_client=dynamodb_client,
        table_name="hextory-test",
        metrics=metrics,
    )


def _auth_header(secret: str) -> dict[str, str]:
    return {"authorization": f"Bearer {mint_token(secret=secret)}"}


def _event(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    path_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "version": "2.0",
        "rawPath": path,
        "headers": headers or {},
        "requestContext": {"http": {"method": method}},
        "pathParameters": path_params or {},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def _json(resp: dict[str, Any]) -> dict[str, Any]:
    return json.loads(resp["body"])


# ---------------------------------------------------------------------------
# TEST-AWS-01 — Lambda route semantics
# ---------------------------------------------------------------------------


def test_aws_01_given_handlers_when_routes_hit_then_run_status_resume_exist(
    handler_ctx, jwt_secret: str
):
    """
    TEST-AWS-01 / AC-01
    Given AWS Lambda handlers wired to RequestGateway
    When POST /runs, GET /runs/{id}, POST /runs/{id}/resume are invoked with JWT
    Then each route responds (create → status → resume)
    """
    headers = _auth_header(jwt_secret)
    create = handle_event(
        _event(
            "POST",
            "/runs",
            headers=headers,
            body={
                "sdd_id": "DES-0002",
                "workflow_id": "starter_factory",
                "payload": {"force_quality": "PASS"},
            },
        ),
        handler_context=handler_ctx,
    )
    assert create["statusCode"] == 200, create["body"]
    body = _json(create)
    assert body["status"] == "shipped"
    tid = body["traveler_id"]

    status_resp = handle_event(
        _event("GET", f"/runs/{tid}", headers=headers, path_params={"id": tid}),
        handler_context=handler_ctx,
    )
    assert status_resp["statusCode"] == 200
    assert _json(status_resp)["traveler_id"] == tid
    assert _json(status_resp)["status"] == "shipped"

    resume = handle_event(
        _event(
            "POST",
            f"/runs/{tid}/resume",
            headers=headers,
            path_params={"id": tid},
        ),
        handler_context=handler_ctx,
    )
    assert resume["statusCode"] == 200
    assert _json(resume)["status"] == "shipped"

    health = handle_event(_event("GET", "/health"), handler_context=handler_ctx)
    assert health["statusCode"] == 200
    assert _json(health)["status"] == "ok"


# ---------------------------------------------------------------------------
# TEST-AWS-02 — Gatekeeper denial
# ---------------------------------------------------------------------------


def test_aws_02_given_draft_sdd_when_post_runs_then_403_without_assembly(
    handler_ctx, jwt_secret: str
):
    """
    TEST-AWS-02 / AC-02
    Given a non-Approved sdd_id
    When POST /runs
    Then HTTP 403 structured denial and routing_history has no assembly entry
    """
    resp = handle_event(
        _event(
            "POST",
            "/runs",
            headers=_auth_header(jwt_secret),
            body={"sdd_id": "DES-9999", "workflow_id": "starter_factory", "payload": {}},
        ),
        handler_context=handler_ctx,
    )
    assert resp["statusCode"] == 403
    body = _json(resp)
    assert body["denied"] is True
    assert body["status"] == "denied"
    nodes = [e["node_id"] for e in body["routing_history"]]
    assert "assembly" not in nodes


def test_aws_02_given_missing_sdd_when_post_runs_then_403(
    handler_ctx, jwt_secret: str
):
    """
    TEST-AWS-02
    Given missing sdd_id
    When POST /runs
    Then Gatekeeper denial (403), no assembly
    """
    resp = handle_event(
        _event(
            "POST",
            "/runs",
            headers=_auth_header(jwt_secret),
            body={"workflow_id": "starter_factory", "payload": {}},
        ),
        handler_context=handler_ctx,
    )
    assert resp["statusCode"] == 403
    body = _json(resp)
    assert body["denied"] is True
    assert all(e["node_id"] != "assembly" for e in body["routing_history"])


# ---------------------------------------------------------------------------
# TEST-AWS-03 — Parity vs local CLI fixtures
# ---------------------------------------------------------------------------


def test_aws_03_given_pass_fixture_when_aws_and_local_then_same_terminal_status(
    jwt_secret: str, dynamodb_client: Any
):
    """
    TEST-AWS-03 / AC-03 / AC-08
    Given equivalent PASS fixtures
    When local gateway and AWS handler both run starter_factory
    Then both reach status=shipped with assembly in routing_history
    """
    local_gw, _ = build_local_gateway(root=REPO, use_memory=True)
    ctx = build_handler_context(
        root=REPO, dynamodb_client=dynamodb_client, table_name="hextory-parity"
    )
    payload = {"force_quality": "PASS"}

    local = local_gw.run(
        workflow_id="starter_factory", sdd_id="DES-0002", payload=payload
    )
    http = handle_event(
        _event(
            "POST",
            "/runs",
            headers=_auth_header(jwt_secret),
            body={
                "sdd_id": "DES-0002",
                "workflow_id": "starter_factory",
                "payload": payload,
            },
        ),
        handler_context=ctx,
    )

    assert local.traveler.status == TravelerStatus.SHIPPED
    assert http["statusCode"] == 200
    assert _json(http)["status"] == "shipped"
    local_nodes = [e.node_id for e in local.traveler.routing_history]
    http_nodes = [e["node_id"] for e in _json(http)["routing_history"]]
    assert "assembly" in local_nodes and "assembly" in http_nodes
    assert "quality" in local_nodes and "quality" in http_nodes
    assert "packaging" in local_nodes and "packaging" in http_nodes


def test_aws_03_given_fail_fixture_when_aws_then_escalated_like_local(
    jwt_secret: str, dynamodb_client: Any
):
    """
    TEST-AWS-03 parity — force_quality FAIL → escalated on both paths
    """
    local_gw, _ = build_local_gateway(root=REPO, use_memory=True)
    ctx = build_handler_context(
        root=REPO, dynamodb_client=dynamodb_client, table_name="hextory-fail"
    )
    payload = {"force_quality": "FAIL"}

    local = local_gw.run(
        workflow_id="starter_factory", sdd_id="DES-0002", payload=payload
    )
    http = handle_event(
        _event(
            "POST",
            "/runs",
            headers=_auth_header(jwt_secret),
            body={
                "sdd_id": "DES-0002",
                "workflow_id": "starter_factory",
                "payload": payload,
            },
        ),
        handler_context=ctx,
    )
    assert local.traveler.status == TravelerStatus.ESCALATED
    assert http["statusCode"] == 200
    assert _json(http)["status"] == "escalated"


# ---------------------------------------------------------------------------
# TEST-AWS-04 — DynamoDB checkpointer restart + resume (moto)
# ---------------------------------------------------------------------------


def test_aws_04_given_moto_dynamodb_when_new_instance_loads_then_resume_works(
    dynamodb_client: Any, jwt_secret: str
):
    """
    TEST-AWS-04 / AC-04
    Given a DynamoDbCheckpointer backed by moto
    When a traveler is saved and a fresh checkpointer instance loads it
    Then resume via gateway returns the same terminal traveler
    """
    cp1 = DynamoDbCheckpointer(table_name="hextory-cp", client=dynamodb_client)
    traveler = DigitalTraveler(
        traveler_id="trv_aws04",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.SHIPPED,
    )
    ref = cp1.save("trv_aws04", traveler)
    assert ref.startswith("dynamodb://")

    # When — "handler restart": new checkpointer, same moto table
    cp2 = DynamoDbCheckpointer(table_name="hextory-cp", client=dynamodb_client)
    loaded = cp2.load("trv_aws04")
    assert loaded is not None
    assert loaded.status == TravelerStatus.SHIPPED

    gw, _ = build_aws_gateway(
        root=REPO,
        checkpointer=cp2,
        idempotency_store=InMemoryIdempotencyStore(),
    )
    result = gw.resume("trv_aws04")

    assert result is not None
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.traveler_id == "trv_aws04"


# ---------------------------------------------------------------------------
# TEST-AWS-05 — LocalStack compose docs + moto harness
# ---------------------------------------------------------------------------


def test_aws_05_given_repo_when_inspect_then_localstack_docs_and_moto_harness_exist():
    """
    TEST-AWS-05 / AC-05
    Given the repo tree
    When operator artifacts are inspected
    Then LocalStack compose (or docs) exist and moto is the unit harness
    """
    compose = REPO / "adapters" / "aws" / "docker-compose.localstack.yml"
    assert compose.is_file()
    text = compose.read_text(encoding="utf-8")
    assert "localstack" in text.lower()
    assert "dynamodb" in text.lower()

    readme = (REPO / "adapters" / "aws" / "README.md").read_text(encoding="utf-8")
    assert "moto" in readme.lower()
    assert "localstack" in readme.lower()
    assert "HEXTORY_JWT_SECRET" in readme
    assert "real AWS" in readme or "real account" in readme.lower()

    # moto import used by this module proves the unit harness path.
    assert mock_aws is not None


# ---------------------------------------------------------------------------
# TEST-AWS-06 — JWT 401 ≠ Gatekeeper denial
# ---------------------------------------------------------------------------


def test_aws_06_given_no_token_when_post_runs_then_401(handler_ctx):
    """
    TEST-AWS-06 / AC-06
    Given no Authorization header
    When POST /runs
    Then 401 (not gate denial)
    """
    resp = handle_event(
        _event(
            "POST",
            "/runs",
            body={"sdd_id": "DES-0002", "workflow_id": "starter_factory", "payload": {}},
        ),
        handler_context=handler_ctx,
    )
    assert resp["statusCode"] == 401


def test_aws_06_given_invalid_token_when_get_runs_then_401(handler_ctx):
    """
    TEST-AWS-06
    Given an invalid bearer token
    When GET /runs/{id}
    Then 401
    """
    resp = handle_event(
        _event(
            "GET",
            "/runs/trv_missing",
            headers={"authorization": "Bearer not-a-valid-jwt"},
            path_params={"id": "trv_missing"},
        ),
        handler_context=handler_ctx,
    )
    assert resp["statusCode"] == 401


def test_aws_06_health_does_not_require_jwt(handler_ctx):
    resp = handle_event(_event("GET", "/health"), handler_context=handler_ctx)
    assert resp["statusCode"] == 200


# ---------------------------------------------------------------------------
# TEST-AWS-07 — no src leaks of boto3 / moto / localstack / adapters
# ---------------------------------------------------------------------------


def test_aws_07_src_does_not_import_boto_moto_localstack_or_adapters():
    """
    TEST-AWS-07 / AC-07 (+ TEST-0010)
    Given all Python files under src/
    When imports are scanned statically
    Then none reference boto3, botocore, moto, localstack, adapters
    """
    banned_prefixes = (
        "boto3",
        "botocore",
        "moto",
        "localstack",
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


# ---------------------------------------------------------------------------
# TEST-AWS-08 — uneployed IaC + CI must not deploy
# ---------------------------------------------------------------------------


def test_aws_08_given_iac_stub_when_inspect_ci_then_no_real_account_deploy():
    """
    TEST-AWS-08 / AC-09
    Given optional SAM/CDK/CFN stubs
    When CI workflows are inspected
    Then stubs exist as uneployed artifacts and CI has no real-account deploy steps
    """
    template = REPO / "adapters" / "aws" / "template.yaml"
    assert template.is_file()
    tpl = template.read_text(encoding="utf-8")
    assert "UNEPLOYED" in tpl or "Do not" in tpl or "DO NOT" in tpl
    assert "AWS::Serverless" in tpl or "AWS::DynamoDB" in tpl

    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    banned = (
        "sam deploy",
        "cdk deploy",
        "cloudformation deploy",
        "aws deploy",
        "terraform apply",
    )
    lowered = ci.lower()
    for token in banned:
        assert token not in lowered, f"CI must not deploy: found {token!r}"

    readme = (REPO / "adapters" / "aws" / "README.md").read_text(encoding="utf-8")
    assert "sam deploy" in readme.lower() or "do not" in readme.lower()


def test_aws_traveler_summary_shape_stable():
    """Helper shape used by Lambda responses stays walkable."""
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


def test_aws_optional_metrics_port_injection(jwt_secret: str, dynamodb_client: Any):
    """Optional DES-0006 MetricsPort can be injected on the AWS path."""
    metrics = InMemoryMetrics()
    ctx = build_handler_context(
        root=REPO,
        dynamodb_client=dynamodb_client,
        table_name="hextory-metrics",
        metrics=metrics,
    )
    resp = handle_event(
        _event(
            "POST",
            "/runs",
            headers=_auth_header(jwt_secret),
            body={
                "sdd_id": "DES-0002",
                "workflow_id": "starter_factory",
                "payload": {"force_quality": "PASS"},
            },
        ),
        handler_context=ctx,
    )
    assert resp["statusCode"] == 200
    # Best-effort counters should have moved (accepted / terminal).
    assert metrics.events  # non-empty after a successful run
