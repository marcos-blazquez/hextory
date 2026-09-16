# Factory engine — architecture intent

| Field | Value |
|---|---|
| **Status** | **Superseded as gate by DES-0002 (Approved)** — retained as historical intent |
| **Created** | 2026-09-15 |
| **Authors** | Marcos Blazquez + New Bot |
| **Dedicated SDD** | [DES-0002 Draft](../design/0002-factory-engine.md) — **Draft** (not Approved); dual review pending |
| **Blocks implementation until** | [DES-0001](../design/0001-hextory-vision.md) is **Approved** *and* [DES-0002](../design/0002-factory-engine.md) is **Approved** |

This document captures the **base prompt intent** for the Hextory factory engine. It is **not** an SDD and **must not** be used as a design-doc gate green light. Prefer **DES-0002** for design decisions once that SDD is under review or Approved; this intent remains historical/input context.

---

## Intent summary

Build a **hexagonal AI Agent Factory** that runs production workflows without human line-by-line code review, while still requiring **human merge approval grounded in Approved SDDs**.

Planned stack (directional):

- Orchestration: **LangGraph**
- Schemas / validation: **Pydantic v2**
- Pure domain + use-cases: **`src/`** (no adapter I/O)
- Adapters for three targets (below)
- Departments: **assembly**, **quality**, **packaging**
- **Gateway** with interceptors
- State: **DigitalTraveler**
- **Quality FAIL → rework** loop back to assembly (or designated step)

---


## Open-ended workflows (nodes / edges)

The initial assembly → quality → packaging sketch is a **starter topology**, not the closed set of all workflows.

- Humans and agents may define **new nodes** (departments, validators, exporters) and **new edges** (including conditional and rework edges) via design docs + config/registry.
- Combinations are **unbounded in principle**; the engine must not hard-code a single permanent graph.
- Each concrete workflow still needs an **Approved SDD** before implementation/run in production posture.
- Code-review avoidance is **one** operating capability of this factory, alongside composable multi-agent workflows, multi-target deploy, and design-gated quality.

## Planned directory tree

```
hextory/
├── docs/                          # design, workflows, maturity, architecture
├── src/                           # PURE core only
│   ├── domain/                    # entities, DigitalTraveler, value objects
│   ├── ports/                     # interfaces (gatekeeper, run, persistence, LLM, …)
│   ├── departments/               # assembly, quality, packaging (pure orchestration hooks)
│   ├── graphs/                    # LangGraph definitions (I/O via ports)
│   └── policies/                  # gate rules, rework limits (pure)
├── adapters/
│   ├── local/                     # CLI, MemorySaver / in-memory checkpointing
│   ├── onprem/                    # Docker, FastAPI, Postgres
│   └── aws/                       # serverless (API Gateway/Lambda or equiv.), managed store
├── tests/
│   ├── unit/                      # core only — no network
│   ├── behavior/                  # BDD-style Given/When/Then (DES-0002-E)
│   └── adapters/                  # optional per-target smokes
├── config/                        # optional manifests (DES-0002)
├── pyproject.toml                 # (future)
└── README.md
```

Exact package names may change in the engine SDD; hexagonal **rules** should not. See DES-0002 for the Draft freeze.

---


## Testing intent (TDD + BDD-style)

- **TDD:** behavior is specified with failing tests before implementation for core/ports work.
- **BDD-style (not Cucumber):** readable behavior specs (Given/When/Then or equivalent) in ordinary test code — no Cucumber/Gherkin toolchain as a project requirement.
- **Enforcement:** at the **testing layer** (CI + conventions). **DES-0002-E** proposes `tests/unit/`, `tests/behavior/`, `tests/adapters/` — pending dual review of DES-0002.

## Hexagonal rules

1. **`src/` imports nothing from `adapters/`.** Dependencies point inward.
2. **Side effects only in adapters** (HTTP, DB, filesystem, cloud SDKs, real LLM clients behind ports).
3. **Pydantic models** define traveler/payload contracts at boundaries; core prefers domain types mapped at adapters.
4. **New deploy target = new adapter package**, not a fork of department logic.
5. **Gatekeeper is a port**: refuse runs/merges that lack Approved SDD linkage (policy in core, enforcement in adapters/CI).

---

## Three deploy targets

| Target | Entrypoint (intent) | Persistence / checkpoint | Notes |
|---|---|---|---|
| **Local** | CLI | MemorySaver / local files | Dev & agent loops — **first slice** per DES-0002-J |
| **On-prem** | FastAPI in Docker | Postgres | Customer VPC / self-host |
| **AWS serverless** | Managed HTTP + functions | Managed store / checkpoints | Elastic runs |

Parity goal: same Approved workflow + traveler semantics on all three; adapter-specific ops stay outside core.

---

## Gateway and interceptors

- **Gateway** accepts run requests (CLI or HTTP), attaches auth/context, loads SDD gate status, creates/resumes DigitalTraveler.
- **Interceptors** (intent): logging/trace injection, design-doc gate check, quota/timeout, idempotency keys.
- Failed gate → do not enter assembly; return structured denial citing missing/unapproved SDD.

---

## Departments and quality loop

```
[Visual placeholder]
Gateway → Assembly → Quality → Packaging → Shipped
                ↑         │ FAIL
                └── rework ←┘  (increment rework_count; escalate at max)
```

| Department | Intent |
|---|---|
| Assembly | Generate/transform artifacts per Approved SDD |
| Quality | Evaluate acceptance criteria; emit PASS/FAIL + defect report |
| Packaging | Produce shippable bundle + manifest; never package on FAIL |

**Constraint:** Shipped is unreachable while Quality is FAIL or design-doc gate is not satisfied.

---

## DigitalTraveler (intent pointer)

See Draft field freeze in [DES-0002](../design/0002-factory-engine.md) §3.1 (was sketch-only in DES-0001). Intent doc no longer freezes schema.

---

## Constraints (non-negotiable for later SDD)

1. **No implementation** from this intent doc alone.
2. **No human line-by-line code review requirement** in the operating model; **human main-line merge approval via design-doc readiness** remains required (DES-0001-B).
3. Prefer **deterministic, unit-tested core**; flaky cloud-only tests are insufficient for Quality.
4. Public MIT project trajectory; keep docs and gates contributor-legible.
5. LangGraph + Pydantic v2 are the **current** intent—engine SDD may refine with rationale (DES table). See DES-0002-B.

---

## Open work before coding

- [x] Approve DES-0001
- [x] Write dedicated factory-engine SDD (DES-0002) — **Drafted** 2026-09-15; **not Approved** yet
- [ ] Dual-review and **Approve** DES-0002
- [ ] Freeze DigitalTraveler schema + department interfaces (proposed in DES-0002 Draft; finalize on Approve)
- [ ] Define CI design-doc gate + human merge policy hooks
- [ ] Then scaffold `src/` + `adapters/local` only as first vertical slice

---

## Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-15 | Marcos Blazquez + New Bot | Initial intent capture; not implementation-approved |
| 2026-09-15 | Marcos Blazquez + Clark Bot | Point to DES-0002 Draft; check off “write SDD” as drafted (not Approved) |
| 2026-09-15 | Clark Bot | DES-0002 Approved; intent no longer the implementation gate |
