"""Pure graph runtime — walks registry edges; optional checkpointer via port.

Core does not import MemorySaver or LangGraph types (DES-0002-J / AC-11).
"""

from __future__ import annotations

from typing import Optional

from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.graphs.registry import Edge, WorkflowDefinition
from src.ports.checkpointer import Checkpointer


def _last_decision(traveler: DigitalTraveler) -> Optional[str]:
    if not traveler.routing_history:
        return None
    return traveler.routing_history[-1].decision.value


def _match_edge(edge: Edge, traveler: DigitalTraveler) -> bool:
    if edge.on_status is not None and traveler.status.value != edge.on_status:
        return False
    if edge.on_decision is not None and _last_decision(traveler) != edge.on_decision:
        return False
    return True


def resolve_next_node(
    definition: WorkflowDefinition,
    current: str,
    traveler: DigitalTraveler,
) -> Optional[str]:
    """Pick the next node_id from registry edges (shared by pure + LangGraph adapters)."""
    candidates = [e for e in definition.edges if e.source == current]
    # Prefer conditional matches; fall back to unconditional (no on_* set).
    conditional = [e for e in candidates if e.on_status or e.on_decision]
    unconditional = [e for e in candidates if not e.on_status and not e.on_decision]

    for edge in conditional:
        if _match_edge(edge, traveler):
            return edge.target
    for edge in unconditional:
        if _match_edge(edge, traveler):
            return edge.target
    return None


def run_workflow(
    definition: WorkflowDefinition,
    traveler: DigitalTraveler,
    *,
    checkpointer: Optional[Checkpointer] = None,
    max_steps: int = 64,
) -> DigitalTraveler:
    """Execute from entry_node until terminal status or no next edge."""
    node_id: Optional[str] = definition.entry_node
    steps = 0

    while node_id is not None and steps < max_steps:
        if traveler.status.value in definition.terminal_statuses:
            break

        fn = definition.nodes.get(node_id)
        if fn is None:
            raise KeyError(f"unknown node_id={node_id} in workflow {definition.workflow_id}")

        traveler = fn(traveler)
        steps += 1

        if checkpointer is not None:
            ref = checkpointer.save(traveler.traveler_id, traveler)
            traveler.checkpoint_ref = ref

        if traveler.status.value in definition.terminal_statuses:
            break

        # After quality escalated, stop even if somehow not in terminal set yet.
        if traveler.status == TravelerStatus.ESCALATED:
            break

        node_id = resolve_next_node(definition, node_id, traveler)

    return traveler


class PureGraphRunner:
    """GraphRunner that delegates to the pure registry walker (default / stable path)."""

    def run(
        self,
        definition: WorkflowDefinition,
        traveler: DigitalTraveler,
        *,
        checkpointer: Optional[Checkpointer] = None,
        max_steps: int = 64,
    ) -> DigitalTraveler:
        return run_workflow(
            definition,
            traveler,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )
