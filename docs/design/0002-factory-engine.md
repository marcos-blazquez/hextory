# DES-0002 — Hextory factory engine (hexagonal multi-agent orchestration)

| Field | Value |
|---|---|
| **Doc ID** | DES-0002 |
| **Title** | Hextory factory engine (hexagonal multi-agent orchestration) |
| **Status** | **Approved** |
| **Authors** | Marcos Blazquez + Clark Bot |
| **Reviewers (human)** | Marcos Blazquez (2026-09-15 — “looks good; start dual review”) |
| **Reviewers (agent)** | Clark Bot (2026-09-15 — checklist pass; see review record) |
| **Created** | 2026-09-15 |
| **Last updated** | 2026-09-16 (Approved body hygiene — remove residual Draft-era wording) |
| **Related REQs** | REQ-0001, REQ-0002, REQ-0003, REQ-0004, REQ-0010, REQ-0011, REQ-0012, REQ-0013, REQ-0014, REQ-0015, REQ-0016, REQ-0017 |
| **Supersedes** | none (consumes [factory-engine-intent.md](../architecture/factory-engine-intent.md) as input; intent is historical — **this Approved SDD** is the implementation gate) |
| **Parent vision** | [DES-0001](0001-hextory-vision.md) (**Approved**) |

---

## 1. Introduction / overview

### 1.1 Problem statement

DES-0001 established the dark-factory vision and design-doc gate. Before this SDD, the project lacked an **Approved** contract for the runtime that orchestrates multi-agent workflows—so agents could not scaffold `src/` without architecture drift, and DigitalTraveler / gatekeeper / rework stayed untestable sketches.

**This SDD (now Approved)** is that contract for the engine. First-slice implementation (`src/` + `adapters/local` + `tests/`) is authorized under §13; on-prem/AWS remain deferred (DES-0002-J).

### 1.2 Goals

- **G1 (REQ-0010):** Specify a hexagonal factory engine: pure `src/` core + ports; adapters for local, on-prem, and AWS with identical traveler/workflow semantics.
- **G2 (REQ-0011):** Support open-ended workflows via graph/registry—starter assembly→quality→packaging is not a closed catalog (DES-0001-C).
- **G3 (REQ-0012):** Freeze the DigitalTraveler schema (including append-only `routing_history`) for first-slice implementation and published-contract consumers.
- **G4 (REQ-0013):** Define RequestGateway, interceptors, and Gatekeeper refusal of runs lacking an Approved SDD id.
- **G5 (REQ-0014):** Specify Quality FAIL → rework with default max attempts **3**, then human escalation.
- **G6 (REQ-0015):** Decide the testing-layer home and TDD + BDD-style (Given/When/Then in ordinary tests, not Cucumber) conventions.
- **G7 (REQ-0016 / REQ-0017):** Bound the first post-Approval implementation slice to `src/` core + `adapters/local` (CLI + MemorySaver); on-prem/AWS later under this SDD or thin amendments.
- **G8:** Preserve DES-0001-B: code-review avoidance is **one** capability; human main-line merge = design-doc readiness, not PR walkthrough.

### 1.3 Success definition

- Dual review Approves or requests changes against this SDD without re-litigating DES-0001.
- Agents implement the local vertical slice against acceptance criteria and TEST IDs without inventing architecture.
- Gatekeeper, traveler schema, rework policy, and package layout are unambiguous enough for unit and behavior tests to fail first (TDD).
- Intent doc remains non-gating; this **Approved** SDD is the sole implementation gate for the engine.

### 1.4 Scope

**In scope:**

- Engine architecture, package layout, ports, starter departments, graph/registry model.
- DigitalTraveler field freeze (DES-0002-G); Gateway + interceptors; Gatekeeper policy.
- Quality rework defaults; failure modes; adapter designs (local detailed; on-prem/AWS sketched).
- Testing-layer home; TEST ID plan; acceptance and gate criteria (§13 green under **Approved**).
- Code-style expectations for walk-through-friendly core.

**Out of scope:** see Explicit non-goals (§8). On-prem/AWS production deployables and full CI automation remain deferred; **first-slice** local core+CLI+tests are authorized only while Status is **Approved** and §13 is green.

---

## 2. System architecture

### 2.1 Context

The factory engine sits under the Hextory dark-factory operating model (DES-0001). Humans and agents produce Approved workflow SDDs; the engine runs those workflows as graphs over DigitalTravelers.

```
[Visual placeholder: context diagram]
Human / Agent CLI or HTTP client
        │
        ▼
RequestGateway (+ interceptors: auth/context, gate check, idempotency, quota/timeout, logging)
        │
        ▼
Gatekeeper port ──refuse if SDD not Approved──► structured denial
        │ allow
        ▼
Core graph runtime (LangGraph via ports) — departments as nodes
        │
        ├── Assembly ──► Quality ──► Packaging ──► Shipped
        │                  │ FAIL
        │                  └── rework (≤ max) ──► Assembly (or designated node)
        │
ports ◄─┴─► adapters: local | on-prem | AWS
              (LLM, persistence/checkpoint, filesystem, HTTP)
```

**Who calls it:** local CLI operators, future FastAPI/on-prem clients, future AWS API Gateway/Lambda entrypoints.  
**What it calls:** LLM providers (behind a port), checkpoint/persistence stores, optional artifact stores—always through adapters.

### 2.2 Architectural style

**Hexagonal (ports & adapters)** — **DES-0002-A**.

| Rule | Enforcement |
|---|---|
| `src/` imports nothing from `adapters/` | Convention + future CI import-linter / custom check |
| Side effects only in adapters | Ports for LLM, persistence, clock, ID generation, filesystem |
| Pydantic v2 at boundaries | Traveler DTO / request schemas; map to domain types in core as needed |
| New deploy target = new adapter package | No fork of department logic |
| Gatekeeper is a port | Policy pure in `src/policies/`; adapters/CI enforce |

Orchestration stack (**DES-0002-B**, directional): **LangGraph** for graphs; **Pydantic v2** for schemas/validation. Alternatives (custom FSM, dataclasses-only) rejected for ecosystem fit and DES-0001 A3 continuity; may be revisited only via SDD amendment with rationale.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| RequestGateway | Accept run/resume requests; run interceptor chain; create/resume traveler | n/a |
| Interceptors | Logging/trace, design-doc gate, quota/timeout, idempotency | n/a |
| Gatekeeper | Refuse runs without Approved SDD id / status | n/a (policy) |
| Graph registry | Resolve workflow_id → node/edge definitions (unbounded combos) | n/a |
| assembly_manager | Produce/transform artifacts per Approved SDD | assembly |
| quality_manager | Evaluate acceptance criteria; PASS/FAIL + defect report | quality |
| packaging_manager | Emit shippable bundle + manifest; never on FAIL | packaging |
| Rework policy | Route FAIL → designated node; count attempts; escalate | quality → assembly |
| Checkpointer (optional at compile) | Persist graph state for resume | n/a (port) |
| Adapters (local / on-prem / aws) | Wire CLI/HTTP, MemorySaver/Postgres/managed store, LLM clients | n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0002-A** | Hexagonal: pure `src/` (domain, ports, departments, graphs, policies); adapters for local / on-prem / AWS | Monolith with env flags; clean architecture without explicit ports | Matches DES-0001; multi-target parity without forking departments |
| **DES-0002-B** | LangGraph + Pydantic v2 as directional stack | Custom FSM; dataclasses; alternate orchestrators | Aligns with intent + DES-0001 A3; schemas at boundaries; amendable with rationale |
| **DES-0002-C** | Open-ended graph/registry; starter assembly→quality→packaging is not a closed catalog | Hard-coded three-node graph only | Consumes DES-0001-C; unbounded node/edge combos via SDD + config/registry |
| **DES-0002-D** | Code-review avoidance is one capability; human merge = design-doc readiness | Require PR walkthrough; fully lights-out merge | Reinforces DES-0001-B / REQ-0004 |
| **DES-0002-E** | Testing layer home: `tests/` with `tests/unit/`, `tests/behavior/`, `tests/adapters/`; TDD + BDD-style Given/When/Then in ordinary tests (**not Cucumber**); enforcement via conventions + future CI | Cucumber/Gherkin; tests inside `src/`; only adapter smokes | Decides DES-0001 Q6 / DES-0001-D; keeps hexagonal purity (tests import `src/`; no adapter I/O into core). |
| **DES-0002-F** | Readable, walk-through-friendly code style in core (explicit names, shallow modules, prefer clarity over cleverness) | Ultra-dense / highly abstract style | Agents and humans must audit against SDD without heroic archaeology |
| **DES-0002-G** | DigitalTraveler schema freeze (§3.1 fields) including append-only `routing_history` | Keep sketch-only forever; over-normalize early | Enables TDD and adapter DTOs; frozen under this Approved SDD (additive fields via amendment) |
| **DES-0002-H** | Gateway + interceptors; Quality FAIL → rework; **max_rework default = 3** then escalate | Unlimited rework; fail-fast with no loop; default 1 or 5 | Predictable cost/latency; per-workflow override allowed with justification in that SDD |
| **DES-0002-I** | Gatekeeper refuses runs without Approved SDD id (and Approved status) | Soft warn; gate only at merge | Runtime + CI both enforce design-doc gate (REQ-0001) |
| **DES-0002-J** | First implementation slice after Approval: `src/` core + `adapters/local` only (CLI + MemorySaver); on-prem/AWS under same SDD or thin amendments | Implement all three targets at once | Smallest verifiable vertical slice; parity later without redesigning core |

---

## 3. Data design

### 3.1 Entities / state

#### DigitalTraveler (schema freeze — **DES-0002-G**)

Mutable state object that moves through factory nodes. Field set below is **frozen** under this Approved SDD; IDs and semantics stay stable (additive fields via amendment). Published contract id: `hextory.digital_traveler@0.1` — see [`docs/contracts/digital-traveler-0.1.md`](../contracts/digital-traveler-0.1.md).

| Field | Type (intent) | Required | Purpose |
|---|---|---|---|
| `traveler_id` | UUID / ULID string | yes | Stable ID for the unit of work |
| `workflow_id` | string | yes | Registry key for graph definition |
| `sdd_id` | string (`DES-NNNN`) | yes | Link to Approved SDD; gatekeeper input |
| `status` | enum string | yes | Lifecycle: e.g. `accepted`, `assembling`, `quality_check`, `rework`, `packaging`, `shipped`, `escalated`, `denied` |
| `payload` | object (JSON-compatible) | yes | Work inputs / intermediate structured data |
| `artifact_refs` | list of `{kind, uri, digest?}` | yes (may be empty) | References to generated artifacts |
| `quality_reports` | list of QualityReport | yes (may be empty) | Structured PASS/FAIL history |
| `rework_count` | non-negative int | yes | Attempts used; incremented on FAIL→rework |
| `max_rework` | positive int | yes | Default **3** unless workflow SDD overrides |
| `routing_history` | list of RoutingEvent | yes (append-only) | Every node visit / routing decision |
| `trace` | list of `{req_id?, des_id?, test_id?, note?}` | yes (may be empty) | Traceability progress |
| `audit` | list of AuditEvent | yes (may be empty) | Who/what transitioned state |
| `idempotency_key` | string \| null | no | Deduplicate run requests |
| `checkpoint_ref` | string \| null | no | Adapter-specific checkpoint handle |
| `last_defect` | DefectReport \| null | no | Latest structured defect for rework |
| `created_at` | ISO-8601 datetime | yes | Creation time (UTC stored; display in operator TZ) |
| `updated_at` | ISO-8601 datetime | yes | Last mutation time |

**RoutingEvent** (append-only; never rewrite prior entries):

| Field | Purpose |
|---|---|
| `seq` | Monotonic sequence within traveler |
| `at` | ISO-8601 timestamp |
| `node_id` | Graph node entered or decided |
| `decision` | e.g. `enter`, `pass`, `fail`, `rework`, `escalate`, `ship`, `deny` |
| `notes` | Short human/agent-readable reason |
| `actor` | `system` \| adapter id \| agent id |

**QualityReport:**

| Field | Purpose |
|---|---|
| `report_id` | Stable id |
| `at` | Timestamp |
| `result` | `PASS` \| `FAIL` |
| `criteria_results` | list of `{ac_id, passed, detail}` |
| `defect` | DefectReport if FAIL |

**DefectReport:** `{ code, summary, details, suggested_rework_node? }`

| Entity | Key fields | Lifecycle |
|---|---|---|
| DigitalTraveler | `traveler_id`, `sdd_id`, `workflow_id`, `status` | created at gateway → routed → shipped / escalated / denied |
| WorkflowDefinition | `workflow_id`, nodes[], edges[], `sdd_id` | registered after Approved SDD; immutable for a run version |
| RunRequest | `workflow_id`, `sdd_id`, `payload`, `idempotency_key?` | validated at gateway |

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
RunRequest
  → Gateway interceptors mutate/annotate context (no traveler yet or resume)
  → Gatekeeper(sdd_id) → deny OR allow
  → Create/resume DigitalTraveler (append routing_history: gateway/accepted)
  → Graph invoke(node=assembly_manager, …)
  → Each node: read traveler → pure transform / port calls via injected deps
             → append routing_history → update status/payload/reports
  → Quality PASS → packaging → shipped (artifact_refs + manifest)
  → Quality FAIL → rework_count++ → if < max_rework: back to rework node
                 → else: status=escalated, stop
  → Optional checkpointer persists compiled-graph state between steps
```

### 3.3 Persistence & retention

| Target | Traveler / checkpoint store | Retention (intent) | PII |
|---|---|---|---|
| Local | MemorySaver + optional local files under workspace | Session / explicit export; no cloud TTL | Avoid secrets in `payload`; redact in logs |
| On-prem | Postgres (traveler rows + checkpoint blob) | Per customer policy; default soft-delete after configurable TTL | Same; encryption at rest = ops concern |
| AWS | Managed store / checkpoint (exact resource names **open** — Q-AWS-1) | Lifecycle rules TBD in adapter amendment | Same |

Core never opens sockets or files; adapters own serialization (JSON via Pydantic models at the boundary).

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| Local CLI (`adapters/local`) | CLI | Local user / env credentials for LLM | `hextory run --sdd DES-NNNN --workflow …`; `hextory status --traveler …`; resume by id |
| On-prem HTTP (future) | FastAPI / HTTP JSON | Token/mTLS (adapter policy) | `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` |
| AWS HTTP (future) | API Gateway → Lambda (or equiv.) | IAM / JWT per amendment | Same semantic contract as on-prem; different binding |
| In-process (tests) | Python API | n/a | Gateway facade with fake ports for unit/behavior tests |

All inbound paths **must** supply `sdd_id` (and workflow identity). Missing or non-Approved → Gatekeeper denial (no assembly entry).

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| LLM port | Assembly / quality reasoning where SDD requires model calls | Retry per interceptor policy; then FAIL with defect or escalate |
| Checkpointer port | Persist/resume graph state | Run may continue in-memory locally; hard-fail if resume required and store down |
| Artifact store port | Read/write blobs | Surface as Quality FAIL or packaging error; no silent drop |
| Gate status reader | Resolve SDD Approved? | Deny closed (fail safe); never assume Approved on read error |
| Clock / ID ports | Deterministic tests | Injected fakes in `tests/unit` |

### 4.3 Events / messages

| Topic / event (logical) | Payload summary | Idempotency |
|---|---|---|
| `run.accepted` | traveler_id, sdd_id, workflow_id | `idempotency_key` on RunRequest |
| `run.denied` | sdd_id, reason | Same key may return cached denial |
| `node.completed` | traveler_id, node_id, decision | Derived from traveler seq |
| `quality.failed` | traveler_id, defect, rework_count | Append-only reports |
| `run.escalated` | traveler_id, reason | Terminal until human action |
| `run.shipped` | traveler_id, artifact_refs | Terminal success |

Exact broker (none locally; optional later) is adapter-specific. Core emits domain facts; adapters map to logs/metrics/queues.

---

## 5. Component design

### 5.1 Core (pure) logic

Lives under `src/` with **no** adapter I/O:

| Package | Contents |
|---|---|
| `src/domain/` | DigitalTraveler and value objects; status transitions; RoutingEvent helpers (append-only) |
| `src/ports/` | Protocols/ABCs: Gatekeeper, LLM, Checkpointer, ArtifactStore, SddStatusReader, Clock, IdGenerator |
| `src/departments/` | `assembly_manager`, `quality_manager`, `packaging_manager` (and future nodes)—pure functions/services taking traveler + ports |
| `src/graphs/` | Graph builders; starter topology factory; registry lookup interfaces (definitions may load from config via port) |
| `src/policies/` | Gate rules, max rework, “no ship on FAIL”, interceptor ordering as pure policy data |

**Readable style (DES-0002-F):** one concept per module where practical; explicit parameter names; avoid deep metaprogramming; comments explain *why* for policy edges.

### 5.2 Adapters

#### `adapters/local` (first slice — **DES-0002-J**)

| Piece | Design |
|---|---|
| CLI (`main.py` or `python -m …`) | Parse run/status/resume; build gateway with local interceptor stack; print traveler summary + routing_history tail |
| MemorySaver checkpointer | LangGraph in-memory / process-local checkpoint; optional file dump for debug |
| Fake or thin LLM client | Behind LLM port; real provider keys only via env—never in core |
| SddStatusReader | Read Approved status from docs metadata and/or `config/sdd_status` (Q-GATE-1 interim) |

#### `adapters/onprem` (later)

- FastAPI app exposing run/resume/status.
- Docker image; Postgres for traveler + checkpoints.
- Same gateway semantics; auth adapter-local.

#### `adapters/aws` (later)

- SAM (or equivalent) templates for HTTP + functions.
- Managed persistence/checkpoint (names TBD — Q-AWS-1).
- Same core graph; no department forks.

Adapter designs are **contracts** in this SDD—not full implementation code.

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Gatekeeper | If `sdd_id` missing OR status ≠ Approved → deny; do not enter assembly |
| Starter routing | assembly → quality → (PASS → packaging → shipped) \| (FAIL → rework) |
| Rework | On FAIL: append QualityReport + DefectReport; `rework_count += 1`; if `rework_count < max_rework` route to `suggested_rework_node` or default assembly; else `escalated` |
| Packaging | Invoked only after Quality PASS; never package on FAIL |
| Ship | Unreachable while Quality FAIL or gate unsatisfied (DES-0001-A) |
| Registry | Nodes/edges registered by `workflow_id`; unknown workflow → deny at gateway |
| Interceptor order (default) | logging/trace → idempotency → quota/timeout → design-doc gate → handoff to graph |

---

## 6. UI (if any)

**CLI UX only for first slice** (no graphical UI).

```
[Visual placeholder: CLI transcript]
$ hextory run --sdd DES-0002 --workflow starter_factory --payload payload.json
accepted traveler_id=trv_…
routing: gateway/accepted → assembly/enter → …
quality: FAIL (AC-03) rework_count=1/3
routing: quality/fail → assembly/rework
…
quality: PASS
packaging: ship manifest written
status: shipped

$ hextory status --traveler trv_…
status=shipped rework_count=1
routing_history: [ … last 5 events … ]
```

Graphical dashboards: **N/A** for this SDD (future product SDD).

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-01 | LangGraph remains suitable for open-ended registries | Rewrite graphs package | Hexagonal isolation; DES-0002-B amendable |
| A-02 | Pydantic v2 sufficient for traveler DTOs | Schema friction | Keep domain types thin; map at edges |
| A-03 | Approved SDD status is machine-readable enough for Gatekeeper | False allow/deny | Define reader contract; fail closed (Q-GATE-1) |
| A-04 | Default max_rework=3 fits most workflows | Cost or under-retry | Per-workflow override in that SDD |
| A-05 | Local MemorySaver enough for first-slice demos | Lost state on crash | Document; file checkpoint optional later |
| A-06 | Contributors follow tests/ layout | Drift | Conventions + future CI (DES-0002-E) |
| A-07 | Parent DES-0001 stays Approved | Vision churn | Engine SDD cites stable DES-0001 decisions |

---

## 8. Explicit non-goals

- **NG1:** Shipping on-prem/AWS adapters or production CI in the first slice (local `src/` + `adapters/local` only per DES-0002-J).
- **NG2:** Implementing on-prem or AWS adapters in the first slice.
- **NG3:** Adopting Cucumber/Gherkin or any BDD *toolchain* (BDD-*style* text in ordinary tests only).
- **NG4:** Requiring human line-by-line code review as a merge prerequisite (DES-0001-B / DES-0002-D).
- **NG5:** Allowing main-line merge or production run without Approved SDD citation.
- **NG6:** Hard-coding a permanent closed catalog of only assembly/quality/packaging.
- **NG7:** Choosing a single mandatory LLM vendor or locking exact AWS resource names in this SDD.
- **NG8:** Building a full web UI / operator console.
- **NG9:** Treating [factory-engine-intent.md](../architecture/factory-engine-intent.md) as an implementation gate.

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement only after gate criteria (§13) are green.

| ID | Criterion | Verification method |
|---|---|---|
| AC-01 | `src/` has no imports from `adapters/` | TEST-0010 (static/import check) |
| AC-02 | Gatekeeper denies run when `sdd_id` missing or not Approved; no assembly routing_history entry | TEST-0011, TEST-0012 |
| AC-03 | DigitalTraveler includes §3.1 fields; `routing_history` is append-only across node visits | TEST-0013 |
| AC-04 | Starter graph: assembly → quality → packaging on PASS | TEST-0014 |
| AC-05 | Quality FAIL routes to rework; increments `rework_count`; after 3 FAILs status=`escalated` (default) | TEST-0015, TEST-0016 |
| AC-06 | Packaging never runs on FAIL; Shipped unreachable while FAIL | TEST-0017 |
| AC-07 | Graph registry accepts an additional custom node/edge without editing department core (open-ended) | TEST-0018 |
| AC-08 | Local CLI can start a run with MemorySaver and print status / routing tail | TEST-0019 (adapter smoke) |
| AC-09 | Unit tests live under `tests/unit/`; behavior scenarios under `tests/behavior/`; no Cucumber dependency | TEST-0020 |
| AC-10 | Behavior tests use readable Given/When/Then (or equivalent) structure in ordinary test modules | TEST-0021 |
| AC-11 | Optional checkpointer can be attached at compile without core knowing MemorySaver types | TEST-0022 |
| AC-12 | Human merge policy docs/comments cite design-doc readiness, not code walkthrough | TEST-0023 (doc/conformance) |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Missing / unapproved SDD | Gatekeeper | Deny; `status=denied`; audit reason | No assembly; human fixes SDD status |
| Unknown workflow_id | Registry lookup | Deny at gateway | Register workflow via Approved SDD + config |
| Assembly artifact error | Exception / empty required outputs | Quality-bound FAIL or escalate if unrecoverable | Treat as FAIL with defect → rework if countable |
| Quality FAIL vs AC | quality_manager | Append report + defect; route rework | Back to assembly (or suggested node); max **3** |
| Exceeded max_rework | Policy after FAIL | `status=escalated`; stop graph | Human designer/reviewer intervenes |
| LLM / port timeout | Interceptor / port error | Retry per policy then FAIL or escalate | Counted as rework only if Quality FAIL emitted |
| Checkpoint write failure | Checkpointer port | Fail resume path; surface error | Operator retries; local may continue ephemeral |
| Packaging after FAIL (bug) | Invariant check | Hard stop; never ship | Fix as engine defect; regression TEST-0017 |

**Rework policy defaults (override only with justification in a workflow SDD):**

- Quality department **FAIL** returns the DigitalTraveler to the owning assembly step (or `suggested_rework_node`) with a structured defect report.
- Max rework attempts before human escalation: **3**.
- Partial ships are **forbidden**.

---

## 11. Human + agent review checklist

Reviewers must check each item. Architecture-critical items require **human** sign-off.

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☑ | ☑ | Yes |
| 2 | Architecture fits hexagonal / factory rules | ☑ | ☑ | Yes |
| 3 | Interfaces and failure modes are specified | ☑ | ☑ | Yes |
| 4 | Acceptance criteria are testable | ☑ | ☑ | Yes |
| 5 | Traceability IDs are complete and unique | ☑ | ☑ | Yes |
| 6 | Gate criteria are unambiguous | ☑ | ☑ | Yes |
| 7 | Security / privacy / compliance touched? | ☑ | ☑ | Yes (PII/secrets guidance in §3.3; no new compliance regime) |
| 8 | Glossary terms used consistently | ☑ | ☑ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☑ | ☑ | No |
| 10 | No implementation leakage that bypasses this SDD | ☑ | ☑ | Yes |
| 11 | Testing-layer home (DES-0002-E) acceptable | ☑ | ☑ | Yes |
| 12 | DigitalTraveler fields (DES-0002-G) acceptable | ☑ | ☑ | Yes |
| 13 | First-slice bound to local adapters (DES-0002-J) acceptable | ☑ | ☑ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | Marcos Blazquez | 2026-09-15 | **Approve** |
| Agent reviewer | Clark Bot | 2026-09-15 | **Approve** |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| REQ-0001 | Design-doc gate; human merge via doc readiness | DES-0001-A/B, DES-0002-D, DES-0002-I | TEST-0011, TEST-0012, TEST-0023 | |
| REQ-0002 | Roles + dual review operating model | DES-0001, DES-0002 (process) | TEST-0023 | |
| REQ-0003 | Hexagonal multi-target factory intent | DES-0002-A, DES-0002-J | TEST-0010, TEST-0019 | |
| REQ-0004 | Open graphs + TDD/BDD-style + code-review avoidance as one capability | DES-0001-C/D, DES-0002-C/D/E | TEST-0018, TEST-0020, TEST-0021 | |
| REQ-0010 | Hexagonal engine core + ports | DES-0002-A, DES-0002-F | TEST-0010 | |
| REQ-0011 | Open-ended graph/registry | DES-0002-C | TEST-0018 | |
| REQ-0012 | DigitalTraveler + routing_history | DES-0002-G | TEST-0013 | |
| REQ-0013 | Gateway + interceptors + gatekeeper | DES-0002-H, DES-0002-I | TEST-0011, TEST-0012 | |
| REQ-0014 | Quality FAIL rework; max 3 | DES-0002-H | TEST-0015, TEST-0016, TEST-0017 | |
| REQ-0015 | Testing layer + TDD/BDD-style | DES-0002-E | TEST-0020, TEST-0021 | |
| REQ-0016 | Multi-target adapter design | DES-0002-A, DES-0002-J | TEST-0019 (local); on-prem/AWS later | |
| REQ-0017 | First slice: src + adapters/local (CLI + MemorySaver) | DES-0002-J | TEST-0019, TEST-0022 | |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

All of the following must be true:

- [x] Status is **Approved** (both human and agent reviews recorded).
- [x] All **Critical** checklist items signed off by a human.
- [x] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [x] Non-goals and failure/rework policy are non-empty and specific.
- [x] Acceptance criteria are binary/testable (no vague “should be good”).
- [x] No open blocking questions in §15 (or each has an approved interim decision) — Q-GATE-1 interim below.
- [x] Maturity / process owners acknowledge this SDD (Marcos dual-review ask + Clark Bot pulse ownership).

**Only when every box is checked may agents generate implementation for this workflow.**

**Post-approval note:** Gate criteria are green. Implementation may proceed for the **first slice only** (`src/` + `adapters/local` per DES-0002-J), under TDD/BDD-style at `tests/` (DES-0002-E). On-prem/AWS still deferred.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **Factory engine** | The hexagonal runtime (core + adapters) that executes Approved workflow graphs over DigitalTravelers |
| **RequestGateway** | Inbound façade that runs interceptors and starts/resumes runs |
| **Interceptor** | Composable pre-graph concern (logging, gate, idempotency, quota/timeout) |
| **Gatekeeper** | Port/policy that refuses runs without Approved SDD id/status |
| **Graph registry** | Lookup from `workflow_id` to node/edge definitions |
| **RoutingEvent** | Append-only record of node visits and routing decisions |
| **MemorySaver** | Local in-process LangGraph checkpointer used in first slice |
| **Escalated** | Terminal status after max rework; requires human intervention |
| **Testing layer** | `tests/` tree enforcing TDD + BDD-style conventions (DES-0002-E) |
| **Starter topology** | Default assembly→quality→packaging graph; not a closed catalog |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| Q-LLM-1 | Exact LLM port signature and default provider for local slice? | Marcos + engine implementer | Before first LLM-backed assembly impl | Soft — fakes suffice for TEST-0014–0017 |
| Q-AWS-1 | Exact AWS resource names (API GW, Lambda, store, checkpoint)? | Marcos | Before `adapters/aws` work | Soft — thin amendment later |
| Q-ONP-1 | On-prem auth scheme (mTLS vs JWT vs both)? | Marcos | Before `adapters/onprem` | Soft |
| Q-GATE-1 | How does SddStatusReader resolve Approved locally (frontmatter parse vs manifest)? | Dual review | Before TEST-0011 green in CI | **Interim Approved 2026-09-15:** fail closed on read/parse error. Local reader MAY use (a) SDD markdown Status field / frontmatter, and/or (b) `config/sdd_status` manifest; both must agree when both present. Exact file format choosable at first-slice impl without new SDD if semantics hold. |
| Q-REG-1 | Concrete registry serialization (YAML/JSON/Python module)? | Dual review | Before multi-workflow demos | Soft — interface frozen; format amendable |
| Q-ID-1 | UUID vs ULID for `traveler_id`? | Dual review | Before Approved | Soft — string opaque to core |
| Q-CHK-1 | File-backed local checkpoint in first slice or MemorySaver only? | Marcos | First-slice impl | Soft — MemorySaver minimum (DES-0002-J) |

**Decided in this SDD (not open):** testing-layer home (**DES-0002-E**); traveler core fields (**DES-0002-G**); max_rework default **3** (**DES-0002-H**); first slice local-only (**DES-0002-J**).

None of Q-* above blocked Approval; Q-GATE-1 interim is recorded; AC-02 is implementable in CI.

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-15 | Marcos Blazquez + Clark Bot | Initial Draft from TEMPLATE + factory-engine-intent + DES-0001; decisions DES-0002-A…J |
| 2026-09-15 | Marcos Blazquez + Clark Bot | Dual review → **Approved**; Q-GATE-1 interim; first-slice implementation now gated-green |
| 2026-09-16 | Cloud Agent | Hygiene scrub: remove residual Draft-era / “may change in review” wording from Approved body; Status unchanged; link published DigitalTraveler 0.1 contract |

## Dual-review record

### Human (Marcos Blazquez) — 2026-09-15

- Verdict: **Approve** (“DES-0002 looks good; start dual review”).
- Accepts DES-0002-A…J including testing-layer home `tests/{unit,behavior,adapters}` and local-first slice.

### Agent (Clark Bot) — 2026-09-15

| Check | Result |
|---|---|
| Aligns with Approved DES-0001 (C/D/B merge gate) | Pass |
| Hexagonal rules + open-ended registry (not closed catalog) | Pass |
| Traveler schema + append-only routing_history testable | Pass |
| AC + TEST IDs binary and mapped | Pass |
| DES-0002-E not Cucumber; testing layer explicit | Pass |
| Intent doc remains non-gating; this SDD is the gate | Pass |
| Scope does not smuggle on-prem/AWS into first slice | Pass |
| Blocking open Qs | None; Q-GATE-1 interim recorded |

**Agent verdict:** **Approve**.

**Joint result:** Status → **Approved**. Implementation allowed for **DES-0002-J first slice only** (`src/` + `adapters/local` + `tests/`), TDD-first.

---

## Package layout (first-slice)

```
hextory/
├── docs/                          # design, workflows, maturity, architecture, contracts
├── src/                           # PURE core only
│   ├── domain/                    # entities, DigitalTraveler, value objects
│   ├── ports/                     # Gatekeeper, LLM, Checkpointer, …
│   ├── departments/               # assembly, quality, packaging (+ future nodes)
│   ├── graphs/                    # LangGraph definitions + registry hooks
│   └── policies/                  # gate rules, rework limits
├── adapters/
│   ├── local/                     # CLI + MemorySaver (first slice)
│   ├── onprem/                    # FastAPI, Docker, Postgres (later)
│   └── aws/                       # SAM/serverless (later)
├── tests/
│   ├── unit/                      # core only — no network / no adapter I/O
│   ├── behavior/                  # BDD-style Given/When/Then scenarios
│   └── adapters/                  # optional per-target smokes
├── config/                        # optional workflow manifests / registry files
├── pyproject.toml
└── README.md
```

---

## Testing approach

| Item | Guidance |
|---|---|
| **TDD** | Failing test before production code for core behavior |
| **BDD-style** | Readable Given/When/Then (or equivalent) in normal test modules — **not Cucumber** unless a future SDD explicitly adopts it |
| **Testing layer** | **`tests/`** — DES-0002-E: `tests/unit/` (core, no I/O), `tests/behavior/` (scenario specs), `tests/adapters/` (optional smokes). Enforcement: conventions now; CI import-linter + path checks later. |
| **Traceability** | Link TEST-* IDs to REQ-* / DES-* |

| TEST ID | Intent | Layer | Maps to |
|---|---|---|---|
| TEST-0010 | No `src`→`adapters` imports | unit / static | AC-01, REQ-0010 |
| TEST-0011 | Gatekeeper denies missing sdd_id | unit / behavior | AC-02, REQ-0013 |
| TEST-0012 | Gatekeeper denies non-Approved sdd | unit / behavior | AC-02, REQ-0001 |
| TEST-0013 | Traveler fields + append-only routing_history | unit | AC-03, REQ-0012 |
| TEST-0014 | Starter PASS path to packaging | behavior | AC-04 |
| TEST-0015 | FAIL increments rework and re-enters assembly | behavior | AC-05, REQ-0014 |
| TEST-0016 | Fourth FAIL (default max 3) → escalated | behavior | AC-05, REQ-0014 |
| TEST-0017 | No packaging / ship on FAIL | unit / behavior | AC-06 |
| TEST-0018 | Custom node/edge via registry | behavior | AC-07, REQ-0011 |
| TEST-0019 | Local CLI + MemorySaver smoke | adapters | AC-08, REQ-0017 |
| TEST-0020 | tests/ layout + no Cucumber dep | unit / static | AC-09, REQ-0015 |
| TEST-0021 | Behavior modules use Given/When/Then structure | behavior | AC-10, REQ-0015 |
| TEST-0022 | Checkpointer injectable at compile via port | unit | AC-11, REQ-0017 |
| TEST-0023 | Merge/gate docs cite design-doc readiness | conformance | AC-12, DES-0002-D |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders above; replace with real diagrams when available.
- **Consistency** — same names for Gateway, DigitalTraveler, departments across SDDs.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live under `docs/design/`; linked from README / maturity focus.
- **Collaboration** — dual review mandatory; record dissent in open questions or changes-requested notes.
- **Future growth** — new adapters/departments without rewriting the core contract.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.
