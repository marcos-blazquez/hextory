# Hextory

**Hextory** is a public, design-gated "dark factory" for shipping production software without relying on human code review as the primary quality gate.

Instead of humans line-reading every pull request, **every workflow requires a Software Design Document (SDD)** that humans *and* agents review and approve. Code generation and implementation are **gated** on that approved design. Agents implement; design docs carry the shared contract.

> Status: **First-slice scaffold**. Vision [DES-0001](docs/design/0001-hextory-vision.md) and factory engine [DES-0002](docs/design/0002-factory-engine.md) are **Approved**. Local vertical slice (`src/` + `adapters/local` + `tests/`) is in tree; on-prem/AWS still deferred. [DES-0003](docs/design/0003-workflow-studio.md) (Hextory Studio UI) is **Draft ideation only** — not authorized to build. See the [maturity scorecard](docs/maturity/SCORECARD.md).

## Dark-factory thesis

A **dark factory** (lights-out manufacturing) runs production without humans on the floor. Applied to software:

| Traditional | Hextory dark factory |
|---|---|
| Humans review code diffs | Humans + agents review **design docs** |
| Code is the source of truth for intent | **Approved SDD** is the source of truth for intent |
| Agents dump PRs for humans to babysit | Agents implement only after **design-doc gates** are green |
| Review bottlenecks scale poorly | Design review scales; implementation is automated |

Humans stay in the loop where it matters: architecture, non-goals, failure policy, and acceptance criteria. Agents draft, review against the SDD, implement, and rework when quality fails.

## Design-doc-over-code-review principle

1. **No Approved SDD → no implementation.** Agents must not generate mergeable product code until the workflow SDD is **Approved**.
2. **Dual design review.** Architecture-critical sections need human approval; agents provide structured design review as a required second pass.
3. **Traceability.** Requirements (`REQ-*`), design decisions (`DES-*`), implementation units, and tests (`TEST-*`) stay linked.
4. **Verification against the SDD.** "Done" means the shippable artifact satisfies the approved design and acceptance criteria—not that a human skimmed a diff.

### Human merge approval ≠ line-by-line code review

- **No human line-by-line CODE review is required** to ship. Agents implement and verify against the Approved SDD; humans do not walk the PR diff as the primary gate.
- **Merges to the main line still require human approval.** That approval is a **doc-review gate**: the human confirms the relevant SDD is Approved, gate criteria are green, and the change set is in scope for that design—not a code walkthrough.
- Optional human audits of code may happen, but they are not the merge prerequisite.

## Repository layout

```
hextory/
├── README.md                          # This file
├── LICENSE                            # MIT
├── .gitignore
├── pyproject.toml                     # pytest, pydantic v2; optional langgraph
├── config/
│   └── sdd_status.json                # Q-GATE-1 interim Approved/Draft manifest
├── docs/
│   ├── design/
│   │   ├── TEMPLATE.md                # SDD template for any workflow
│   │   ├── 0001-hextory-vision.md     # Meta-system vision (Approved)
│   │   └── 0002-factory-engine.md     # Factory engine SDD (Approved)
│   ├── workflows/
│   │   └── design-doc-review.md       # Ideation → Approved → Shipped
│   ├── maturity/
│   │   ├── ASPECTS.md                 # 0–100 maturity aspects
│   │   └── SCORECARD.md               # Current baseline scores
│   └── architecture/
│       └── factory-engine-intent.md   # Intent input (non-gating; see DES-0002)
├── src/                               # PURE core (no adapters imports)
│   ├── domain/                        # DigitalTraveler, routing_history
│   ├── ports/                         # Gatekeeper, Checkpointer, GraphRunner, SddStatusReader, …
│   ├── departments/                   # assembly, quality, packaging
│   ├── graphs/                        # registry + starter topology + runtime
│   ├── policies/                      # gate, rework, interceptors
│   └── gateway/                       # RequestGateway
├── adapters/
│   └── local/                         # CLI + checkpointers + SddStatusReader + optional LangGraph runtime
└── tests/
    ├── unit/
    ├── behavior/                      # Given/When/Then in ordinary pytest (not Cucumber)
    └── adapters/
```

First-slice engine (`DES-0002-J`) is present: pure `src/` + `adapters/local` + `tests/`. On-prem/AWS adapters remain deferred.

## Run tests and local CLI (DES-0002 first slice)

Human **main-line merge** still means **design-doc readiness** (Approved SDD + green gates)—not a code walkthrough.

```bash
cd /workspace/hextory   # or your clone root
python -m pip install -e ".[dev]"
# Optional LangGraph runtime + parity tests:
# python -m pip install -e ".[dev,langgraph]"
python -m pytest
```

CLI smoke (Approved synthetic run → shipped):

```bash
python -m adapters.local.cli run --sdd DES-0002 --workflow starter_factory --force-quality PASS
# or, after install: hextory run --sdd DES-0002 --workflow starter_factory --force-quality PASS
```

Denied examples (Gatekeeper):

```bash
python -m adapters.local.cli run --sdd DES-9999 --workflow starter_factory   # Draft in config/sdd_status.json
```

`config/sdd_status.json` plus markdown `**Status**` in `docs/design/` feed the local `SddStatusReader` (Q-GATE-1: fail closed; both must agree when present).

### Persistent store (FileCheckpointer)

By default the CLI writes travelers and quality FAIL artifacts under **`.hextory/`** (gitignored):

```
.hextory/
  travelers/{traveler_id}.json
  artifacts/{traveler_id}/quality_fail_{report_id}.json
  idempotency/{key}.json
```

`checkpoint_ref` is a `file://…` URI. Cross-process status no longer needs `--from-json`:

```bash
# Force FAIL → escalated; leaves traveler JSON + fail artifacts on disk
python -m adapters.local.cli run --sdd DES-0002 --force-quality FAIL --store-dir /tmp/hextory-store
# Note traveler_id from the run output, then in a new process:
python -m adapters.local.cli status --traveler trv_… --store-dir /tmp/hextory-store
```

- `--store-dir PATH` — override store root (run and status).
- `--memory` — process-local `MemoryCheckpointer` (unit tests / no disk).
- `--from-json` — still available on `status` as an optional snapshot override.


### Idempotency keys

Pass `--idempotency-key KEY` on `run`. Repeated requests with the same key return the **same traveler** (including prior denials) instead of starting a new run. Different keys create new travelers. Keys without a prior entry are recorded after the first completed run.

- In-process / `--memory`: `InMemoryIdempotencyStore`
- File store: `.hextory/idempotency/{key}.json` → `{traveler_id}` (`FileIdempotencyStore`)

Design choice: dedicated `IdempotencyStore` port (`src/ports/idempotency.py`) maps key→traveler_id; Checkpointer stays traveler_id-keyed. The interceptor resolves a replay id; the gateway loads and returns that traveler.

### Quota / timeout defaults

Interceptor order: logging → idempotency → **quota/timeout** → design-doc gate.

Default quota is generous so local suites stay green: **10_000 requests / 3600s** sliding window. Tests inject a fake `Clock` and lower `max_requests` to prove denial. Optional `payload["timeout_seconds"]` (or `--timeout-seconds`) records a deadline in traveler metadata without aborting the run in this slice.

### Local LLM modes (`HEXTORY_LLM_MODE`)

No cloud API keys are required for defaults or tests.

| Mode | Behavior |
|---|---|
| `null` (default) | `NullLlm` — empty completions |
| `echo` | `EchoLlm` — deterministic local echo of the prompt |
| `openai` | Optional OpenAI-compatible client; **fail-closed** if `HEXTORY_OPENAI_API_KEY` / `OPENAI_API_KEY` unset |

Pass `--llm-assist` (sets `payload["llm_assist"]=true`) so assembly/quality call the wired `LlmPort` and record a short note on the traveler. Existing `force_quality` paths work unchanged without assist / without an LLM.

```bash
HEXTORY_LLM_MODE=echo python -m adapters.local.cli run \
  --sdd DES-0002 --force-quality PASS --llm-assist --memory
```

### Graph runtimes (`--runtime pure|langgraph`)

Default execution is the **pure** registry walker in `src/graphs/runtime.py` (stable; no LangGraph dependency). An optional **LangGraph** adapter lives under `adapters/local/langgraph_runtime.py` and implements the same `GraphRunner` port so `RequestGateway` stays hexagonal — `src/` never imports `langgraph`.

```bash
# Stable default
python -m adapters.local.cli run --sdd DES-0002 --force-quality PASS --runtime pure

# Optional LangGraph path (requires: pip install -e ".[dev,langgraph]")
python -m adapters.local.cli run --sdd DES-0002 --force-quality PASS --runtime langgraph
```

Parity tests under `tests/adapters/test_langgraph_runtime.py` skip cleanly when `langgraph` is not installed. Traveler persistence always goes through the `Checkpointer` port (FileCheckpointer / MemoryCheckpointer), not LangGraph’s MemorySaver in core.

## Contributing and CI

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the design-doc gate, hexagonal rules, and testing layout.

CI workflow (GitHub Actions, once the repo is hosted): [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — pytest + `scripts/ci_design_gates.py`. Locally:

```bash
python scripts/ci_design_gates.py
pytest
```

`git init` / remotes stay off until maintainers enable them; these files can land first.

## How to contribute (via design docs)

1. **Read** [docs/workflows/design-doc-review.md](docs/workflows/design-doc-review.md).
2. **Copy** [docs/design/TEMPLATE.md](docs/design/TEMPLATE.md) to `docs/design/NNNN-slug.md` (next free number).
3. **Fill** all sections, including dark-factory extras (acceptance criteria, non-goals, failure/rework policy, gate criteria, traceability IDs).
4. **Submit for dual review** (human + agent). Iterate until **Approved**.
5. **Only then** may agents generate implementation. Verification must map back to the SDD.

Code-only contributions that bypass an Approved SDD will be rejected once public git PR policy is active.

## Key links

| Doc | Purpose |
|---|---|
| [Maturity scorecard](docs/maturity/SCORECARD.md) | Honest baseline + next actions |
| [Maturity aspects](docs/maturity/ASPECTS.md) | What 0–100 means per aspect |
| [Design-doc review workflow](docs/workflows/design-doc-review.md) | States, rules, naming |
| [Vision SDD (0001)](docs/design/0001-hextory-vision.md) | Meta-system design (**Approved**) |
| [Factory engine SDD (0002)](docs/design/0002-factory-engine.md) | Hexagonal multi-agent engine (**Approved**) |
| [Hextory Studio SDD (0003)](docs/design/0003-workflow-studio.md) | Managed workflow canvas — Twilio Studio–like (**Draft**, ideation only) |
| [Factory engine intent](docs/architecture/factory-engine-intent.md) | Historical intent; gate is DES-0002 **Approved** |
| [CONTRIBUTING](CONTRIBUTING.md) | Design-doc gate, tests, CI on-ramp |
| [SDD template](docs/design/TEMPLATE.md) | Start here for new workflows |

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Marcos Blazquez.

## Maturity pulse reports

Hourly assessments write design-doc-style reports under [`docs/maturity/reports/`](docs/maturity/reports/). Template: [`docs/maturity/REPORT_TEMPLATE.md`](docs/maturity/REPORT_TEMPLATE.md). Overall ≥ 90 pauses the pulse until a human restarts it. Every run reports back, including when scores are unchanged.
