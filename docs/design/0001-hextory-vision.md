# DES-0001 — Hextory vision (meta-system)

| Field | Value |
|---|---|
| **Doc ID** | DES-0001 |
| **Title** | Hextory vision — design-gated dark factory |
| **Status** | **Approved** |
| **Authors** | Marcos Blazquez + Clark Bot |
| **Reviewers (human)** | Marcos Blazquez (2026-09-15 — architecture, roles, non-goals; “looks good”) |
| **Reviewers (agent)** | Clark Bot (2026-09-15 — checklist pass; see §14) |
| **Created** | 2026-09-15 |
| **Last updated** | 2026-09-15 (Approved after dual review) |
| **Related REQs** | REQ-0001, REQ-0002, REQ-0003 |
| **Supersedes** | none |

---

## 1. Introduction / overview

### 1.1 Problem statement

Two related bottlenecks block AI-assisted production software:

1. **Human code-review bottleneck.** Diff-centric review does not scale when agents produce large volumes of code. Humans become rubber stamps or blockers; neither yields trustworthy ships.
2. **Agent code without shared design.** Agents that implement from chat threads or vague tickets generate inconsistent architecture, silent scope creep, and unverifiable “done.” There is no durable contract binding requirement → design → implementation → test.

Hextory addresses both by making the **Software Design Document (SDD)** the primary gate. Humans and agents co-review design; implementation is allowed only after approval.

### 1.2 Goals

- **G1 (REQ-0001):** Establish a public project culture where **Approved SDDs** are mandatory before code generation for any workflow.
- **G2 (REQ-0002):** Define roles and an operating model for a software **dark factory** (human designers, agent implementers, dual reviewers).
- **G3 (REQ-0003):** Capture high-level factory architecture intent (hexagonal, multi-target adapters, quality rework loop) without authorizing full engine implementation yet.

### 1.3 Success definition

- Contributors know where design docs live, how dual review works, and that unapproved code is out of policy.
- Vision, workflow, maturity scorecard, and engine **intent** docs exist and are cross-linked.
- First engine implementation SDD (future DES) can be written against this vision without re-litigating basics.

### 1.4 Scope

**In scope:** vision, operating model, roles, high-level architecture sketch, DigitalTraveler sketch, interface sketch, glossary, open questions.

**Out of scope:** runnable LangGraph factory code, production AWS/on-prem deployables, CI gate automation (described as future), binding API schemas.

---

## 2. Goals and non-goals (summary)

### Goals

| ID | Goal |
|---|---|
| REQ-0001 | Design-doc gate is the path to implementation |
| REQ-0002 | Dark-factory roles and dual review are explicit |
| REQ-0003 | Hexagonal factory intent is documented for later SDDs |
| REQ-0004 | Open-ended graphs + TDD/BDD-style testing + code-review avoidance as one capability |

### Explicit non-goals

- **NG1:** Replacing all human judgment—humans own architecture-critical approval.
- **NG2:** Shipping a full factory engine in this ideation pack.
- **NG3:** Mandating a specific LLM vendor or cloud as the only runtime.
- **NG4:** Requiring human line-by-line CODE review of implementation diffs as a merge prerequisite (see merge gate below).
- **NG5:** Allowing main-line merges without human confirmation that the design-doc gate is green.

---

## 3. Dark factory operating model

```
[Visual placeholder: operating model]
Ideation → Draft SDD → Human review → Agent review → Approved
        → Implementation allowed → Verification vs SDD → Shipped
        ↖ Quality FAIL / Changes requested (rework)
```

**Principles**

1. **Design is the factory floor plan.** Code is the manufactured good.
2. **Lights-out implementation.** Once gates are green, agents assemble, quality-check, and package without waiting on line-by-line human review.
3. **Rework is first-class.** Quality FAIL loops back with structured defects; it is not an informal “try again” chat.
4. **Public by default.** Process and docs are visible so external contributors can follow the same gates.

### Merge gate (human approval without code walkthrough)

| Required | Not required |
|---|---|
| Human approval to merge to the **main line** | Human line-by-line review of implementation code |
| Confirmation that the workflow **SDD is Approved** and gate criteria are green | PR diff walkthrough as the primary quality signal |
| Confirmation the change set is **in scope** for that SDD | Humans re-deriving design from the code |

**DES-0001-B:** Main-line merges require human approval grounded in design-doc readiness. Agent implementation + verification against the Approved SDD replace human code walkthrough as the default quality path.

---

## 4. Roles

| Role | Who | Responsibilities |
|---|---|---|
| **Human designer** | Humans | Own problem framing, architecture-critical sections, non-goals, acceptance criteria; approve or request changes |
| **Agent implementer** | Agents | Draft SDDs (allowed); implement **only** after Approved; map work to REQ/DES/TEST IDs |
| **Human reviewer** | Humans | Dual-review pass focusing on architecture, risk, non-goals, gates |
| **Agent reviewer** | Agents | Structured checklist review: consistency, traceability, testability, hexagonal fit |
| **Process steward** | Human (initially Marcos) | Maturity scorecard, template health, public-project readiness |

Agents may **draft** SDDs. Humans **must** approve architecture-critical sections before status may become Approved.

---

## 5. System architecture (factory — high level)

### 5.1 Hexagonal intent

Pure **core** in `src/` (domain + use-cases). **Ports** define gatekeeper, run, persistence, and department interfaces. **Adapters** bind targets:

| Target | Typical adapters |
|---|---|
| Local | CLI, MemorySaver / in-memory checkpointing |
| On-prem | Docker, FastAPI, Postgres |
| AWS serverless | Lambda/API Gateway (or equivalent), managed persistence |

```
[Visual placeholder: hexagonal diagram]
        ┌─────────────────────────┐
        │   Gateway + interceptors │
        └───────────┬─────────────┘
                    │
        ┌───────────▼─────────────┐
        │  Core (pure) + graph     │
        │  Departments:            │
        │   assembly | quality |   │
        │   packaging              │
        └───────────┬─────────────┘
     ports ◄────────┴────────► adapters (local / on-prem / AWS)
```

### 5.2 Departments

| Department | Responsibility |
|---|---|
| **Assembly** | Produce or transform artifacts per Approved SDD |
| **Quality** | Evaluate against acceptance criteria; PASS/FAIL + defect report |
| **Packaging** | Emit shippable outputs (artifacts, manifests, release metadata) |

**DES-0001-C:** Assembly / quality / packaging is a **starter topology**, not a closed catalog. The factory must allow **open-ended node/edge combinations** (new departments, validators, exporters, conditional/rework edges) defined via SDDs + config/registry. Combinations are unbounded in principle.

### 5.3 Quality FAIL rework loop

On Quality **FAIL**, the DigitalTraveler returns to Assembly (or a designated rework step) with defect details. After max attempts (defined per workflow SDD), escalate to a human designer/reviewer.

**DES-0001-A:** Factory runtime (when built) must not mark work Shipped while Quality is FAIL or SDD gate is not Approved.

---

## 6. Data design — DigitalTraveler sketch

`DigitalTraveler` is the mutable state object that moves through the factory.

| Field (sketch) | Purpose |
|---|---|
| `traveler_id` | Stable ID for the unit of work |
| `workflow_id` / `sdd_id` | Link to Approved SDD (DES-NNNN) |
| `status` | Ideation…Shipped (see workflow doc) |
| `payload` | Work inputs / intermediate artifacts refs |
| `quality_reports[]` | Structured PASS/FAIL history |
| `rework_count` | Attempts used |
| `trace` | REQ/DES/TEST references satisfied so far |
| `audit` | Who/what transitioned state |

Exact schema is deferred to a dedicated engine SDD; this sketch is directional only.

---

## 7. Interface design (sketch)

| Interface | Role |
|---|---|
| **Gatekeeper** | Enforce design-doc gate; refuse implementation runs without Approved SDD |
| **Run endpoints** | Start/resume factory runs; accept traveler + workflow identity |
| **CLI** | Local operator entrypoint for drafts, reviews status, and local runs |

AuthN/Z, API schemas, and event bus details are **out of scope** until the engine SDD.

---

## 8. Assumptions and dependencies

| ID | Assumption | Risk | Mitigation |
|---|---|---|---|
| A1 | Contributors will write SDDs before coding | Bypass culture | Public PR policy + CI gates (future) |
| A2 | Agents can follow Approved SDDs faithfully enough | Drift | Verification vs SDD + quality dept |
| A3 | LangGraph + Pydantic v2 remain suitable for the engine | Tech change | Hexagonal core isolates engine choice |
| A4 | Public git hosting will be used | Delay going public | Track under maturity aspect 10 |

---

## 9. Open questions

| ID | Question | Owner | Notes |
|---|---|---|---|
| Q1 | Exact DigitalTraveler schema and persistence model? | Engine SDD | Deferred |
| Q2 | Which CI checks enforce the design-doc gate first? | Process steward | After public git |
| Q3 | How are agent reviewer identities attested in git history? | TBD | Sign-off convention |
| Q4 | License/community norms beyond MIT? | Marcos | Scorecard aspect 10 |
| Q5 | Max default rework attempts factory-wide vs per SDD? | Engine SDD | Prefer per-SDD |
| Q6 | Exact home of the testing layer (package layout)? | Engine SDD | Deferred; must not block DES-0001 |
| Q7 | Graph/registry format for open-ended workflows? | Engine SDD | Deferred |

---

## 10. Traceability (initial)

| REQ ID | Description | DES IDs | TEST IDs |
|---|---|---|---|
| REQ-0001 | Design-doc gate before implementation; human merge via doc readiness (not code walkthrough) | DES-0001, DES-0001-A, DES-0001-B | TEST-0001 (future: gatekeeper + merge-policy tests) |
| REQ-0002 | Roles + dual review operating model | DES-0001 | TEST-0002 (future: workflow conformance) |
| REQ-0003 | Hexagonal multi-target factory intent | DES-0001 + engine intent doc | TEST-0003 (future) |
| REQ-0004 | Open graphs + TDD/BDD-style + code-review avoidance as one capability | DES-0001-C, DES-0001-D | TEST-0004 (future) |

---

## 11. Gate criteria for *this* doc

Before DES-0001 may move to **Approved**:

- [x] Human review of architecture, roles, non-goals — Marcos Blazquez, 2026-09-15
- [x] Agent review for consistency with TEMPLATE and workflow doc — Clark Bot, 2026-09-15 (§14)
- [x] Open questions labeled deferred vs blocking (Q1–Q7 deferred; none blocking for vision)
- [x] Cross-links from README and scorecard verified

**Note:** Approving DES-0001 does **not** authorize factory engine implementation. A dedicated engine SDD is still required (see [factory-engine-intent.md](../architecture/factory-engine-intent.md)).

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Hextory** | This project: a design-gated dark factory for agent-implemented software, named for hexagonal architecture + history/traceability of design. |
| **Dark factory** | Operating model where implementation proceeds without human code-review as the primary gate; humans gate design instead. |
| **Design-doc gate** | Rule: no code generation/merge/ship for a workflow until its SDD is Approved by dual review. Main-line merge still needs human approval of that readiness—not a line-by-line code review. |
| **DigitalTraveler** | State object that carries a unit of work through factory departments and statuses. |
| **Department** | Factory stage with a clear responsibility: assembly, quality, or packaging (extensible later). |
| **SDD** | Software Design Document under `docs/design/`. |

---

## 13. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-15 | Marcos Blazquez + New Bot | Initial Draft for ideation pack |
| 2026-09-15 | Clark Bot | Agent review amendments: open graphs (DES-0001-C), TDD/BDD (DES-0001-D), REQ-0004; dual review → **Approved** |

## 14. Dual-review record

### Human (Marcos Blazquez) — 2026-09-15

- Verdict: **Approve** architecture / roles / non-goals (“looks good; ready for dual review”).
- Merge-gate understanding: human merge = design-doc readiness, not code walkthrough.

### Agent (Clark Bot) — 2026-09-15

Checklist:

| Check | Result |
|---|---|
| Problem / goals / non-goals coherent | Pass |
| Dual-review + merge gate consistent with workflow doc | Pass |
| Traceability IDs present; TEST deferred clearly | Pass |
| Scope does not smuggle engine implementation | Pass |
| Open questions deferred vs blocking | Pass (all deferred) |
| Gaps found vs later product guidance | Amended in-doc: open-ended graphs, TDD/BDD-style not Cucumber, testing-layer TBD, code-review avoidance as one capability |
| Readable future-code / hexagonal intent aligned | Pass (directional) |

**Agent verdict:** **Approve** (with amendments above incorporated).

**Joint result:** Status → **Approved**. Does **not** authorize factory engine code; dedicated engine SDD still required.
