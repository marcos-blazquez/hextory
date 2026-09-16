"""Starter topology: assembly → quality → packaging (not a closed catalog)."""

from __future__ import annotations

from typing import Optional

from src.departments.assembly import NODE_ID as ASSEMBLY
from src.departments.assembly import run_assembly
from src.departments.packaging import NODE_ID as PACKAGING
from src.departments.packaging import run_packaging
from src.departments.quality import NODE_ID as QUALITY
from src.departments.quality import run_quality
from src.graphs.registry import Edge, GraphRegistry, WorkflowDefinition
from src.ports.llm import LlmPort

STARTER_WORKFLOW_ID = "starter_factory"


def build_starter_definition(
    sdd_id: str = "DES-0002",
    *,
    llm: Optional[LlmPort] = None,
) -> WorkflowDefinition:
    wf = WorkflowDefinition(
        workflow_id=STARTER_WORKFLOW_ID,
        sdd_id=sdd_id,
        entry_node=ASSEMBLY,
    )

    if llm is None:
        wf.register_node(ASSEMBLY, run_assembly)
        wf.register_node(QUALITY, run_quality)
    else:
        # Closures keep GraphRunner's unary call signature while injecting LlmPort.
        def _assembly(traveler):
            return run_assembly(traveler, llm=llm)

        def _quality(traveler):
            return run_quality(traveler, llm=llm)

        wf.register_node(ASSEMBLY, _assembly)
        wf.register_node(QUALITY, _quality)

    wf.register_node(PACKAGING, run_packaging)

    # assembly → quality (unconditional after assembly)
    wf.register_edge(Edge(source=ASSEMBLY, target=QUALITY, label="to_quality"))
    # quality PASS → packaging
    wf.register_edge(
        Edge(
            source=QUALITY,
            target=PACKAGING,
            on_decision="pass",
            label="pass_to_packaging",
        )
    )
    # quality FAIL → rework → assembly (while not escalated)
    wf.register_edge(
        Edge(
            source=QUALITY,
            target=ASSEMBLY,
            on_decision="rework",
            label="fail_rework",
        )
    )
    # escalated is terminal (no edge)
    return wf


def register_starter(
    registry: GraphRegistry,
    sdd_id: str = "DES-0002",
    *,
    llm: Optional[LlmPort] = None,
) -> WorkflowDefinition:
    definition = build_starter_definition(sdd_id=sdd_id, llm=llm)
    registry.register(definition)
    return definition
