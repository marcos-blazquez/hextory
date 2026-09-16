"""GraphRunner port — pluggable workflow execution (DES-0002-B).

Core default is the pure registry walker. Adapters may supply LangGraph
(or other) runners; ``src/`` never imports LangGraph types.
"""

from __future__ import annotations

from typing import Optional, Protocol

from src.domain.traveler import DigitalTraveler
from src.graphs.registry import WorkflowDefinition
from src.ports.checkpointer import Checkpointer


class GraphRunner(Protocol):
    """Execute a registered WorkflowDefinition over a DigitalTraveler."""

    def run(
        self,
        definition: WorkflowDefinition,
        traveler: DigitalTraveler,
        *,
        checkpointer: Optional[Checkpointer] = None,
        max_steps: int = 64,
    ) -> DigitalTraveler:
        """Run until terminal status / no next edge / max_steps."""
        ...
