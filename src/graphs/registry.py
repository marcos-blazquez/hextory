"""Open-ended graph registry (DES-0002-C).

Register nodes/edges by workflow_id without editing department core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from src.domain.traveler import DigitalTraveler

NodeFn = Callable[[DigitalTraveler], DigitalTraveler]


@dataclass
class Edge:
    """Conditional or unconditional edge from a node."""

    source: str
    target: str
    # When set, edge is taken only if traveler.status.value matches (or special keys).
    on_status: Optional[str] = None
    # When set, match last routing decision value.
    on_decision: Optional[str] = None
    label: str = ""


@dataclass
class WorkflowDefinition:
    workflow_id: str
    sdd_id: str
    entry_node: str
    nodes: dict[str, NodeFn] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    terminal_statuses: frozenset[str] = field(
        default_factory=lambda: frozenset({"shipped", "escalated", "denied"})
    )

    def register_node(self, node_id: str, fn: NodeFn) -> None:
        self.nodes[node_id] = fn

    def register_edge(self, edge: Edge) -> None:
        self.edges.append(edge)


class GraphRegistry:
    """Lookup workflow_id → WorkflowDefinition. Unknown → None."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> None:
        self._workflows[definition.workflow_id] = definition

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(workflow_id)

    def has(self, workflow_id: str) -> bool:
        return workflow_id in self._workflows

    def workflow_ids(self) -> list[str]:
        return sorted(self._workflows.keys())
