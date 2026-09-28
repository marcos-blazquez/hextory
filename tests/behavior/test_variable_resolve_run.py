"""Behavior: `{{var}}` resolve at run accept (DES-0008 / TEST-VAR-03/05/06/07/08).

Given/When/Then scenarios in ordinary pytest (NG7: no Cucumber / Gherkin).
Traceability: REQ-0020 (proposed), REQ-0012, REQ-0013 → DES-0008-D/E/G + §3.3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from adapters.local.variable_source import InMemoryEnvironmentSource
from src.domain.statuses import TravelerStatus
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import GraphRegistry
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.ports.metrics import (
    METRIC_GATE_DENIALS,
    METRIC_RUNS_ACCEPTED,
    METRIC_RUNS_TERMINAL,
    InMemoryMetrics,
)
from src.ports.sdd_status import SddStatus
from src.ports.variable_resolver import REDACTED, KernelVariableResolver
from tests.conftest import FakeSddStatusReader

SECRET = "tok-very-secret-123"


def _gateway(
    *,
    statuses: Optional[dict[str, SddStatus]] = None,
    metrics: Optional[InMemoryMetrics] = None,
    with_resolver: bool = True,
) -> RequestGateway:
    registry = GraphRegistry()
    register_starter(registry)
    env = InMemoryEnvironmentSource(
        {"staging": {"region": "eu-west", "api_token": SECRET, "flow_greeting": "env-hi"}},
        secret_names={"api_token"},
    )
    return RequestGateway(
        gatekeeper=PolicyGatekeeper(
            FakeSddStatusReader(statuses or {"DES-0002": SddStatus.APPROVED})
        ),
        registry=registry,
        metrics=metrics,
        variable_resolver=KernelVariableResolver() if with_resolver else None,
        environment_source=env if with_resolver else None,
    )


def _all_text(result) -> str:
    return result.traveler.model_dump_json() + result.reason


def test_given_env_and_flow_vars_when_run_then_station_inputs_resolved_before_assembly():
    """
    TEST-VAR-05 / TEST-VAR-04 / AC-VAR-05 (DES-0008 §6 transcript)
    Given Environment profile "staging" (region) and in-flow flow_greeting overriding env
    When a starter run is accepted with prompt "Say {{flow_greeting}} to {{region}}"
    Then the station input reads the resolved text and payload["vars"] holds the snapshot
    """
    # Given
    gw = _gateway()
    payload = {"vars": {"flow_greeting": "hi"}, "prompt": "Say {{flow_greeting}} to {{region}}"}

    # When
    result = gw.run(
        workflow_id="starter_factory", sdd_id="DES-0002", payload=payload, env_profile="staging"
    )

    # Then
    assert result.denied is False
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.payload["prompt"] == "Say hi to eu-west"
    assert result.traveler.payload["vars"] == {
        "api_token": REDACTED,
        "flow_greeting": "hi",
        "region": "eu-west",
    }
    assert payload["prompt"] == "Say {{flow_greeting}} to {{region}}", "caller payload not mutated"


def test_given_undefined_var_when_run_then_fail_closed_before_any_node():
    """
    TEST-VAR-03 / AC-VAR-03 / DES-0008-D + §10
    Given an Approved workflow and a field binding {{missing}} and {{also_missing}}
    When the run is requested
    Then it fails closed before assembly with a structured, deterministic resolve error
    And the failure is not counted as a gate denial
    """
    # Given
    metrics = InMemoryMetrics()
    gw = _gateway(metrics=metrics)

    # When
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"prompt": "{{missing}} {{region}} {{also_missing}}"},
        env_profile="staging",
    )

    # Then
    assert result.denied is True
    assert result.traveler.status == TravelerStatus.DENIED
    assert all(e.node_id != "assembly" for e in result.traveler.routing_history)
    assert result.reason == (
        "variable resolve failed: undefined_variable: "
        "missing=[also_missing, missing] fields=[prompt]"
    )
    err = result.traveler.payload["_resolve_error"]
    assert err["code"] == "undefined_variable"
    assert err["missing_names"] == ["also_missing", "missing"]
    assert result.traveler.payload["prompt"] == "{{missing}} {{region}} {{also_missing}}"
    assert metrics.total(METRIC_GATE_DENIALS) == 0
    assert metrics.total(METRIC_RUNS_ACCEPTED) == 0
    assert metrics.get(
        METRIC_RUNS_TERMINAL, {"workflow_id": "starter_factory", "status": "denied"}
    ) == 1


def test_given_unknown_env_profile_when_run_then_fail_closed():
    """
    TEST-VAR-09 / Q-VAR-4 (present-but-missing profile → fail closed)
    Given no "prod" Environment profile
    When a run names env_profile="prod"
    Then the run is denied with env_profile_not_found and no node runs
    """
    gw = _gateway()
    result = gw.run(
        workflow_id="starter_factory", sdd_id="DES-0002", payload={}, env_profile="prod"
    )
    assert result.denied is True
    assert result.traveler.payload["_resolve_error"]["code"] == "env_profile_not_found"
    assert all(e.node_id != "assembly" for e in result.traveler.routing_history)


def test_given_draft_workflow_sdd_with_vars_when_run_then_gatekeeper_still_denies():
    """
    TEST-VAR-06 / AC-VAR-06 / NG1 (Gatekeeper unchanged)
    Given a Draft workflow SDD and a payload that would resolve cleanly
    When the run is requested with a resolver wired
    Then Gatekeeper denies exactly as before and no variables are resolved
    """
    # Given
    metrics = InMemoryMetrics()
    gw = _gateway(
        statuses={"DES-9999": SddStatus.DRAFT, "DES-0002": SddStatus.APPROVED},
        metrics=metrics,
    )

    # When
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-9999",
        payload={"prompt": "{{region}}"},
        env_profile="staging",
    )

    # Then
    assert result.denied is True
    assert "_resolve_error" not in result.traveler.payload
    assert result.traveler.payload["prompt"] == "{{region}}"
    assert metrics.total(METRIC_GATE_DENIALS) == 1


def test_given_secret_env_var_when_run_succeeds_or_fails_then_secret_never_in_notes_or_snapshot():
    """
    TEST-VAR-08 / DES-0008 §3.3 (redact in logs / snapshots / error snippets)
    Given a secret-backed api_token in the Environment profile
    When one run binds it successfully and another fails with the secret text in the template
    Then routing notes, audit, payload["vars"], error payload and reason never hold the raw secret
    And the successful station input does receive the concrete secret
    """
    # Given
    gw = _gateway()

    # When
    ok = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"auth_header": "Bearer {{api_token}}"},
        env_profile="staging",
    )
    bad = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"note": f"leaked {SECRET} {{{{nope}}}}"},
        env_profile="staging",
    )

    # Then
    assert ok.traveler.payload["auth_header"] == f"Bearer {SECRET}"
    assert ok.traveler.payload["vars"]["api_token"] == REDACTED
    notes = " ".join(e.notes for e in ok.traveler.routing_history)
    assert SECRET not in notes
    assert SECRET not in repr(bad.traveler.payload["_resolve_error"])
    assert SECRET not in bad.reason
    assert SECRET not in " ".join(e.notes for e in bad.traveler.routing_history)
    assert SECRET not in repr(bad.traveler.payload.get("vars"))


def test_given_no_resolver_wired_when_run_then_legacy_payload_untouched():
    """
    TEST-VAR-06 (no behavior change for existing wiring)
    Given a gateway built without a VariableResolverPort
    When a run carries bind-like text
    Then the payload passes through exactly as before (no vars snapshot added)
    """
    gw = _gateway(with_resolver=False)
    result = gw.run(workflow_id="starter_factory", sdd_id="DES-0002", payload={"prompt": "{{x}}"})
    assert result.denied is False
    assert result.traveler.payload["prompt"] == "{{x}}"
    assert "vars" not in result.traveler.payload


def test_var_07_this_module_uses_given_when_then_docstrings():
    """
    TEST-VAR-07 / AC-VAR-07
    Given this behavior module
    When each scenario docstring is inspected
    Then every scenario states Given, When and Then
    """
    import ast

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    tests = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert tests
    for fn in tests:
        doc = ast.get_docstring(fn) or ""
        for word in ("Given", "When", "Then"):
            assert word in doc, f"{fn.name} missing {word}"
