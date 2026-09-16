# DES-0004 — On-prem adapter (`adapters/onprem`)

| Field | Value |
|---|---|
| **Doc ID** | DES-0004 |
| **Title** | On-prem adapter (FastAPI + Postgres + Docker) |
| **Status** | **Draft** |
| **Authors** | Marcos Blazquez (on-prem-first direction) + Clark Bot |
| **Reviewers (human)** | Marcos Blazquez (pending) |
| **Reviewers (agent)** | Clark Bot (pending) |
| **Created** | 2026-09-16 |
| **Last updated** | 2026-09-16 |
| **Related REQs** | REQ-0010, REQ-0016 (from DES-0002); also REQ-0003, REQ-0013, REQ-0015 |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**) |
| **Implementation** | **Not authorized** while Status is Draft — scaffold only after dual review Approves this SDD |

---

## 0. Document posture

This SDD drafts the **second deploy target** for the factory engine: an on-prem HTTP adapter under `adapters/onprem`, as sketched in DES-0002 §5.2. Marcos directed **on-prem first** for multi-target readiness; AWS remains deferred.

**Hard rules (must survive into any future build):**

1. Same Gatekeeper / DigitalTraveler / GraphRunner ports as the local CLI — **no fork of core**.
2. `src/` must not import FastAPI, Postgres drivers, or any `adapters/` package (DES-0002-A / TEST-0010).
3. HTTP run/resume/status semantics match the local CLI traveler contract (parity tests under `tests/adapters/`).
4. Auth is **adapter-local** — core stays agnostic of JWT/mTLS.
5. Public kernel stays product-agnostic: never name private sibling products or out-of-tree app brands in this SDD or adapter code.
6. DES-0003 (Studio UI) remains Draft ideation and is **out of scope** here.

---

## 1. Introduction / overview

### 1.1 Problem statement

Aspect **9** (multi-target deploy readiness) is capped while only `adapters/local` exists. Operators need a second deploy path beyond the local CLI — HTTP + durable persistence + containerized ops — **without** taking on AWS yet. DES-0002 already sketched `adapters/onprem` (FastAPI, Docker, Postgres) but deferred it under DES-0002-J. This SDD is the design gate for that slice.

### 1.2 Goals

- **G1 (REQ-0010 / REQ-0016):** Specify `adapters/onprem` so the same pure `src/` core runs under an on-prem HTTP binding with identical traveler/workflow semantics to `adapters/local`.
- **G2:** HTTP semantic parity with the local CLI: `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` (plus Gatekeeper denial behavior for missing / non-Approved `sdd_id`).
- **G3:** Postgres-backed checkpointer (and traveler persistence) suitable for process restart and resume.
- **G4:** Docker Compose (or equivalent) for local/on-prem operator loops — API + Postgres together.
- **G5 (REQ-0015):** TDD + BDD-style (Given/When/Then in ordinary pytest, not Cucumber) tests under `tests/adapters/` proving parity vs local CLI traveler outcomes.
- **G6:** Default auth for the first on-prem slice: **JWT bearer**; leave mTLS as a later option (see Q-ONP-1).

### 1.3 Success definition

- Dual review Approves (or requests changes on) this Draft without re-litigating DES-0002 core ports.
- After Approval, agents can scaffold `adapters/onprem/` against §9 acceptance criteria and TEST IDs without inventing architecture.
- Parity tests demonstrate that a run accepted/denied/shipped/escalated via HTTP matches the local CLI traveler semantics for the same inputs.
- Aspect-9 evidence path exists on paper (adapter package + compose + parity tests) once implemented; this Draft alone does not claim multi-target readiness.

### 1.4 Scope

**In scope (this Draft):**

- On-prem adapter architecture, HTTP contract, Postgres persistence role, Docker Compose ops shape.
- Auth default proposal (JWT bearer) and open questions for Marcos confirmation.
- Design decisions DES-0004-A…; acceptance criteria; gate criteria; TEST ID plan.
- Traceability to REQ-0010 / REQ-0016 (and related gateway/testing REQs).

**Out of scope:** see Explicit non-goals (§8). No FastAPI/Postgres/Docker implementation lands while Status is **Draft**.

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
HTTP client (curl / ops tool / future Studio profile)
        │  Authorization: Bearer <JWT>
        ▼
adapters/onprem FastAPI  ──► RequestGateway (src/) + interceptors
        │                           │
        │                           ├── Gatekeeper / SddStatusReader
        │                           ├── GraphRunner (pure or LangGraph via port)
        │                           └── departments (unchanged)
        │
        ├── Postgres checkpointer / traveler store
        └── Docker Compose (api + db)
```

**Who calls it:** on-prem operators and HTTP clients.  
**What it calls:** the same `src/` gateway and ports as `adapters/local`; Postgres for durable state.

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). This SDD owns the **on-prem adapter boundary only**. Core packages (`domain`, `ports`, `departments`, `graphs`, `policies`, `gateway`) are not forked.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| FastAPI app (`adapters/onprem`) | HTTP bind for run / status / resume; JWT validation; map JSON ↔ gateway DTOs | n/a |
| RequestGateway (core) | Interceptors + start/resume runs | n/a |
| Gatekeeper + SddStatusReader | Refuse non-Approved `sdd_id` | n/a |
| Postgres checkpointer adapter | Persist/resume graph + traveler state | n/a |
| Docker Compose stack | Local/on-prem ops: API service + Postgres | n/a |
| Parity tests (`tests/adapters/`) | HTTP vs local CLI traveler semantics | n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0004-A** | First multi-target slice after local is **on-prem** (`adapters/onprem`); AWS deferred | AWS first; both at once | Marcos on-prem-first direction; smaller second-target surface |
| **DES-0004-B** | Default auth = **JWT bearer** for first on-prem slice; mTLS optional later | mTLS-only; JWT+mTLS mandatory day one; no auth | Unblocks HTTP ops; matches DES-0002 Q-ONP-1 soft open; Marcos to confirm (Q-ONP-1) |
| **DES-0004-C** | Postgres for traveler + checkpoint persistence | Files only; Redis; SQLite | Matches DES-0002 on-prem sketch; durable resume across restarts |
| **DES-0004-D** | Reuse core `RequestGateway` + interceptor stack; adapter only wires ports | Separate on-prem gateway; fork Gatekeeper | Preserves REQ-0010 / REQ-0013; no second engine |
| **DES-0004-E** | HTTP routes: `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` with same semantic contract as local CLI | Custom verb set; gRPC-first | Aligns with DES-0002 §4.1 sketch |
| **DES-0004-F** | Ship Docker Compose for api + Postgres as the operator path | K8s-only; bare metal scripts only | Lowest friction for local/on-prem validation |
| **DES-0004-G** | Parity proven by TDD/BDD-style tests under `tests/adapters/` | Manual-only smoke; Cucumber | DES-0002-E; REQ-0015 |

---

## 3. Data design

### 3.1 Entities / state

Core DigitalTraveler schema is **unchanged** (DES-0002-G / published `hextory.digital_traveler@0.1`). This adapter persists and returns the same traveler fields.

| Entity | Key fields | Lifecycle |
|---|---|---|
| DigitalTraveler | `traveler_id`, `sdd_id`, `workflow_id`, status, `routing_history`, `rework_count`, … | Created on accepted run; updated through graph; terminal shipped / escalated / denied |
| Checkpoint record | `traveler_id`, checkpoint blob / LangGraph-compatible state, updated_at | Written on node boundaries; required for resume |
| Run request (HTTP) | `sdd_id`, `workflow_id`, payload, optional `idempotency_key` | Mapped to core RunRequest |
| Auth principal (adapter-local) | JWT subject / claims used only for interceptor context | Not stored in traveler core schema |

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
Client JWT → FastAPI → (optional auth interceptor context)
  → RequestGateway → Gatekeeper
      → deny → HTTP 4xx structured denial (no assembly)
      → allow → GraphRunner + Postgres checkpointer
          → traveler status / routing_history persisted
          → HTTP 200 JSON traveler summary
```

### 3.3 Persistence & retention

- **Store:** Postgres (version TBD — Q-ONP-2).
- **What:** traveler snapshots, checkpoints, idempotency keys (adapter concern; same semantics as local File/Memory stores).
- **Retention:** operator-controlled; default “retain until deleted” for first slice (no automatic TTL unless a later amendment).
- **PII:** treat payload as potentially sensitive; no secrets in traveler fields by convention (DES-0002); DB credentials only via env / Compose secrets.

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| `POST /runs` | HTTP JSON | JWT bearer (proposed) | Start run; body includes `sdd_id`, `workflow_id`, payload; optional idempotency key |
| `GET /runs/{id}` | HTTP JSON | JWT bearer (proposed) | Status / traveler summary by `traveler_id` |
| `POST /runs/{id}/resume` | HTTP JSON | JWT bearer (proposed) | Resume from Postgres checkpoint |
| Health (optional) | HTTP | none or JWT | Liveness for Compose/`/health` — non-workflow |

All workflow paths **must** supply `sdd_id` (and workflow identity on create). Missing or non-Approved → Gatekeeper denial (no assembly entry), same as local CLI.

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| Core RequestGateway | Run orchestration | Propagate structured denial / traveler errors as HTTP responses |
| Postgres | Checkpoints + traveler persistence | Fail run/resume with actionable error if store down when durability required |
| SddStatusReader | Resolve Approved? | Fail closed (deny) on read/parse error (Q-GATE-1) |
| LLM port (optional) | Same as local when enabled | Retry/FAIL per core interceptor policy |

### 4.3 Events / messages

Same logical domain facts as DES-0002 §4.3 (`run.accepted`, `run.denied`, `quality.failed`, `run.shipped`, …). First on-prem slice may map these to structured logs only (no required message broker).

---

## 5. Component design

### 5.1 Core (pure) logic

**No new core packages required for the happy path.** On-prem reuses:

- `RequestGateway` + interceptors
- Gatekeeper / policies
- DigitalTraveler + GraphRunner ports
- Starter (and registered) workflows

Any new port method needed for Postgres binding must be justified in an amendment or this SDD’s revision before Approval — prefer implementing the existing Checkpointer / ArtifactStore ports in the adapter.

### 5.2 Adapters

#### `adapters/onprem` (this SDD — post-Approval)

| Piece | Design |
|---|---|
| FastAPI app | Routes for run / status / resume; dependency-inject gateway with on-prem ports |
| JWT auth middleware | Validate bearer token; attach principal to request context (adapter-local) |
| Postgres checkpointer | Implement Checkpointer port against Postgres |
| Traveler store | Persist/load traveler documents for status/resume |
| SddStatusReader wiring | Reuse or share local reader semantics (manifest + markdown Status) |
| Docker Compose | `api` + `postgres` services; env for DSN and JWT secret/issuer |
| Entrypoint | `python -m adapters.onprem…` or container CMD — exact module name at impl |

#### Explicitly not in this adapter

- AWS bindings (`adapters/aws`)
- Studio / React / `adapters/web` (DES-0003)
- Core schema changes

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Gatekeeper | Unchanged from DES-0002 — non-Approved → deny |
| Traveler semantics | Identical outcomes to local CLI for same workflow inputs / force-quality fixtures |
| Auth | Reject missing/invalid JWT with 401; do not confuse with Gatekeeper 4xx denial |
| Idempotency | Honor `idempotency_key` when provided (same semantics as local) |
| Rework / escalate | Core policy only (max 3 default) |

---

## 6. UI (if any)

**N/A — no UI.** This workflow is HTTP API / ops (Compose) only. CLI remains `adapters/local`. Studio remains DES-0003 Draft ideation.

```
[Visual placeholder: curl transcript]
$ curl -s -X POST https://onprem.example/runs \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sdd_id":"DES-0002","workflow_id":"starter_factory","payload":{}}'
{"traveler_id":"trv_…","status":"shipped", …}

$ curl -s https://onprem.example/runs/trv_… \
    -H "Authorization: Bearer $TOKEN"
{"traveler_id":"trv_…","status":"shipped","routing_history":[…]}
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-01 | DES-0002 remains Approved and local slice stays the semantic reference | Parity undefined | Freeze traveler contract `@0.1`; parity tests |
| A-02 | Marcos confirms JWT for first slice (Q-ONP-1) | Rework auth middleware | Keep auth adapter-local; mTLS as additive option |
| A-03 | Postgres is acceptable on-prem dependency | Ops friction | Document Compose; version pin in Q-ONP-2 |
| A-04 | TLS termination can be deferred to reverse proxy (Q-ONP-3) | App-level TLS complexity | Default: terminate at proxy; app speaks HTTP inside Compose network |
| A-05 | No core schema change needed for on-prem persistence | Forced traveler migration | Adapter maps existing fields only |

---

## 8. Explicit non-goals

- **NG1:** AWS adapter / SAM / managed cloud resources (`adapters/aws`).
- **NG2:** Studio UI, React, xyflow, or `adapters/web` (DES-0003 stays Draft ideation).
- **NG3:** Changing DigitalTraveler core schema or published `@0.1` contract.
- **NG4:** Forking Gatekeeper, departments, or RequestGateway into an on-prem-only engine.
- **NG5:** Implementing FastAPI/Postgres/Compose code while this SDD is **Draft** (docs-only until Approved).
- **NG6:** Mandating mTLS on day one (optional later; see Q-ONP-1).
- **NG7:** Message bus / multi-region HA as first-slice requirements.

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement **only after** gate criteria (§13) are green (Status **Approved**).

| ID | Criterion | Verification method |
|---|---|---|
| AC-01 | `adapters/onprem` exposes `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` | TEST-ONP-01 |
| AC-02 | Non-Approved / missing `sdd_id` → Gatekeeper denial (no assembly); HTTP maps structured denial | TEST-ONP-02 |
| AC-03 | Approved starter workflow run reaches same terminal statuses as local CLI for equivalent fixtures | TEST-ONP-03 (parity) |
| AC-04 | Postgres checkpointer supports process restart + resume | TEST-ONP-04 |
| AC-05 | Docker Compose brings up API + Postgres; documented smoke path works | TEST-ONP-05 / manual smoke |
| AC-06 | JWT bearer required on workflow routes; invalid/missing → 401 | TEST-ONP-06 |
| AC-07 | `src/` has zero FastAPI/Postgres/`adapters` imports | TEST-0010 + TEST-ONP-07 |
| AC-08 | Adapter tests live under `tests/adapters/` with BDD-style readability | TEST-ONP-03 docstrings / layout |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Invalid / missing JWT | Auth middleware | HTTP 401; no gateway call | Client refreshes token |
| Gatekeeper deny | Core policy | HTTP 4xx structured denial | Fix SDD status / cite Approved id |
| Postgres unavailable | Connection/health errors | Fail run/resume; do not pretend MemorySaver success in on-prem mode | Restore DB; retry |
| Quality FAIL | Core quality | Rework per DES-0002-H (max 3) then escalate | Same as local |
| Checkpoint corrupt / missing on resume | Checkpointer load | Structured error; no silent restart | Operator investigates store |

**Rework policy defaults:** inherit DES-0002-H (max rework **3**, then human escalation). Partial ships forbidden.

---

## 11. Human + agent review checklist

Reviewers must check each item. Architecture-critical items require **human** sign-off.

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☐ | ☐ | Yes |
| 2 | Architecture fits hexagonal / factory rules (no core fork) | ☐ | ☐ | Yes |
| 3 | Interfaces and failure modes are specified | ☐ | ☐ | Yes |
| 4 | Acceptance criteria are testable | ☐ | ☐ | Yes |
| 5 | Traceability IDs are complete and unique | ☐ | ☐ | Yes |
| 6 | Gate criteria are unambiguous | ☐ | ☐ | Yes |
| 7 | Security / privacy / compliance touched? (JWT, TLS, DB secrets) | ☐ | ☐ | Yes |
| 8 | Glossary terms used consistently | ☐ | ☐ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☐ | ☐ | No |
| 10 | No implementation leakage that bypasses this SDD | ☐ | ☐ | Yes |
| 11 | Q-ONP-1 interim (JWT default) acceptable to Marcos | ☐ | ☐ | Yes |
| 12 | AWS and Studio explicitly non-goals | ☐ | ☐ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | Marcos Blazquez | | Approve / Changes requested |
| Agent reviewer | Clark Bot | | Approve / Changes requested |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| REQ-0010 | Hexagonal engine core + ports | DES-0002-A, **DES-0004-D** | TEST-0010, TEST-ONP-07 | On-prem binds ports only |
| REQ-0016 | Multi-target adapter design | DES-0002-A/J, **DES-0004-A…G** | TEST-ONP-01…06 | Second target after local |
| REQ-0003 | Hexagonal multi-target factory intent | DES-0004-A | TEST-ONP-03 | Aspect-9 path |
| REQ-0013 | Gateway + interceptors + gatekeeper | DES-0004-D | TEST-ONP-02 | Reuse gateway |
| REQ-0015 | Testing layer + TDD/BDD-style | DES-0004-G | TEST-ONP-03 | `tests/adapters/` |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

All of the following must be true:

- [ ] Status is **Approved** (both human and agent reviews recorded).
- [ ] All **Critical** checklist items signed off by a human.
- [ ] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [ ] Non-goals and failure/rework policy are non-empty and specific.
- [ ] Acceptance criteria are binary/testable (no vague “should be good”).
- [ ] No open **blocking** questions in §15 (or each has an approved interim decision) — Q-ONP-1 needs Marcos confirmation or recorded interim.
- [ ] Maturity / process owners acknowledge this SDD in dual review (Marcos + Clark).

**Only when every box is checked may agents generate implementation for this workflow.**

**Draft note:** While Status is **Draft**, agents must **not** scaffold FastAPI, Postgres checkpointers, or Compose files as product implementation. Docs/index updates for this Draft are allowed.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **On-prem adapter** | `adapters/onprem` HTTP + Postgres + Docker binding of the factory engine |
| **Parity** | Same traveler terminal status / gate denial semantics as `adapters/local` for equivalent inputs |
| **JWT bearer** | `Authorization: Bearer <token>` auth for first on-prem slice |
| **Postgres checkpointer** | Checkpointer port implementation backed by PostgreSQL |
| **Compose stack** | Docker Compose services for API + database |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) and [0002-factory-engine.md](0002-factory-engine.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-ONP-1** | Confirm auth: this Draft proposes **JWT bearer** for the first on-prem slice; mTLS later optional. Confirm or override (mTLS / both)? | Marcos | Before Approval | **Proposed interim:** JWT bearer default — **awaiting Marcos confirmation** |
| **Q-ONP-2** | Postgres major version pin for Compose (e.g. 16 vs 15)? | Marcos + implementer | Before first Compose merge | Open |
| **Q-ONP-3** | TLS termination: reverse proxy vs app-level TLS? | Marcos | Before production-hardening slice | **Proposed interim:** reverse proxy terminates TLS; app HTTP on internal network — confirm |
| Q-ONP-4 | Exact JWT issuer/audience/secret wiring (env names, rotation)? | Implementer after Approval | During first impl slice | Soft — adapter-local |
| Q-ONP-5 | OpenAPI publish path (repo vs generated artifact)? | Dual review | Soft | Soft |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-16 | Marcos Blazquez (direction) + Clark Bot | Initial Draft: on-prem-first adapter SDD; JWT proposal; parity + Compose goals; no implementation |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same names as DES-0002 for gateway, traveler, gatekeeper.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions or changes-requested notes.
- **Future growth** — AWS remains a later adapter; do not smuggle cloud into this SDD.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Failing test before production code for HTTP parity and gate denial |
| BDD-style | Readable Given/When/Then in ordinary pytest modules — **not Cucumber** |
| Testing layer | `tests/adapters/` (DES-0002-E); optional unit fakes for auth/DB borders |
| Traceability | Link TEST-ONP-* to REQ-0010 / REQ-0016 / DES-0004-* |

### First implementation slice (AFTER Approval — not now)

When §13 is green:

1. Scaffold `adapters/onprem/` (FastAPI app + JWT middleware + Postgres checkpointer wiring).
2. Add `docker-compose.yml` (api + Postgres) and minimal operator docs.
3. Add `tests/adapters/` parity tests vs local CLI traveler semantics (TEST-ONP-01…07).
4. Do **not** change traveler core schema; do **not** implement AWS or Studio.

---

## Review records

Agent/human review stubs for dual Approval are recorded under `docs/design/reviews/` **when dual review completes** (same pattern as DES-0001 / DES-0002). Draft SDDs do not require a review file until review starts.
