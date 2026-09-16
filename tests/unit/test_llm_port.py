"""TDD: LlmPort — Null default, Scripted/Fake, optional department use."""

from __future__ import annotations

from src.departments.assembly import run_assembly
from src.departments.quality import run_quality
from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import GraphRegistry
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.ports.llm import FakeLlm, NullLlm, ScriptedLlm
from src.ports.sdd_status import SddStatus
from tests.conftest import FakeSddStatusReader


def _traveler(**payload) -> DigitalTraveler:
    return DigitalTraveler(
        traveler_id="trv_test",
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        status=TravelerStatus.ACCEPTED,
        payload=dict(payload),
    )


def test_null_llm_returns_empty():
    assert NullLlm().complete("hello") == ""


def test_scripted_llm_exact_and_default():
    llm = ScriptedLlm({"ping": "pong"}, default="fallback")
    assert llm.complete("ping") == "pong"
    assert llm.complete("other") == "fallback"
    assert llm.calls == ["ping", "other"]


def test_fake_llm_alias_is_scripted():
    assert FakeLlm is ScriptedLlm


def test_assembly_without_assist_ignores_llm():
    llm = ScriptedLlm(default="SHOULD_NOT_APPEAR")
    t = run_assembly(_traveler(product="widget"), llm=llm)
    assert t.payload.get("assembled") is True
    assert "llm_note" not in t.payload
    assert llm.calls == []


def test_assembly_with_assist_records_note():
    llm = ScriptedLlm(prefix_scripts={"Assemble": "assembled-ok"}, default="")
    t = run_assembly(_traveler(product="gizmo", llm_assist=True), llm=llm)
    assert t.payload["llm_note"] == "assembled-ok"
    assert any(a.action == "llm_assist" for a in t.audit)
    assert llm.calls and llm.calls[0].startswith("Assemble")


def test_quality_force_pass_unchanged_without_assist():
    t = _traveler(assembled=True, force_quality="PASS")
    out = run_quality(t, llm=ScriptedLlm(default="nope"))
    assert out.routing_history[-1].decision.value == "pass"
    assert "quality_llm_note" not in out.payload


def test_quality_with_assist_records_note_and_still_respects_force():
    llm = ScriptedLlm(prefix_scripts={"Quality": "looks-good"})
    t = _traveler(assembled=True, force_quality="PASS", llm_assist=True)
    out = run_quality(t, llm=llm)
    assert out.payload["quality_llm_note"] == "looks-good"
    assert out.routing_history[-1].decision.value == "pass"


def test_gateway_with_scripted_llm_and_assist_flag():
    llm = ScriptedLlm(prefix_scripts={"Assemble": "asm-note", "Quality": "qa-note"})
    registry = GraphRegistry()
    register_starter(registry, llm=llm)
    gw = RequestGateway(
        gatekeeper=PolicyGatekeeper(
            FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})
        ),
        registry=registry,
    )
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS", "llm_assist": True, "product": "x"},
    )
    assert result.denied is False
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert result.traveler.payload.get("llm_note") == "asm-note"
    assert result.traveler.payload.get("quality_llm_note") == "qa-note"


def test_gateway_default_null_path_unchanged():
    """Existing force_quality path without llm_assist / without LLM injection."""
    registry = GraphRegistry()
    register_starter(registry)  # no llm
    gw = RequestGateway(
        gatekeeper=PolicyGatekeeper(
            FakeSddStatusReader({"DES-0002": SddStatus.APPROVED})
        ),
        registry=registry,
    )
    result = gw.run(
        workflow_id="starter_factory",
        sdd_id="DES-0002",
        payload={"force_quality": "PASS"},
    )
    assert result.traveler.status == TravelerStatus.SHIPPED
    assert "llm_note" not in result.traveler.payload
