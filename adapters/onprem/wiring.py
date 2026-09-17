"""Wire RequestGateway for the on-prem adapter (DES-0004-D).

Same Gatekeeper + LocalSddStatusReader + starter registry semantics as
``adapters.local.cli.build_gateway``. Persistence defaults to Postgres when a
DSN is available; tests may inject MemoryCheckpointer / in-memory idempotency.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

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


def _repo_root() -> Path:
    # adapters/onprem/wiring.py → hextory/
    return Path(__file__).resolve().parents[2]


def build_gateway(
    *,
    root: Optional[Path] = None,
    checkpointer: Optional[Checkpointer] = None,
    idempotency_store: Optional[IdempotencyStore] = None,
    runner: Optional[GraphRunner] = None,
    llm: Optional[LlmPort] = None,
    use_memory: bool = False,
    database_url: Optional[str] = None,
) -> tuple[RequestGateway, Checkpointer]:
    """Build gateway with on-prem ports.

    Default: Postgres checkpointer + Postgres idempotency when not
    ``use_memory`` and a DSN is provided/resolvable. Pass explicit
    ``checkpointer`` / ``idempotency_store`` for tests.
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
    # Prefer env LLM when not overridden (same as local CLI).
    if llm is None:
        try:
            selected_llm = llm_from_env()
        except ValueError:
            selected_llm = NullLlm()

    registry = GraphRegistry()
    register_starter(registry, sdd_id="DES-0002", llm=selected_llm)

    dsn = database_url or os.environ.get("HEXTORY_DATABASE_URL", "").strip() or None

    if checkpointer is not None:
        cp: Checkpointer = checkpointer
    elif use_memory or not dsn:
        cp = MemoryCheckpointer()
    else:
        from adapters.onprem.postgres_checkpointer import PostgresCheckpointer

        cp = PostgresCheckpointer(dsn)

    if idempotency_store is not None:
        idem: IdempotencyStore = idempotency_store
    elif use_memory or isinstance(cp, MemoryCheckpointer) or not dsn:
        idem = InMemoryIdempotencyStore()
    else:
        from adapters.onprem.postgres_idempotency import PostgresIdempotencyStore

        idem = PostgresIdempotencyStore(dsn)

    selected = runner if runner is not None else PureGraphRunner()
    gateway = RequestGateway(
        gatekeeper=gatekeeper,
        registry=registry,
        checkpointer=cp,
        runner=selected,
        idempotency_store=idem,
    )
    return gateway, cp
