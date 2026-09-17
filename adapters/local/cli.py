"""Local CLI: hextory run / status (DES-0002-J).

Default persistence is FileCheckpointer under ``.hextory/`` (travelers + FAIL
artifacts + idempotency map). Pass ``checkpointer=MemoryCheckpointer()`` or
``--memory`` for process-local / unit-test use. Optional ``--store-dir``
overrides the store root.

Runtime: ``--runtime pure`` (default, stable) or ``--runtime langgraph``
(optional extra: ``pip install -e ".[dev,langgraph]"``).

LLM: ``HEXTORY_LLM_MODE=null|echo|openai`` (default null; no cloud keys required).
Pass ``--llm-assist`` to set ``payload["llm_assist"]=True`` when a non-null LLM
is wired.

Metrics (DES-0006 / Q-OBS-3): after ``run``, dump counters to stdout (``--metrics-dump``)
or a file (``--metrics-file PATH``). No HTTP ``/metrics`` on local first slice.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from adapters.local.echo_llm import llm_from_env
from adapters.local.file_checkpointer import DEFAULT_STORE_DIRNAME, FileCheckpointer
from adapters.local.file_idempotency import FileIdempotencyStore
from adapters.local.memory_checkpointer import MemoryCheckpointer
from adapters.local.metrics_dump import dump_metrics
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
from src.ports.metrics import InMemoryMetrics, MetricsPort


def _repo_root() -> Path:
    # adapters/local/cli.py → hextory/
    return Path(__file__).resolve().parents[2]


def default_store_dir(root: Optional[Path] = None) -> Path:
    return (root or _repo_root()) / DEFAULT_STORE_DIRNAME


def resolve_runner(runtime: str = "pure") -> GraphRunner:
    """Select GraphRunner. Default ``pure`` for stability; ``langgraph`` needs optional extra."""
    key = (runtime or "pure").strip().lower()
    if key == "pure":
        return PureGraphRunner()
    if key == "langgraph":
        try:
            from adapters.local.langgraph_runtime import LangGraphRunner
        except ImportError as exc:  # pragma: no cover - exercised when extra missing
            raise SystemExit(
                "langgraph runtime requested but langgraph is not installed. "
                'Install with: pip install -e ".[dev,langgraph]"'
            ) from exc
        return LangGraphRunner()
    raise SystemExit(f"unknown --runtime {runtime!r}; choose pure|langgraph")


def build_gateway(
    *,
    root: Optional[Path] = None,
    store_dir: Optional[Path] = None,
    checkpointer: Optional[Checkpointer] = None,
    use_memory: bool = False,
    runtime: str = "pure",
    runner: Optional[GraphRunner] = None,
    llm: Optional[LlmPort] = None,
    idempotency_store: Optional[IdempotencyStore] = None,
    metrics: Optional[MetricsPort] = None,
) -> tuple[RequestGateway, Checkpointer]:
    """Wire Gatekeeper + starter registry + checkpointer + optional GraphRunner/LLM.

    Default checkpointer is FileCheckpointer under ``root/.hextory``.
    MemoryCheckpointer is used when ``use_memory=True`` or when an explicit
    MemoryCheckpointer is passed (unit tests).
    Default runtime is pure registry walker; pass ``runtime="langgraph"`` or an
    explicit ``runner`` for the LangGraph adapter.
    Idempotency: FileIdempotencyStore under the same store root (or in-memory
    when ``use_memory``).
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
    registry = GraphRegistry()
    register_starter(registry, sdd_id="DES-0002", llm=selected_llm)

    resolved_store = store_dir or default_store_dir(root)
    if checkpointer is not None:
        cp: Checkpointer = checkpointer
    elif use_memory:
        cp = MemoryCheckpointer()
    else:
        cp = FileCheckpointer(resolved_store)

    if idempotency_store is not None:
        idem: IdempotencyStore = idempotency_store
    elif use_memory or isinstance(cp, MemoryCheckpointer):
        idem = InMemoryIdempotencyStore()
    else:
        idem = FileIdempotencyStore(resolved_store)

    selected = runner if runner is not None else resolve_runner(runtime)
    gateway = RequestGateway(
        gatekeeper=gatekeeper,
        registry=registry,
        checkpointer=cp,
        runner=selected,
        idempotency_store=idem,
        metrics=metrics,
    )
    return gateway, cp


def _print_traveler_summary(traveler: Any, *, denied: bool = False, reason: str = "") -> None:
    print(f"traveler_id={traveler.traveler_id}")
    print(f"status={traveler.status.value}")
    print(f"sdd_id={traveler.sdd_id}")
    print(f"workflow_id={traveler.workflow_id}")
    print(f"rework_count={traveler.rework_count}/{traveler.max_rework}")
    if traveler.checkpoint_ref:
        print(f"checkpoint_ref={traveler.checkpoint_ref}")
    if denied or traveler.status.value == "denied":
        print(f"denied=True reason={reason or _deny_reason(traveler)}")
    if traveler.payload.get("llm_note"):
        print(f"llm_note={traveler.payload['llm_note']}")
    if traveler.payload.get("quality_llm_note"):
        print(f"quality_llm_note={traveler.payload['quality_llm_note']}")
    fail_arts = [a for a in traveler.artifact_refs if a.kind in ("quality_fail", "defect")]
    if fail_arts:
        print(f"quality_fail_artifacts={len(fail_arts)}")
        for a in fail_arts[-3:]:
            print(f"  {a.kind}: {a.uri}")
    history = traveler.routing_history
    tail = history[-5:] if len(history) > 5 else history
    print("routing_history (tail):")
    for ev in tail:
        print(f"  [{ev.seq}] {ev.node_id}/{ev.decision.value} — {ev.notes}")


def _deny_reason(traveler: Any) -> str:
    for ev in reversed(traveler.routing_history):
        if ev.decision.value == "deny":
            return ev.notes
    return ""


def _store_dir_from_args(args: argparse.Namespace, root: Path) -> Path:
    if getattr(args, "store_dir", None):
        return Path(args.store_dir)
    return default_store_dir(root)


def cmd_run(args: argparse.Namespace) -> int:
    root = _repo_root()
    runtime = getattr(args, "runtime", "pure") or "pure"
    try:
        llm = llm_from_env()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    metrics: Optional[MetricsPort] = None
    if getattr(args, "metrics_dump", False) or getattr(args, "metrics_file", None):
        metrics = InMemoryMetrics()
    if args.memory:
        gateway, _ = build_gateway(
            root=root, use_memory=True, runtime=runtime, llm=llm, metrics=metrics
        )
    else:
        gateway, _ = build_gateway(
            root=root,
            store_dir=_store_dir_from_args(args, root),
            runtime=runtime,
            llm=llm,
            metrics=metrics,
        )
    payload: dict[str, Any] = {}
    if args.payload:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    if args.force_quality:
        payload["force_quality"] = args.force_quality
    if args.fail_until_rework is not None:
        payload["fail_until_rework"] = args.fail_until_rework
    if getattr(args, "llm_assist", False):
        payload["llm_assist"] = True
    if getattr(args, "timeout_seconds", None) is not None:
        payload["timeout_seconds"] = args.timeout_seconds

    result = gateway.run(
        workflow_id=args.workflow,
        sdd_id=args.sdd,
        payload=payload,
        idempotency_key=args.idempotency_key,
    )
    _print_traveler_summary(result.traveler, denied=result.denied, reason=result.reason)
    if metrics is not None:
        dump_metrics(metrics, dest=getattr(args, "metrics_file", None) or None)
    return 1 if result.denied else 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _repo_root()
    # Optional override: load a snapshot JSON (still supported for ad-hoc dumps).
    if args.from_json:
        from src.domain.traveler import DigitalTraveler

        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        traveler = DigitalTraveler.model_validate(data)
        _print_traveler_summary(traveler)
        return 0

    runtime = getattr(args, "runtime", "pure") or "pure"
    if args.memory:
        gateway, _ = build_gateway(root=root, use_memory=True, runtime=runtime)
    else:
        gateway, _ = build_gateway(
            root=root,
            store_dir=_store_dir_from_args(args, root),
            runtime=runtime,
        )

    traveler = gateway.status(args.traveler)
    if traveler is None:
        print(f"traveler not found: {args.traveler}", file=sys.stderr)
        store = _store_dir_from_args(args, root)
        print(
            f"hint: expected file under {store / 'travelers'} "
            f"(or pass --from-json <snapshot>)",
            file=sys.stderr,
        )
        return 1
    _print_traveler_summary(traveler)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hextory", description="Hextory local factory CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Start a workflow run")
    run_p.add_argument("--sdd", required=True, help="SDD id e.g. DES-0002")
    run_p.add_argument("--workflow", default="starter_factory")
    run_p.add_argument("--payload", help="Path to JSON payload")
    run_p.add_argument("--force-quality", choices=["PASS", "FAIL"])
    run_p.add_argument("--fail-until-rework", type=int, default=None)
    run_p.add_argument("--idempotency-key", default=None)
    run_p.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Optional request timeout recorded as deadline metadata",
    )
    run_p.add_argument(
        "--llm-assist",
        action="store_true",
        help="Ask assembly/quality to call the wired LlmPort (HEXTORY_LLM_MODE)",
    )
    run_p.add_argument(
        "--store-dir",
        default=None,
        help=f"FileCheckpointer root (default: <repo>/{DEFAULT_STORE_DIRNAME})",
    )
    run_p.add_argument(
        "--memory",
        action="store_true",
        help="Use process-local MemoryCheckpointer instead of file store",
    )
    run_p.add_argument(
        "--runtime",
        choices=["pure", "langgraph"],
        default="pure",
        help="Graph runner: pure (default, stable) or langgraph (optional extra)",
    )
    run_p.add_argument(
        "--metrics-dump",
        action="store_true",
        help="After run, dump DES-0006 metric counters to stdout (Q-OBS-3)",
    )
    run_p.add_argument(
        "--metrics-file",
        default=None,
        help="After run, write metric dump to this file path (Q-OBS-3)",
    )
    run_p.set_defaults(func=cmd_run)

    st_p = sub.add_parser("status", help="Show traveler status / routing tail")
    st_p.add_argument("--traveler", required=True)
    st_p.add_argument("--from-json", help="Load traveler snapshot JSON (optional override)")
    st_p.add_argument(
        "--store-dir",
        default=None,
        help=f"FileCheckpointer root (default: <repo>/{DEFAULT_STORE_DIRNAME})",
    )
    st_p.add_argument(
        "--memory",
        action="store_true",
        help="Use MemoryCheckpointer (empty unless same process)",
    )
    st_p.add_argument(
        "--runtime",
        choices=["pure", "langgraph"],
        default="pure",
        help="Graph runner used when building gateway (status loads via checkpointer)",
    )
    st_p.set_defaults(func=cmd_status)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
