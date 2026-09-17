# DES-0005 — AWS adapter (`adapters/aws`)

| Field | Value |
|---|---|
| **Doc ID** | DES-0005 |
| **Title** | AWS adapter (API Gateway + Lambda + DynamoDB; LocalStack/moto first) |
| **Status** | **Draft** |
| **Authors** | Marcos Blazquez (direction) + Clark Bot |
| **Reviewers (human)** | pending |
| **Reviewers (agent)** | pending |
| **Created** | 2026-09-17 |
| **Last updated** | 2026-09-17 |
| **Related REQs** | REQ-0010, REQ-0016 (from DES-0002); also REQ-0003, REQ-0013, REQ-0015 |
| **Supersedes** | none (refines DES-0002 §5.2 `adapters/aws` sketch; supersedes soft Q-AWS-1 resource-name deferral with concrete first-slice choices below) |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**), [DES-0004](0004-onprem-adapter.md) (**Approved**) as the second-target parity reference |
| **Implementation** | **Not authorized** — Draft only; dual review required before Approval; no `adapters/aws` code, no real AWS account deploy in this docs package |

---

## 0. Document posture

This SDD is the design gate for the **third deploy target**: an AWS-shaped adapter under `adapters/aws`, as sketched in DES-0002 §5.2 and explicitly deferred by DES-0004 (NG1). Local CLI and on-prem HTTP are already in tree; aspect **9** remains capped near ~70 until a third target proves the same Gatekeeper / DigitalTraveler / GraphRunner ports.

**Hard rules (must survive into any future build):**

1. Same RequestGateway / Gatekeeper / DigitalTraveler / GraphRunner ports as local + on-prem — **no fork of core**.
2. `src/` must not import AWS SDK, boto3, LocalStack, moto, SAM/CDK runtimes, FastAPI, or any `adapters/` package (DES-0002-A / TEST-0010).
3. Run / status / resume semantics match the local CLI traveler contract (and on-prem HTTP equivalents) — parity tests under `tests/adapters/`.
4. Auth is **adapter-local** — core stays agnostic of API keys / JWT / IAM authorizers.
5. Public kernel stays product-agnostic: never name private sibling products or out-of-tree app brands in this SDD or adapter code.
6. Traveler contract stays `hextory.digital_traveler@0.1` / DES-0002-G — no core schema change.
7. DES-0003 (Studio UI) remains Draft ideation and is **out of scope** here.
8. First-slice proof is **LocalStack and/or moto** (+ Docker Compose or documented LocalStack compose). **Explicit NG: no deploy to a real AWS account** in the first slice.

**Dual review required** before Status may move to Approved. Reviewers remain pending; §13 stays unchecked until dual Approve.

---

## 1. Introduction / overview

### 1.1 Problem statement

Aspect **9** (multi-target deploy readiness) is capped at roughly **~70** while only `adapters/local` and `adapters/onprem` exist. Operators and maturity scoring need a **third** deploy path that binds the same pure core under AWS-shaped ingress and persistence — **without** requiring a live cloud account for the first verification slice. DES-0002 already sketched `adapters/aws` (API Gateway → Lambda, managed store) but deferred it under DES-0002-J / DES-0004-A. This SDD is the design gate for that slice.

### 1.2 Goals

- **G1 (REQ-0010 / REQ-0016):** Specify `adapters/aws` so the same pure `src/` core runs under an AWS-shaped binding with identical traveler/workflow semantics to `adapters/local` and `adapters/onprem`.
- **G2:** Semantic parity for run / status / resume (or AWS-shaped equivalents) vs local CLI traveler outcomes — same Gatekeeper denial and terminal statuses (shipped / escalated / denied).
- **G3:** First slice proven with **moto and/or LocalStack** + Docker Compose (or documented LocalStack compose). **Explicit NG: no deploy to a real AWS account.**
- **G4:** Optional IaC (SAM / CDK / CloudFormation) may land as design-tracked artifacts that are **not applied** against a real account in the first slice.
- **G5 (REQ-0015):** TDD + BDD-style (Given/When/Then in ordinary pytest, not Cucumber) tests under `tests/adapters/` proving parity vs local CLI traveler outcomes.

### 1.3 Success definition

- Dual review Approves this SDD without re-litigating DES-0002 core ports or DES-0004 on-prem parity baseline.
- Agents implement the AWS-shaped vertical slice against acceptance criteria and TEST IDs without inventing architecture.
- Parity tests demonstrate that a run accepted/denied/shipped/escalated via the AWS adapter path matches local CLI traveler semantics for the same inputs (under LocalStack/moto).
- Aspect-9 evidence path exists once implemented (adapter package + LocalStack/moto compose or harness + parity tests) **without** real-account deploy.

### 1.4 Scope

**In scope (this Draft SDD — design only until Approved):**

- AWS adapter architecture, inbound HTTP contract mapping, DynamoDB (primary) persistence role, LocalStack/moto proof path.
- Auth default proposal (adapter-local API key / JWT via authorizer stub) and open questions for Marcos confirmation.
- Design decisions DES-0005-A…F; acceptance criteria; gate criteria; TEST ID plan.
- Traceability to REQ-0010 / REQ-0016 (and related gateway/testing REQs).
- Optional uneployed IaC stub posture (SAM/CDK/CloudFormation checked into repo but not applied).

**Out of scope:** see Explicit non-goals (§8). First-slice AWS scaffold is authorized **only** after Status is **Approved** and §13 is green; Studio remains deferred; real AWS account deploy remains NG for first slice.

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
HTTP client (curl / ops tool / future Studio profile)
        │  Authorization: API key or Bearer JWT (adapter-local; Q-AWS-1)
        ▼
API Gateway HTTP API  ──► Lambda handlers (`adapters/aws`)
        │                           │
        │                           ├── RequestGateway (src/) + interceptors
        │                           ├── Gatekeeper / SddStatusReader
        │                           ├── GraphRunner (pure or LangGraph via port)
        │                           └── departments (unchanged)
        │
        ├── DynamoDB checkpointer / traveler store (Checkpointer port)
        └── LocalStack (Compose) and/or moto (unit) — first-slice proof only
            Optional: uneployed SAM/CDK/CloudFormation stubs (not applied)
```

**Who calls it:** AWS-shaped HTTP clients and CI/parity harnesses (LocalStack/moto).  
**What it calls:** the same `src/` gateway and ports as `adapters/local` / `adapters/onprem`; DynamoDB (or LocalStack DynamoDB) for durable state.

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). This SDD owns the **AWS adapter boundary only**. Core packages (`domain`, `ports`, `departments`, `graphs`, `policies`, `gateway`) are not forked.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| API Gateway HTTP API + Lambda handlers (`adapters/aws`) | AWS-shaped bind for run / status / resume; auth validation; map JSON ↔ gateway DTOs | n/a |
| RequestGateway (core) | Interceptors + start/resume runs | n/a |
| Gatekeeper + SddStatusReader | Refuse non-Approved `sdd_id` | n/a |
| DynamoDB checkpointer adapter | Persist/resume graph + traveler state via Checkpointer port | n/a |
| LocalStack Compose / moto harness | First-slice proof without real AWS account | n/a |
| Optional IaC stubs | SAM/CDK/CloudFormation as design-tracked, **not applied** in first slice | n/a |
| Parity tests (`tests/adapters/`) | AWS-path vs local CLI traveler semantics | n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0005-A** | Third deploy target after on-prem is **AWS-shaped** (`adapters/aws`) | GCP/Azure first; “generic cloud” only; skip third target | Aligns with DES-0002 sketch; clears aspect-9 ceiling after local+onprem |
| **DES-0005-B** | First-slice proof = **LocalStack and/or moto**; real AWS account deploy deferred (**NG**) | Real account day one; LocalStack-only forever | Verifiable in CI/public kernel without credentials or spend |
| **DES-0005-C** | Persistence primary = **DynamoDB** via Checkpointer port (traveler + checkpoint items); S3 deferred for large artifacts | S3-primary blobs; S3+Dynamo dual-write day one; reuse Postgres remotely | Single managed KV matches serverless handlers; LocalStack/moto Dynamo coverage is mature; simpler first slice than dual stores (**Q-AWS-2** confirms vs S3-primary) |
| **DES-0005-D** | Inbound = **API Gateway HTTP API + Lambda handlers** mapped to same semantic ops as on-prem `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` | Lambda Function URL only; ALB+ECS; API Gateway REST (v1) | Matches DES-0002 AWS sketch; multi-route HTTP semantics without Function URL’s thinner gateway features; HTTP API is lighter than REST v1 |
| **DES-0005-E** | Auth is **adapter-local** (API keys and/or JWT via LocalStack authorizer stub); core stays agnostic | IAM-only SigV4 for all clients; no auth in first slice; copy on-prem JWT verbatim as mandatory | Keeps hexagonal purity; LocalStack can stub authorizers; exact scheme is **Q-AWS-1** for Marcos |
| **DES-0005-F** | Reuse core `RequestGateway` + interceptor stack; adapter only wires ports | Separate AWS gateway; fork Gatekeeper | Preserves REQ-0010 / REQ-0013; no second engine |

---

## 3. Data design

### 3.1 Entities / state

Core DigitalTraveler schema is **unchanged** (DES-0002-G / published `hextory.digital_traveler@0.1`). This adapter persists and returns the same traveler fields.

| Entity | Key fields | Lifecycle |
|---|---|---|
| DigitalTraveler | `traveler_id`, `sdd_id`, `workflow_id`, status, `routing_history`, `rework_count`, … | Created on accepted run; updated through graph; terminal shipped / escalated / denied |
| Checkpoint record | `traveler_id` (PK), checkpoint blob / LangGraph-compatible state, updated_at | Written on node boundaries; required for resume |
| Run request (HTTP) | `sdd_id`, `workflow_id`, payload, optional `idempotency_key` | Mapped to core RunRequest |
| Auth principal (adapter-local) | API key id / JWT subject used only for interceptor context | Not stored in traveler core schema |
| Idempotency record | `idempotency_key` → traveler_id / denial | Adapter concern; same semantics as local/on-prem |

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
Client auth → API Gateway HTTP API → Lambda handler
  → RequestGateway → Gatekeeper
      → deny → HTTP 4xx structured denial (no assembly)
      → allow → GraphRunner + DynamoDB checkpointer
          → traveler status / routing_history persisted
          → HTTP 200 JSON traveler summary
```

LocalStack/moto substitute DynamoDB + API Gateway/Lambda emulation for the same flow in first-slice tests.

### 3.3 Persistence & retention

- **Primary store:** DynamoDB (table design at impl — proposed: traveler item + checkpoint item keyed by `traveler_id`; exact GSI/TTL open under Q-AWS-2 interim).
- **Secondary (deferred):** S3 only if artifact blobs exceed Dynamo item limits — **not** required for first slice traveler/checkpoint parity.
- **What:** traveler snapshots, checkpoints, idempotency keys (adapter concern; same semantics as local File/Memory and on-prem Postgres stores).
- **Retention:** operator-controlled; default “retain until deleted” for first slice (no automatic TTL unless a later amendment).
- **PII:** treat payload as potentially sensitive; no secrets in traveler fields by convention (DES-0002); AWS credentials only via env / Compose secrets for LocalStack — never baked into core.

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| `POST /runs` (API GW → Lambda) | HTTP JSON | Adapter-local (API key / JWT — Q-AWS-1) | Start run; body includes `sdd_id`, `workflow_id`, payload; optional idempotency key |
| `GET /runs/{id}` | HTTP JSON | Same | Status / traveler summary by `traveler_id` |
| `POST /runs/{id}/resume` | HTTP JSON | Same | Resume from DynamoDB checkpoint |
| Health (optional) | HTTP | none or same | Liveness for LocalStack smoke — non-workflow |

All workflow paths **must** supply `sdd_id` (and workflow identity on create). Missing or non-Approved → Gatekeeper denial (no assembly entry), same as local CLI / on-prem.

Semantic ops match on-prem DES-0004-E even if physical binding is API Gateway + Lambda rather than long-lived FastAPI.

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| Core RequestGateway | Run orchestration | Propagate structured denial / traveler errors as HTTP responses |
| DynamoDB (or LocalStack Dynamo) | Checkpoints + traveler persistence | Fail run/resume with actionable error if store down when durability required |
| SddStatusReader | Resolve Approved? | Fail closed (deny) on read/parse error (Q-GATE-1) |
| LLM port (optional) | Same as local when enabled | Retry/FAIL per core interceptor policy |

### 4.3 Events / messages

Same logical domain facts as DES-0002 §4.3 (`run.accepted`, `run.denied`, `quality.failed`, `run.shipped`, …). First AWS slice may map these to structured logs (and, once DES-0006 is Approved, metrics exporters). No required SNS/SQS/EventBridge broker in first slice.

---

## 5. Component design

### 5.1 Core (pure) logic

**No new core packages required for the happy path.** AWS reuses:

- `RequestGateway` + interceptors
- Gatekeeper / policies
- DigitalTraveler + GraphRunner ports
- Starter (and registered) workflows

Any new port method needed for DynamoDB binding must be justified in an amendment or this SDD’s revision before Approval — prefer implementing the existing Checkpointer / ArtifactStore / IdempotencyStore ports in the adapter.

### 5.2 Adapters

#### `adapters/aws` (this SDD — post-Approval only)

| Piece | Design |
|---|---|
| Lambda handlers | Map API Gateway events ↔ run / status / resume; dependency-inject gateway with AWS ports |
| Auth middleware / authorizer integration | Validate API key or JWT (stub authorizer under LocalStack); attach principal to request context (adapter-local) |
| DynamoDB checkpointer | Implement Checkpointer port against DynamoDB (moto/LocalStack in first slice) |
| Traveler store | Persist/load traveler documents for status/resume |
| SddStatusReader wiring | Reuse or share local reader semantics (manifest + markdown Status) |
| LocalStack Compose (or documented compose) | Emulate API GW / Lambda / Dynamo for smoke |
| moto unit harness | In-process Dynamo (and related) fakes for fast CI (**Q-AWS-3**) |
| Optional IaC stub | SAM/CDK/CloudFormation templates checked in; **not applied** to a real account |
| Entrypoint | Handler module names at impl — e.g. `adapters.aws.handlers…` |

#### Explicitly not in this adapter (first slice)

- Real AWS account deploy / CI that applies IaC to live accounts
- Studio / React / `adapters/web` (DES-0003)
- Core schema changes
- Observability dashboards (owned by DES-0006; may consume AWS adapter later)

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Gatekeeper | Unchanged from DES-0002 — non-Approved → deny |
| Traveler semantics | Identical outcomes to local CLI for same workflow inputs / force-quality fixtures |
| Auth | Reject missing/invalid credentials with 401; do not confuse with Gatekeeper 4xx denial |
| Idempotency | Honor `idempotency_key` when provided (same semantics as local/on-prem) |
| Rework / escalate | Core policy only (max 3 default) |
| Real-account deploy | Forbidden in first slice (DES-0005-B / NG1) |

---

## 6. UI (if any)

**N/A — no UI.** This workflow is AWS-shaped HTTP / Lambda / ops (LocalStack Compose) only. CLI remains `adapters/local`. On-prem remains `adapters/onprem`. Studio remains DES-0003 Draft ideation.

```
[Visual placeholder: curl transcript against LocalStack]
$ curl -s -X POST https://localhost:4566/restapis/…/runs \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sdd_id":"DES-0002","workflow_id":"starter_factory","payload":{}}'
{"traveler_id":"trv_…","status":"shipped", …}

$ curl -s https://localhost:4566/…/runs/trv_… \
    -H "Authorization: Bearer $TOKEN"
{"traveler_id":"trv_…","status":"shipped","routing_history":[…]}
```

Exact LocalStack URLs/ports are impl details; parity is semantic, not URL-string identity with on-prem.

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-01 | DES-0002 remains Approved and local slice stays the semantic reference; DES-0004 on-prem is the HTTP parity peer | Parity undefined | Freeze traveler contract `@0.1`; parity tests vs local CLI |
| A-02 | LocalStack and/or moto can emulate enough API GW + Dynamo for first-slice parity | Emulation gaps block CI | Prefer moto for unit Dynamo; optional LocalStack compose smoke (**Q-AWS-3**) |
| A-03 | DynamoDB is acceptable primary store (DES-0005-C) | Late switch to S3-primary | **Q-AWS-2**; interim = Dynamo primary |
| A-04 | Auth scheme can be stubbed in LocalStack before production IAM/JWT hardening | Auth rework | **Q-AWS-1** blocking for Approve unless interim accepted |
| A-05 | No core schema change needed for Dynamo persistence | Forced traveler migration | Adapter maps existing fields only |
| A-06 | Optional IaC stubs do not imply live deploy | Accidental `sam deploy` / CDK apply | NG1 + CI must not apply to real accounts |

---

## 8. Explicit non-goals

- **NG1:** Deploy to a **real AWS account** (apply IaC, create live resources, use production credentials) in the first slice.
- **NG2:** Studio UI, React, xyflow, or `adapters/web` (DES-0003 stays Draft ideation).
- **NG3:** Changing DigitalTraveler core schema or published `@0.1` contract.
- **NG4:** Forking Gatekeeper, departments, or RequestGateway into an AWS-only engine.
- **NG5:** Shipping `adapters/aws` implementation while this SDD is still Draft.
- **NG6:** Mandating S3 as primary checkpoint store in first slice (deferred; see Q-AWS-2).
- **NG7:** Message bus (SNS/SQS/EventBridge), multi-region HA, or Step Functions orchestration as first-slice requirements.
- **NG8:** Importing AWS SDK / LocalStack / moto into `src/`.

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement **only after** gate criteria (§13) are green (Status **Approved**).

| ID | Criterion | Verification method |
|---|---|---|
| AC-01 | `adapters/aws` exposes run / status / resume semantic ops equivalent to on-prem `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume` | TEST-AWS-01 |
| AC-02 | Non-Approved / missing `sdd_id` → Gatekeeper denial (no assembly); HTTP maps structured denial | TEST-AWS-02 |
| AC-03 | Approved starter workflow run reaches same terminal statuses as local CLI for equivalent fixtures (under LocalStack and/or moto) | TEST-AWS-03 (parity) |
| AC-04 | DynamoDB checkpointer supports process/handler restart + resume | TEST-AWS-04 |
| AC-05 | LocalStack Compose (or documented LocalStack compose) **or** moto harness proves the path without a real AWS account | TEST-AWS-05 / manual smoke |
| AC-06 | Auth required on workflow routes per Q-AWS-1 resolution; invalid/missing → 401 (distinct from Gatekeeper denial) | TEST-AWS-06 |
| AC-07 | `src/` has zero AWS SDK / LocalStack / moto / `adapters` imports | TEST-0010 + TEST-AWS-07 |
| AC-08 | Adapter tests live under `tests/adapters/` with BDD-style readability; no Cucumber | TEST-AWS-03 docstrings / layout |
| AC-09 | Any IaC stubs in-repo are not applied to a real account in first-slice CI | TEST-AWS-08 / CI policy review |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Invalid / missing auth | Auth middleware / authorizer | HTTP 401; no gateway call | Client refreshes credentials |
| Gatekeeper deny | Core policy | HTTP 4xx structured denial | Fix SDD status / cite Approved id |
| DynamoDB unavailable | Connection/errors from store | Fail run/resume; do not pretend MemorySaver success in AWS mode | Restore LocalStack/Dynamo; retry |
| Quality FAIL | Core quality | Rework per DES-0002-H (max 3) then escalate | Same as local |
| Checkpoint corrupt / missing on resume | Checkpointer load | Structured error; no silent restart | Operator investigates store |
| Accidental real-account deploy attempt | CI / operator procedure | Block; treat as out of first-slice scope | Amend SDD before live deploy slice |

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
| 7 | Security / privacy / compliance touched? (auth, secrets, no real-account deploy) | ☐ | ☐ | Yes |
| 8 | Glossary terms used consistently | ☐ | ☐ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☐ | ☐ | No |
| 10 | No implementation leakage that bypasses this SDD | ☐ | ☐ | Yes |
| 11 | Q-AWS-1 interim (auth) acceptable to Marcos or resolved | ☐ | ☐ | Yes |
| 12 | Real AWS account deploy and Studio explicitly non-goals for first slice | ☐ | ☐ | Yes |
| 13 | LocalStack/moto-first proof path is explicit | ☐ | ☐ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | | | Approve / Changes requested |
| Agent reviewer | | | Approve / Changes requested |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| REQ-0010 | Hexagonal engine core + ports | DES-0002-A, **DES-0005-F** | TEST-0010, TEST-AWS-07 | AWS binds ports only |
| REQ-0016 | Multi-target adapter design | DES-0002-A/J, **DES-0005-A…F** | TEST-AWS-01…08 | Third target after local + on-prem |
| REQ-0003 | Hexagonal multi-target factory intent | DES-0005-A | TEST-AWS-03 | Aspect-9 path |
| REQ-0013 | Gateway + interceptors + gatekeeper | DES-0005-F | TEST-AWS-02 | Reuse gateway |
| REQ-0015 | Testing layer + TDD/BDD-style | DES-0005 (G5) | TEST-AWS-03 | `tests/adapters/` |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

All of the following must be true:

- [ ] Status is **Approved** (both human and agent reviews recorded).
- [ ] All **Critical** checklist items signed off by a human.
- [ ] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [ ] Non-goals and failure/rework policy are non-empty and specific.
- [ ] Acceptance criteria are binary/testable (no vague “should be good”).
- [ ] No open blocking questions in §15 (or each has an approved interim decision).
- [ ] Maturity / process owners acknowledge this SDD in the workflow tracker (when tooling exists).

**Only when every box is checked may agents generate implementation for this workflow.**

**Draft note:** Gate criteria are **not** green. Do not scaffold `adapters/aws` or apply IaC until dual Approve.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **AWS adapter** | `adapters/aws` API Gateway HTTP API + Lambda + DynamoDB binding of the factory engine |
| **Parity** | Same traveler terminal status / gate denial semantics as `adapters/local` for equivalent inputs |
| **LocalStack** | Local AWS service emulator used for compose smoke without a real account |
| **moto** | In-process AWS service mocks for fast unit/adapter tests |
| **DynamoDB checkpointer** | Checkpointer port implementation backed by DynamoDB (or LocalStack/moto Dynamo) |
| **Uneployed IaC** | SAM/CDK/CloudFormation artifacts present as design-tracked stubs, not applied to a live account |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) and [0002-factory-engine.md](0002-factory-engine.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-AWS-1** | Auth for first slice: API keys, JWT via LocalStack authorizer stub, both, or another scheme? | Marcos | Before Approval (blocking unless interim accepted) | **Proposed interim:** JWT bearer stub via LocalStack authorizer (aligns with on-prem DES-0004-B); API keys optional alternate — confirm |
| **Q-AWS-2** | DynamoDB vs S3 as primary traveler/checkpoint store? | Marcos | Before Approval (or accept interim) | **Proposed interim (this SDD):** DynamoDB primary; S3 deferred for large artifacts only |
| **Q-AWS-3** | LocalStack vs moto-only in CI? | Marcos + implementer | Before first CI merge post-Approval | **Proposed:** moto unit tests required; optional LocalStack Compose smoke (manual or nightly) |
| Q-AWS-4 | Exact Dynamo table key schema / GSI / TTL? | Implementer after Approval | During first impl slice | Soft — adapter-local |
| Q-AWS-5 | Which IaC flavor for uneployed stubs (SAM vs CDK vs raw CFN)? | Dual review | Soft | Soft — pick one stub at impl |
| Q-AWS-6 | When (if ever) is real-account deploy authorized (separate slice / amendment)? | Marcos | After first LocalStack/moto slice | Soft — requires explicit amendment; not first slice |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-17 | Marcos Blazquez (direction) + Clark Bot | Initial Draft: AWS third-target adapter; LocalStack/moto-first; DynamoDB primary; API GW HTTP API + Lambda; no real-account deploy; no implementation |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same names as DES-0002 / DES-0004 for gateway, traveler, gatekeeper, parity.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions or changes-requested notes.
- **Future growth** — real-account deploy is a later slice; do not smuggle live cloud into first proof.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Failing test before production code for HTTP/handler parity and gate denial |
| BDD-style | Readable Given/When/Then in ordinary pytest modules — **not Cucumber** |
| Testing layer | `tests/adapters/` (DES-0002-E); moto unit + optional LocalStack compose smoke |
| Traceability | Link TEST-AWS-* to REQ-0010 / REQ-0016 / DES-0005-* |

### First implementation slice (authorized **only after** Approval)

§13 must be green. Follow-up implementation (separate from this Draft docs package) may:

1. Scaffold `adapters/aws/` (Lambda handlers + auth wiring + DynamoDB checkpointer).
2. Add LocalStack Docker Compose (or documented LocalStack compose) and/or moto parity harness.
3. Add `tests/adapters/` parity tests vs local CLI traveler semantics (TEST-AWS-01…08).
4. Optionally check in uneployed SAM/CDK/CloudFormation stubs — **do not** apply to a real AWS account.
5. Do **not** change traveler core schema; do **not** implement Studio; do **not** deploy to a real AWS account.

---

## Review records

Dual review **pending**. Human and agent reviewers empty until recorded. Status remains **Draft**.
