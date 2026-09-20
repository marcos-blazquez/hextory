# DES-0009 — RequestGateway run bind (consumer starts live factory runs)

| Field | Value |
|---|---|
| **Doc ID** | DES-0009 |
| **Title** | RequestGateway run bind (consumer starts live factory runs) |
| **Status** | Draft |
| **Authors** | Cursor Cloud Agent (draft) |
| **Reviewers (human)** | TBD — Marcos Blazquez (dual review not completed in this agent turn) |
| **Reviewers (agent)** | TBD — Clark Bot (dual review not completed in this agent turn) |
| **Created** | 2026-09-20 |
| **Last updated** | 2026-09-20 |
| **Related REQs** | REQ-0010 (hexagonal ports); REQ-0012 (traveler); REQ-0013 (gateway/interceptors); REQ-0020 (env + in-flow vars, DES-0008); proposed **REQ-0021** (public consumer run-start contract / Stations execute slice) |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**), [DES-0004](0004-onprem-adapter.md) (**Approved**), [DES-0005](0005-aws-adapter.md) (**Approved**), [DES-0008](0008-env-and-flow-variables.md) (**Approved**) |
| **Implementation** | **Not authorized** while Status is Draft — no new gateway fork, no consumer Studio wiring claimed as shipped from this Draft |

---

## 0. Document posture

This SDD is a **thin Draft** for the **public run-start contract**: how a consumer Studio (or any HTTP / in-process client) starts a live factory run so Stations execute, with variables already resolved per DES-0008.

**Why Draft (not Approved):** dual human + agent review is mandatory. This agent turn authors the Draft only. **Do not treat this document as an implementation gate.**

**Hard rules (must survive into any future build):**

1. **RequestGateway remains the sole inbound run authority** — extend / document it; do **not** invent a parallel `FactoryRunPort` / second allow-deny engine.
2. Reuse DES-0002 DigitalTraveler, Gatekeeper, interceptor stack — **no Gatekeeper fork**.
3. Variable resolve (DES-0008 `VariableResolverPort`) binds **before** `RequestGateway.run` / HTTP `POST /runs`; the gateway still owns accept → traveler → graph.
4. Public kernel stays **consumer-agnostic**: no private sibling product names in this SDD or its tests.
5. HTTP semantics for denial vs auth vs missing traveler **must match** existing `adapters/onprem` and `adapters/aws` binds (verify against tree; do not invent a third status map).

---

## 1. Introduction / overview

### 1.1 Problem statement

DES-0008 freezes Environment + in-flow variables (`{{var}}` / `VariableResolverPort`) and seeds additive `payload["vars"]`. Authoring clients may resolve vars at publish time, but the **public contract to start a live run** (Stations execute) is still only implied by DES-0002 + adapter SDDs.

Without a thin, dual-reviewed run-bind SDD:

- Consumers invent private “execute” façades beside RequestGateway.
- Studio-shaped clients seed vars but never call the gateway.
- Denial (Gatekeeper) vs 401 (auth) vs transport errors stay easy to confuse.

### 1.2 Goals

- **G1 (REQ-0021 / REQ-0013):** Freeze the **RequestGateway run bind** — in-process `run` / `status` / `resume` and the HTTP routes already shipped in on-prem + AWS adapters.
- **G2:** Specify inputs: `sdd_id`, `workflow_id`, `payload` (including DES-0008 `vars`), optional `idempotency_key`, adapter-local auth principal.
- **G3:** Specify outputs: `traveler_id`, `status`, structured denial vs **401** vs other errors — aligned with existing adapters.
- **G4:** Place **`VariableResolverPort` before** `RequestGateway.run` (resolve → then start run).
- **G5:** Keep the port name honest: **RequestGateway** is the core; HTTP is the bind — not a new parallel authority.

### 1.3 Success definition

- Dual review Approves (or requests changes) without re-litigating DES-0002 / DES-0008.
- After Approval, consumer clients and agents can wire “resolve vars → `POST /runs`” without private execute APIs.
- Stations-execute product slice cites this SDD for the public start-run contract.

### 1.4 Scope

**In scope:**

- Public run-start / status / resume contract (in-process + HTTP).
- How DES-0008 resolve fits before gateway accept.
- Status-code and body semantics verified against `adapters/onprem` and `adapters/aws`.
- Design decisions, acceptance criteria, TEST ID plan, gate criteria.

**Out of scope:** see Explicit non-goals (§8). No implementation while Draft.

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
Consumer Studio / CLI / HTTP client
        │
        │  1) VariableResolverPort.effective_vars / resolve_*
        │     → payload["vars"] (+ node field templates resolved as needed)
        ▼
HTTP bind (on-prem FastAPI / AWS API GW→Lambda)  OR  in-process Python
        │  POST /runs  { sdd_id, workflow_id, payload, idempotency_key? }
        │  Authorization: Bearer …   ← adapter-local; 401 ≠ gate denial
        ▼
RequestGateway.run(...)          ← ONLY inbound run authority
        │  interceptors (DES-0002-H)
        │  Gatekeeper(sdd_id) unchanged
        ▼
DigitalTraveler → GraphRunner    ← Stations / departments execute
```

**Who calls it:** any consumer that starts a live run (Studio-shaped clients, CLI, tests, adapters).  
**What it does not call:** Gatekeeper is not replaced; var resolve is not a second allow/deny engine.

### 2.2 Architectural style

Hexagonal / ports & adapters. This SDD owns the **consumer-facing run bind** of existing RequestGateway + adapter HTTP. Variable bind/resolve remains DES-0008. Engine / traveler / Gatekeeper remain DES-0002.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| **`VariableResolverPort`** | Merge env + in-flow; resolve `{{var}}` **before** start-run | n/a (DES-0008) |
| **RequestGateway** | `run` / `status` / `resume`; interceptor chain; create traveler; invoke graph | n/a |
| HTTP bind (on-prem / AWS) | Map JSON + JWT ↔ gateway; status codes | n/a |
| Gatekeeper | Approved-SDD gate only | n/a |
| GraphRunner | Stations / department execution | assembly / quality / packaging / … |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0009-A** | **Port / authority name = RequestGateway** (document HTTP as its **run bind**). Do not mint `RunPort` / `FactoryRunPort` as a second inbound façade | New `FactoryRunPort` wrapping gateway; Studio-only execute API | Extends existing REQ-0013 authority; avoids parallel allow/deny |
| **DES-0009-B** | HTTP ops stay: `POST /runs`, `GET /runs/{traveler_id}`, `POST /runs/{traveler_id}/resume` (parity on-prem ↔ AWS) | New `/execute` path; Studio-private RPC | Already shipped in DES-0004 / DES-0005 adapters |
| **DES-0009-C** | Consumer path: **resolve binds → then `RequestGateway.run` / `POST /runs`** with `payload` including `vars` | Resolve only inside gateway after accept; skip resolve | Matches “vars already resolved” Studio start-run; still compatible with gateway-side seed from DES-0008 |
| **DES-0009-D** | Status map (HTTP): **401** = adapter auth only; **403** = structured gateway denial (`RunResult.denied`); **404** = unknown traveler; **200** = accepted/completed result body (or status lookup). Auth never returns gate-shaped traveler denial | Fold auth into 403; invent 422 for gate | Verified in `adapters/onprem/app.py` + `adapters/aws/handlers.py` |
| **DES-0009-E** | Auth principal is **adapter-local** (JWT bearer stub today); core RequestGateway stays identity-agnostic | Core Cognito / hosted IdP in `src/` | Keeps hexagonal core; IdP products are non-goals here |
| **DES-0009-F** | Implementation deferred until Approved | Soft-allow Draft consumer wiring as “shipped contract” | Hard rule: Draft ≠ production posture for new bind code |

---

## 3. Data design

### 3.1 Entities / state

| Entity | Key fields | Lifecycle |
|---|---|---|
| Run request body | `sdd_id`, `workflow_id`, `payload`, optional `idempotency_key` | one HTTP / in-process call |
| `payload["vars"]` | effective map from DES-0008 (additive under `@0.1`) | seeded pre-run and/or at gateway; checkpointed with traveler |
| `RunResult` | `traveler`, `denied`, `reason` | returned from `RequestGateway.run` / `resume` |
| Traveler summary JSON | `traveler_id`, `status`, `denied`, `reason`, routing, payload, … | HTTP response body (on-prem / AWS parity) |
| Auth principal | adapter-local subject claims | request-scoped; not a core traveler field |

No new DigitalTraveler core fields. No Gatekeeper schema change.

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
1. Consumer builds env + in-flow maps
2. VariableResolverPort.effective_vars(...) → effective
3. Optional: resolve_fields / resolve_template for authored node templates
4. POST /runs | RequestGateway.run(
     sdd_id, workflow_id,
     payload={..., "vars": effective, ...},
     idempotency_key?
   )
5. Interceptors → Gatekeeper → traveler create OR denial
6. GraphRunner executes Stations when accepted
7. Response: traveler_id + status (+ denied/reason when denied)
```

### 3.3 Persistence & retention

Unchanged from DES-0002 / adapter SDDs. Traveler + `payload["vars"]` persist via Checkpointer. No new store for this SDD.

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| `RequestGateway.run` | In-process Python | n/a (caller supplies context) | Start run; returns `RunResult` |
| `RequestGateway.status` | In-process | n/a | Load traveler by id or `None` |
| `RequestGateway.resume` | In-process | n/a | Resume or terminal replay; `None` if missing |
| `POST /runs` | HTTP JSON | JWT bearer (adapter) | Body: `sdd_id`, `workflow_id`, `payload`, optional `idempotency_key` |
| `GET /runs/{id}` | HTTP JSON | JWT bearer | Traveler summary; **404** if missing |
| `POST /runs/{id}/resume` | HTTP JSON | JWT bearer | Resume; **404** if missing; **403** if denied result |

#### HTTP request (`POST /runs`) — semantic body

```json
{
  "sdd_id": "DES-0002",
  "workflow_id": "starter_factory",
  "payload": {
    "vars": { "region": "us-east-1", "flow_greeting": "hi" }
  },
  "idempotency_key": "optional-client-key"
}
```

#### HTTP response outcomes (verified against adapters)

| Outcome | HTTP | Body shape | Notes |
|---|---|---|---|
| Auth missing / invalid | **401** | `{ "detail": ... }` (+ `WWW-Authenticate` on AWS) | **Never** a Gatekeeper denial |
| Gate / interceptor / unknown workflow denial | **403** | Traveler summary with `denied: true`, `reason`, `traveler_id`, `status: "denied"` | Structured denial; no assembly entry when gate denies |
| Accepted / completed run | **200** | Traveler summary (`denied: false`) | Status may be shipped / escalated / in-progress per runner |
| Traveler not found (GET/resume) | **404** | `{ "detail": "traveler not found: …" }` | |
| Gateway not wired (on-prem) | **503** | detail | Ops misconfig; not a product denial |
| Route not found (AWS) | **404** | detail | |

**In-process:** `RunResult.denied` / `reason` mirror the 403 body facts without HTTP. Missing traveler on `status` / `resume` → `None` (adapters map to 404).

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| **`VariableResolverPort`** (before run) | Produce effective `payload["vars"]` / resolve templates | Undefined bind → fail closed **before** gateway (DES-0008-D); not a 403 gate denial |
| **RequestGateway** | Accept / deny / execute | `RunResult` or traveler errors per DES-0002 |
| Gatekeeper | Approved SDD check | Denial → traveler DENIED + HTTP 403 |
| Checkpointer / GraphRunner | Persist + execute | Same as DES-0002 / adapters |

### 4.3 Events / messages

Reuse DES-0002 lifecycle facts (`run.accepted`, `run.denied`, …). No new required broker topics. Metrics scrape remains DES-0006 (explicit non-goal here).

---

## 5. Component design

### 5.1 Core (pure) logic

**No new core package required for the happy path.** Document and (post-Approval) optionally thin-harden:

- Existing `RequestGateway.run` / `status` / `resume` signatures and `RunResult`.
- Optional clarity helpers (docs / type aliases) that **alias** RequestGateway — must not become a second façade that bypasses Gatekeeper.

Forbidden in `src/`:

- Consumer Studio UI, Cognito/IdP SDKs, private execute APIs that skip RequestGateway.
- Gatekeeper forks / soft-allow Draft workflow runs.

### 5.2 Adapters

| Piece | Design |
|---|---|
| `adapters/onprem` | FastAPI routes already implement the HTTP bind (DES-0004-E) |
| `adapters/aws` | Lambda handlers already implement the same semantic ops (DES-0005-D) |
| `adapters/local` CLI | In-process `RequestGateway.run` parity |
| Consumer Studio | **After Approval:** call resolve → HTTP/in-process run bind; no private engine |

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Authority | Only RequestGateway starts/resumes runs |
| Pre-run vars | Consumer SHOULD call `VariableResolverPort` so `payload["vars"]` is effective before `run` |
| Gatekeeper | Unchanged — missing / non-Approved `sdd_id` → deny |
| Auth vs deny | 401 ≠ 403; adapters must keep that split |
| Idempotency | Honor `idempotency_key` when provided (existing interceptor) |
| Unknown workflow | Gateway denial (HTTP 403), not 404 |

---

## 6. UI (if any)

**N/A — no UI in this SDD.** Studio canvas / publish UX belongs to DES-0003 (Draft ideation) and remains an explicit non-goal here. This document only freezes the **API / port contract** those UIs must call to start a live run.

```
[Visual placeholder: curl transcript]
$ # 1) resolve vars (VariableResolverPort / client) → payload.vars
$ curl -s -X POST https://onprem.example/runs \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sdd_id":"DES-0002","workflow_id":"starter_factory","payload":{"vars":{"region":"eu"}}}'
{"traveler_id":"trv_…","status":"shipped","denied":false,…}

$ # Missing JWT → 401 (not gate denial)
$ # Draft / missing sdd_id → 403 traveler denial body
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-1 | On-prem + AWS HTTP status maps stay the public reference | Drift invents a third map | Cite adapter files; TEST-RUN-* parity |
| A-2 | DES-0008 `payload["vars"]` additive attachment is stable | Consumer invents private bags | Depend on Approved DES-0008; no private names |
| A-3 | Dual review before any new bind/impl claimed from this SDD | Agents ship Draft as done | §13 + CONTRIBUTING |
| A-4 | Auth remains adapter-local for first consumer slice | Pressure to put Cognito in core | NG2; DES-0009-E |

---

## 8. Explicit non-goals

- **NG1:** No Studio UI, canvas, publish UX, or web app implementation (DES-0003 remains separate).
- **NG2:** No Cognito / hosted identity-provider product design in core or this SDD.
- **NG3:** No metrics scrape / Prometheus `/metrics` / Grafana work (DES-0006 owns that).
- **NG4:** No Gatekeeper fork / soft-allow; no parallel `FactoryRunPort` inbound authority.
- **NG5:** No private sibling product names in this public doc or its tests.
- **NG6:** No Cucumber / Gherkin toolchain.
- **NG7:** No real cloud account deploy from the implementation PR or CI.
- **NG8:** No redesign of traveler core schema or interceptor order (unless a future SDD).

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement **only after** gate criteria (§13) are green (Status **Approved**).

| ID | Criterion | Verification method |
|---|---|---|
| AC-RUN-01 | Public docs/tests treat **RequestGateway** as the only start-run authority (no parallel inbound port type required) | TEST-RUN-01 + review |
| AC-RUN-02 | HTTP `POST /runs` accepts `sdd_id`, `workflow_id`, `payload` (with `vars`), optional `idempotency_key` on on-prem and AWS binds | TEST-RUN-02 |
| AC-RUN-03 | Missing/invalid bearer → **401**; Gatekeeper denial → **403** with traveler summary (`denied: true`) | TEST-RUN-03 |
| AC-RUN-04 | Unknown `traveler_id` on GET/resume → **404** | TEST-RUN-04 |
| AC-RUN-05 | Documented consumer sequence: VariableResolverPort (or equivalent effective map) **before** `RequestGateway.run` / `POST /runs` | TEST-RUN-05 (behavior narrative + optional unit) |
| AC-RUN-06 | Gatekeeper behavior unchanged for Approved vs non-Approved workflow SDDs | TEST-RUN-06 / existing gate tests |
| AC-RUN-07 | Behavior tests use Given/When/Then style in ordinary pytest | TEST-RUN-07 |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Undefined `{{var}}` pre-run | VariableResolverPort | Fail closed before gateway | Fix vars/templates; re-call resolve then run |
| Auth failure | Adapter JWT | HTTP **401** | Supply valid bearer |
| Gate denial | Gatekeeper | Traveler DENIED; HTTP **403** | Approve SDD / fix `sdd_id` |
| Unknown workflow | Gateway | Denial; HTTP **403** | Register workflow |
| Missing traveler | status/resume | HTTP **404** / `None` | Correct id |
| Impl claiming this Draft as shipped contract | Process / review | Reject | Dual Approve + §13 |

**Rework policy:** Pre-run resolve failures and gate denials are **request** failures, not Quality FAIL→assembly rework (unless a workflow SDD maps them). Default max rework (3) unchanged for quality loops.

---

## 11. Human + agent review checklist

Reviewers must check each item. Architecture-critical items require **human** sign-off.

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☐ | ☐ | Yes |
| 2 | Architecture fits hexagonal / factory rules; RequestGateway remains sole run authority; no Gatekeeper fork | ☐ | ☐ | Yes |
| 3 | Interfaces and failure modes specified; 401 ≠ 403 ≠ 404 | ☐ | ☐ | Yes |
| 4 | Acceptance criteria are testable | ☐ | ☐ | Yes |
| 5 | Traceability IDs are complete and unique | ☐ | ☐ | Yes |
| 6 | Gate criteria are unambiguous | ☐ | ☐ | Yes |
| 7 | Security / privacy / compliance touched? (auth principal, payload vars) | ☐ | ☐ | Yes |
| 8 | Glossary terms used consistently | ☐ | ☐ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☐ | ☐ | No |
| 10 | No implementation leakage; no private product names | ☐ | ☐ | Yes |
| 11 | VariableResolverPort ordered **before** gateway run in consumer path | ☐ | ☐ | Yes |
| 12 | HTTP bind matches existing on-prem / AWS adapters (no third map) | ☐ | ☐ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | | | Approve / Changes requested |
| Agent reviewer | | | Approve / Changes requested |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| REQ-0021 (proposed) | Public consumer run-start / Stations-execute bind | DES-0009-A…F | TEST-RUN-01…07 | |
| REQ-0013 | Gateway + interceptors + gatekeeper | DES-0009-A, D | TEST-RUN-03, TEST-RUN-06 | |
| REQ-0010 | Hexagonal ports | DES-0009-A, E | TEST-RUN-01 | |
| REQ-0012 | DigitalTraveler; no core fork | DES-0009 | TEST-RUN-02 | |
| REQ-0020 | Env + in-flow vars before/with run envelope | DES-0008 + DES-0009-C | TEST-RUN-05 | |

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
- [ ] `config/sdd_status.json` lists `"DES-0009": "Approved"` matching the Status cell.

**Only when every box is checked may agents generate implementation for new bind code under this SDD.**

**Current state:** Status is **Draft** — §13 is **not** green. Dual review required. Do not implement from this Draft.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **RequestGateway** | Core inbound façade: `run` / `status` / `resume` — sole run authority |
| **Run bind** | Consumer-facing contract of RequestGateway (in-process + HTTP `POST/GET /runs…`) |
| **Stations execute** | Product slice: live factory run where registered graph nodes (Stations) actually run |
| **Structured denial** | `RunResult.denied` / HTTP **403** traveler summary — not auth failure |
| **Auth principal** | Adapter-local identity from JWT (or future adapter auth); not a core traveler field |
| **Pre-run resolve** | Calling `VariableResolverPort` so `payload["vars"]` is effective before start-run |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) and [0002-factory-engine.md](0002-factory-engine.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-RUN-1** | May gateway-side DES-0008 seed remain mandatory even when consumer already sent effective `payload["vars"]`? | Dual review | Before Approval (or accept interim) | Soft interim proposal: **merge** consumer `vars` with adapter env using DES-0008-G precedence; do not wipe client vars |
| **Q-RUN-2** | Should resume require the same pre-run resolve step, or only create (`POST /runs`)? | Dual review | Before Approval | Soft interim: resolve applies to **create**; resume uses checkpointed traveler payload |
| Q-RUN-3 | Expose a documented Python Protocol alias (name-only) that simply describes RequestGateway methods for typed consumers? | Dual review | Post-MVP | Soft — prefer documenting RequestGateway directly (DES-0009-A) |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-20 | Cursor Cloud Agent | Initial **Draft**: RequestGateway run bind; resolve-then-start; HTTP 401/403/404 parity with on-prem + AWS; dual review pending; no Approval claimed |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same names as DES-0002 / DES-0004 / DES-0005 / DES-0008.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions or changes-requested notes.
- **Future growth** — deeper Studio UX gets DES-0003 (or amendments); do not overload this SDD.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the design produces code)

| Item | Guidance |
|---|---|
| TDD | Failing test before production consumer-bind wiring |
| BDD-style | Readable Given/When/Then in ordinary pytest — **not Cucumber** |
| Testing layer | `tests/unit/` + `tests/behavior/` + existing `tests/adapters/` parity |
| Traceability | Link TEST-RUN-* to REQ-0021 / REQ-0013 / DES-0009-* |

### Planned TEST IDs (post-Approval)

| TEST ID | Intent |
|---|---|
| TEST-RUN-01 | No parallel inbound run port required; RequestGateway remains the façade |
| TEST-RUN-02 | `POST /runs` body fields + `payload["vars"]` accepted (on-prem + AWS harness) |
| TEST-RUN-03 | 401 auth vs 403 gate denial split |
| TEST-RUN-04 | 404 missing traveler on GET/resume |
| TEST-RUN-05 | Resolve-then-run sequence documented / covered in behavior test |
| TEST-RUN-06 | Gatekeeper still denies non-Approved workflow SDDs |
| TEST-RUN-07 | Behavior module uses Given/When/Then structure |

### First implementation slice (only after Approval)

§13 must be green. Follow-up implementation (separate from this Draft) may:

1. Add consumer-facing docs / examples that call resolve → `POST /runs` / `RequestGateway.run`.
2. Add TEST-RUN-01…07 (mostly adapter/behavior parity; avoid duplicating DES-0008 VAR tests).
3. Optionally clarify gateway merge when client already supplied `payload["vars"]` (Q-RUN-1).
4. Do **not** implement Studio UI; do **not** add Cognito to core; do **not** fork Gatekeeper; do **not** invent `FactoryRunPort`.
