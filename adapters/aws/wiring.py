"""Wire RequestGateway for the AWS adapter (DES-0005-F).

Same Gatekeeper + LocalSddStatusReader + starter registry semantics as
``adapters.local.cli.build_gateway`` / ``adapters.onprem.wiring``. Persistence
defaults to DynamoDB when not ``use_memory``; tests inject moto clients.
Optional MetricsPort injection (DES-0006) when provided.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from adapters.local.echo_llm import llm_from_env
from adapters.local.memory_checkpointer import MemoryCheckpointer
from adapters.local.sdd_status_reader import LocalSddStatusReader
from src.gateway.request_gateway import RequestGateway
from src.graphs.registry import GraphRegistry
from src.graphs.runtime import PureGraphRunner
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.ports.checkpointer import Checkpointer
from src.ports.graph_runner import GraphRunner
from src.ports.idempotency import IdempotencyStore, InMemoryIdempotencyStore
from src.ports.llm import LlmPort, NullLlm
from src.ports.metrics import MetricsPort


def _repo_root() -> Path:
    # adapters/aws/wiring.py → hextory/
    return Path(__file__).resolve().parents[2]


def build_gateway(
    *,
    root: Optional[Path] = None,
    checkpointer: Optional[Checkpointer] = None,
    idempotency_store: Optional[IdempotencyStore] = None,
    runner: Optional[GraphRunner] = None,
    llm: Optional[LlmPort] = None,
    use_memory: bool = False,
    dynamodb_client: Any = None,
    table_name: Optional[str] = None,
    metrics: Optional[MetricsPort] = None,
) -> tuple[RequestGateway, Checkpointer]:
    """Build gateway with AWS ports.

    Default: DynamoDB checkpointer + DynamoDB idempotency when not
    ``use_memory``. Pass explicit ``checkpointer`` / ``idempotency_store``
    or a moto ``dynamodb_client`` for tests.
    """
    root = root or _repo_root()
    manifest = root / "config" / "sdd_status.json"
    docs_design = root / "docs" / "design"
    reader = LocalSddStatusReader(
        manifest_path=manifest if manifest.is_file() else None,
        docs_design_dir=docs_design if docs_design.is_dir() else None,
    )
    gatekeeper = PolicyGatekeeper(reader)
    selected_llm: LlmPort = llm if llm is not None else NullLlm()
    if llm is None:
        try:
            selected_llm = llm_from_env()
        except ValueError:
            selected_llm = NullLlm()

    registry = GraphRegistry()
    register_starter(registry, sdd_id="DES-0002", llm=selected_llm)

    if checkpointer is not None:
        cp: Checkpointer = checkpointer
    elif use_memory:
        cp = MemoryCheckpointer()
    else:
        from adapters.aws.dynamodb_checkpointer import DynamoDbCheckpointer

        cp = DynamoDbCheckpointer(table_name=table_name, client=dynamodb_client)
        cp.ensure_table()

    if idempotency_store is not None:
        idem: IdempotencyStore = idempotency_store
    elif use_memory or isinstance(cp, MemoryCheckpointer):
        idem = InMemoryIdempotencyStore()
    else:
        from adapters.aws.dynamodb_idempotency import DynamoDbIdempotencyStore

        idem = DynamoDbIdempotencyStore(
            table_name=table_name,
            client=dynamodb_client,
            checkpointer=cp if hasattr(cp, "ensure_table") else None,
        )

    selected = runner if runner is not None else PureGraphRunner()
    gateway = RequestGateway(
        gatekeeper=gatekeeper,
        registry=registry,
        checkpointer=cp,
        runner=selected,
        idempotency_store=idem,
        metrics=metrics,
    )
    return gateway, cp
