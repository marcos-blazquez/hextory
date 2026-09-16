"""LangGraph adapter — compiles WorkflowDefinition into a StateGraph.

Lives under adapters/ so ``src/`` stays free of langgraph imports (DES-0002-B / AC-11).
Traveler persistence uses the Checkpointer port (not LangGraph MemorySaver in core).
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from src.domain.statuses import TravelerStatus
from src.domain.traveler import DigitalTraveler
from src.graphs.registry import WorkflowDefinition
from src.graphs.runtime import resolve_next_node
from src.ports.checkpointer import Checkpointer


class _GraphState(TypedDict):
    traveler: DigitalTraveler
    steps: int
    last_node: Optional[str]


def _coerce_traveler(value: Any) -> DigitalTraveler:
    if isinstance(value, DigitalTraveler):
        return value
    if isinstance(value, dict):
        return DigitalTraveler.model_validate(value)
    raise TypeError(f"expected DigitalTraveler or dict, got {type(value)!r}")


def _is_terminal(definition: WorkflowDefinition, traveler: DigitalTraveler) -> bool:
    if traveler.status.value in definition.terminal_statuses:
        return True
    if traveler.status == TravelerStatus.ESCALATED:
        return True
    return False


def compile_workflow(
    definition: WorkflowDefinition,
    *,
    checkpointer: Optional[Checkpointer] = None,
    max_steps: int = 64,
):
    """Build and compile a LangGraph StateGraph from an open-ended registry definition."""
    if not definition.nodes:
        raise ValueError(f"workflow {definition.workflow_id} has no nodes")
    if definition.entry_node not in definition.nodes:
        raise KeyError(
            f"entry_node={definition.entry_node!r} missing from workflow {definition.workflow_id}"
        )

    builder: StateGraph = StateGraph(_GraphState)

    for node_id, fn in definition.nodes.items():
        builder.add_node(node_id, _make_node(node_id, fn, checkpointer=checkpointer))

    builder.add_edge(START, definition.entry_node)

    for node_id in definition.nodes:
        targets = {e.target for e in definition.edges if e.source == node_id}
        path_map: dict[Any, Any] = {t: t for t in targets}
        path_map[END] = END
        builder.add_conditional_edges(
            node_id,
            _make_router(definition, node_id, max_steps=max_steps),
            path_map,
        )

    return builder.compile()


def _make_node(
    node_id: str,
    fn,
    *,
    checkpointer: Optional[Checkpointer],
):
    def node(state: _GraphState) -> dict[str, Any]:
        traveler = _coerce_traveler(state["traveler"])
        traveler = fn(traveler)
        steps = int(state.get("steps") or 0) + 1
        if checkpointer is not None:
            ref = checkpointer.save(traveler.traveler_id, traveler)
            traveler.checkpoint_ref = ref
        return {"traveler": traveler, "steps": steps, "last_node": node_id}

    node.__name__ = f"lg_{node_id}"
    return node


def _make_router(definition: WorkflowDefinition, source: str, *, max_steps: int):
    def route(state: _GraphState) -> Any:
        traveler = _coerce_traveler(state["traveler"])
        steps = int(state.get("steps") or 0)
        if steps >= max_steps:
            return END
        if _is_terminal(definition, traveler):
            return END
        nxt = resolve_next_node(definition, source, traveler)
        return nxt if nxt is not None else END

    route.__name__ = f"route_from_{source}"
    return route


class LangGraphRunner:
    """GraphRunner implementation backed by LangGraph StateGraph."""

    def run(
        self,
        definition: WorkflowDefinition,
        traveler: DigitalTraveler,
        *,
        checkpointer: Optional[Checkpointer] = None,
        max_steps: int = 64,
    ) -> DigitalTraveler:
        graph = compile_workflow(
            definition,
            checkpointer=checkpointer,
            max_steps=max_steps,
        )
        result = graph.invoke(
            {
                "traveler": traveler,
                "steps": 0,
                "last_node": None,
            }
        )
        return _coerce_traveler(result["traveler"])
