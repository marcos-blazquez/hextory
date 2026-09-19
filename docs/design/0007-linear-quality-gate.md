# DES-0007 — Linear quality gate workflow

| Field | Value |
|---|---|
| **Doc ID** | DES-0007 |
| **Title** | Linear quality gate workflow (`linear_quality_gate`) |
| **Status** | Draft |
| **Authors** | Cursor Cloud Agent (draft) |
| **Reviewers (human)** | TBD — Marcos Blazquez (dual review not completed in this agent turn) |
| **Reviewers (agent)** | TBD — Clark Bot (dual review not completed in this agent turn) |
| **Created** | 2026-09-19 |
| **Last updated** | 2026-09-19 |
| **Related REQs** | REQ-0011 (open-ended registry); REQ-0012 (traveler); REQ-0013 (gateway/gatekeeper); REQ-0014 (quality outcomes); proposed **REQ-0019** (second concrete workflow beyond starter) |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**) |
| **Implementation** | **Not authorized** while Status is Draft — register/run only after dual Approve + §13 green |

---

## 0. Document posture

This SDD is a **thin Draft** for a second concrete factory workflow beyond the in-tree `starter_factory` topology (assembly → quality → packaging with rework). Maturity pulses repeatedly flag **thin Approved *workflow* SDD coverage**: DES-0001/0002/0004/0005/0006 are platform/adapter/obs SDDs; they do not dual-review a second runnable workflow graph.

**Why Draft (not Approved):** dual human + agent review is mandatory (DES-0001 / design-doc-review). This agent turn can author the Draft and record agent checklist intent, but cannot substitute Marcos Blazquez + Clark Bot dual Approve. **Do not treat this document as an implementation gate.**

**Hard rules (must survive into any future build):**

1. Reuse DES-0002 departments, traveler contract (`hextory.digital_traveler@0.1`), Gatekeeper, and GraphRegistry — do not fork Gatekeeper or invent a parallel engine.
2. Register a **new** `workflow_id` (`linear_quality_gate`); do not collapse this into `starter_factory`.
3. Public kernel stays consumer-agnostic: no private sibling product names in this SDD or its tests.
4. Adapters (local / on-prem / AWS) bind the same workflow semantics; no deploy-target fork of department logic.
5. No real AWS account deploy from CI (DES-0005 NG1 remains).

---

## 1. Introduction / overview

### 1.1 Problem statement

The factory engine (DES-0002) proves open-ended graphs via registry, but the only first-slice concrete topology in tree is `starter_factory` (assembly → quality → packaging with FAIL→rework). Operators and maturity scoring need a **second Approved workflow SDD** that:

- Demonstrates a different topology (linear, no rework loop).
- Is thin enough to dual-review quickly.
- Is implementable later as a registry registration + tests without redesigning core.

Without a second workflow SDD, aspect **2** (design-doc coverage) stays capped on platform SDDs alone.

### 1.2 Goals

- **G1 (REQ-0019 / REQ-0011):** Specify `linear_quality_gate` as a registered workflow distinct from `starter_factory`.
- **G2:** Linear path: **intake → quality → packaging → shipped**, with **no rework edge** (quality FAIL → escalate).
- **G3:** Reuse existing department node ids / pure functions where possible; prefer composition over new departments.
- **G4:** Gatekeeper still refuses runs when this SDD is not **Approved**.
- **G5:** TEST-LQG-* plan so post-Approval TDD is unambiguous.

### 1.3 Success definition

- Dual review Approves (or requests changes) without re-litigating DES-0002 ports.
- After Approval, agents can register `linear_quality_gate` and prove PASS→shipped and FAIL→escalated with ordinary pytest (no Cucumber).
- Maturity pulses can cite a second workflow SDD (Draft now; Approved after dual review).

### 1.4 Scope

**In scope:**

- Workflow id, topology, edges, failure/escalate policy for `linear_quality_gate`.
- Design decisions, acceptance criteria, TEST ID plan, gate criteria.
- Traceability to REQ-0011 / proposed REQ-0019.

**Out of scope:** see Explicit non-goals (§8). No implementation while Draft.

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
CLI / HTTP client
        │
        ▼
RequestGateway + Gatekeeper ──refuse if DES-0007 not Approved──► denial
        │ allow
        ▼
GraphRegistry[linear_quality_gate]
        │
        ├── intake (assembly node or thin alias) ──► quality ──PASS──► packaging ──► shipped
        │                                    │
        │                                    └── FAIL ──► escalated (terminal; no rework)
        └── (no FAIL→intake edge)
```

**Who calls it:** same gateway / CLI / on-prem / AWS run surfaces as `starter_factory`.  
**What it calls:** existing department runnables + GraphRunner; no new adapter stack.

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). This SDD owns only the **workflow definition** (nodes/edges/policy overrides for this graph). Engine, traveler schema, and adapters remain DES-0002 / DES-0004 / DES-0005.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| `linear_quality_gate` WorkflowDefinition | Registry entry: entry node, edges, `sdd_id=DES-0007` | n/a |
| Intake node | Prepare traveler payload for quality (reuse assembly or thin wrapper) | assembly (reuse) |
| Quality node | PASS / FAIL evaluation (existing `run_quality`) | quality |
| Packaging node | Ship on PASS (existing `run_packaging`) | packaging |
| Escalate path | On FAIL: terminal escalated — **no** rework edge | n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0007-A** | `workflow_id` = `linear_quality_gate` | Reuse `starter_factory`; unnamed second graph | Distinct registry key proves open-ended catalogs (REQ-0011) |
| **DES-0007-B** | Topology: intake → quality → packaging; FAIL → escalate | Keep FAIL→rework like starter; quality-only single node | Differentiates second workflow; “linear” = no rework loop |
| **DES-0007-C** | Reuse DES-0002 department callables; no new core departments in first slice | New `intake` department package | Thin SDD; faster dual review; less surface area |
| **DES-0007-D** | Max rework for this workflow = **0** (escalate on first FAIL) | Inherit global max 3 | Linear gate semantics; starter keeps default 3 |
| **DES-0007-E** | Implementation deferred until Approved | Soft-allow Draft runs | Hard rule: Draft ≠ runnable production posture |

---

## 3. Data design

### 3.1 Entities / state

| Entity | Key fields | Lifecycle |
|---|---|---|
| DigitalTraveler | unchanged DES-0002-G / `hextory.digital_traveler@0.1` | created → routed → shipped / escalated / denied |
| WorkflowDefinition | `workflow_id=linear_quality_gate`, `sdd_id=DES-0007`, nodes[], edges[] | registered after Approval; immutable for a run version |
| QualityReport | existing | attached on quality PASS/FAIL |

No traveler schema change.

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
RunRequest(sdd_id=DES-0007, workflow_id=linear_quality_gate, payload)
  → Gatekeeper(Approved?)
  → intake mutates payload (assembled / criteria inputs)
  → quality decides PASS|FAIL
       PASS → packaging → status=shipped
       FAIL → status=escalated (+ defect report); stop
```

### 3.3 Persistence & retention

Same checkpointer ports as DES-0002 / adapter SDDs. No new stores. No PII requirements beyond existing traveler rules.

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| Local CLI | CLI | n/a (local) | `run --sdd DES-0007 --workflow linear_quality_gate …` after Approval |
| On-prem / AWS HTTP | HTTP JSON | per adapter SDD | Same `sdd_id` + `workflow_id` body fields as starter runs |

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| Gatekeeper | Refuse non-Approved DES-0007 | Structured denial; no graph entry |
| GraphRegistry | Resolve `linear_quality_gate` | Unknown workflow → deny at gateway |
| Department runnables | Execute nodes | Quality FAIL → escalate (this workflow) |

### 4.3 Events / messages

Reuse DES-0002 run lifecycle events (`run.accepted`, terminal status). No new topics required for first slice.

---

## 5. Component design

### 5.1 Core (pure) logic

- `build_linear_quality_gate_definition(...)` (proposed under `src/graphs/`) returning `WorkflowDefinition`.
- Edges: intake→quality; quality PASS→packaging; quality FAIL→**no** rework target (runner marks escalated per DES-0007-D).
- Pure: no I/O, no adapter imports.

### 5.2 Adapters

No new adapters. Local/on-prem/AWS register the workflow the same way they register `starter_factory` today (wiring-only).

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Entry | `intake` (assembly reusable) |
| PASS | quality → packaging → shipped |
| FAIL | escalate immediately; `rework_count` stays 0; no return to intake |
| Draft runs | Gatekeeper deny when status ≠ Approved |

---

## 6. UI (if any)

**N/A — no UI.** API/CLI/agent-only. DES-0003 Studio remains Draft ideation and must not be implemented here.

```
[Visual placeholder: CLI transcript]
$ hextory run --sdd DES-0007 --workflow linear_quality_gate --force-quality PASS
# → shipped (post-Approval)

$ hextory run --sdd DES-0007 --workflow linear_quality_gate --force-quality FAIL
# → escalated (post-approval; no rework loop)
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-1 | DES-0002 GraphRunner can express escalate-without-rework edges | Runner assumes rework always | Confirm/extend runner policy in impl slice; keep test first |
| A-2 | Reusing assembly as “intake” is acceptable naming | Confusion with starter | Document alias in registry metadata / node notes |
| A-3 | Dual review will occur before any code merge for this workflow | Agents implement from Draft | Gatekeeper + CONTRIBUTING + PR template block Draft impl |

---

## 8. Explicit non-goals

- **NG1:** No Gatekeeper fork / soft-allow on Draft DES-0007.
- **NG2:** No traveler schema change; no new published contract version.
- **NG3:** No Studio / canvas / web UI (DES-0003).
- **NG4:** No real AWS deploy in the implementation PR or CI.
- **NG5:** No replacement of `starter_factory`; both workflows remain valid.
- **NG6:** No private product names or consumer-specific departments in public kernel.
- **NG7:** No Cucumber / Gherkin toolchain.

---

## 9. Acceptance criteria for agent implementation

Concrete only after Status is **Approved** and §13 is green.

| ID | Criterion | Verification method |
|---|---|---|
| AC-LQG-01 | `linear_quality_gate` registered and distinct from `starter_factory` | TEST-LQG-01 |
| AC-LQG-02 | Gatekeeper denies run when DES-0007 is Draft / missing / ERROR | TEST-LQG-02 |
| AC-LQG-03 | After Approval: PASS path ends `shipped` with packaging in `routing_history` | TEST-LQG-03 |
| AC-LQG-04 | After Approval: FAIL path ends `escalated` with **no** rework return to intake | TEST-LQG-04 |
| AC-LQG-05 | `src/` gains no `adapters/` or `langgraph` imports | TEST-0010 (existing) + review |
| AC-LQG-06 | Behavior tests use Given/When/Then style in ordinary pytest | TEST-LQG-05 |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Gate deny (non-Approved) | Gatekeeper | Structured denial | None — fix SDD status via dual review |
| Quality FAIL | Quality department | Escalate | **None** (DES-0007-D) |
| Unknown workflow_id | Registry | Deny at gateway | Register after Approval |
| Adapter / checkpointer fault | Adapter | Surface error; no silent ship | Per adapter SDD |

**Rework policy override for this workflow:** max rework attempts = **0**. First quality FAIL escalates. Do not inherit starter’s max 3 for this `workflow_id`.

---

## 11. Human + agent review checklist

Reviewers must check each item. Architecture-critical items require **human** sign-off.

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☐ | ☐ | Yes |
| 2 | Architecture fits hexagonal / factory rules | ☐ | ☐ | Yes |
| 3 | Interfaces and failure modes are specified | ☐ | ☐ | Yes |
| 4 | Acceptance criteria are testable | ☐ | ☐ | Yes |
| 5 | Traceability IDs are complete and unique | ☐ | ☐ | Yes |
| 6 | Gate criteria are unambiguous | ☐ | ☐ | Yes |
| 7 | Security / privacy / compliance touched? | ☐ | ☐ | If yes → Yes |
| 8 | Glossary terms used consistently | ☐ | ☐ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☐ | ☐ | No |
| 10 | No implementation leakage that bypasses this SDD | ☐ | ☐ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | | | Approve / Changes requested |
| Agent reviewer | | | Approve / Changes requested |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| REQ-0011 | Open-ended graph/registry | DES-0002-C, DES-0007-A | TEST-LQG-01 | |
| REQ-0012 | DigitalTraveler unchanged | DES-0002-G, DES-0007 | TEST-LQG-03/04 | |
| REQ-0013 | Gateway + Gatekeeper | DES-0002-I, DES-0007-E | TEST-LQG-02 | |
| REQ-0014 | Quality outcomes (escalation variant) | DES-0007-B/D | TEST-LQG-04 | |
| REQ-0019 (proposed) | Second concrete workflow beyond starter | DES-0007 | TEST-LQG-01…05 | |

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
- [ ] `config/sdd_status.json` lists `"DES-0007": "Approved"` matching the Status cell.

**Only when every box is checked may agents generate implementation for this workflow.**

**Current state:** Status is **Draft** — §13 is **not** green. No implementation authorized.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **Linear quality gate** | Workflow with a single forward quality decision and no FAIL→intake rework edge |
| **`linear_quality_gate`** | Registry `workflow_id` for this SDD |
| **Intake** | First node; may reuse assembly callable |
| **Escalate-on-FAIL** | First quality FAIL ends the run as escalated |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) and [0002-factory-engine.md](0002-factory-engine.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-LQG-1** | Confirm intake = reuse `assembly` node id vs introduce `intake` alias id | Dual review | Before Approval | Open — proposed interim: reuse `assembly` callable with entry notes “intake” |
| **Q-LQG-2** | Should FAIL attach the same DefectReport shape as starter? | Dual review | Before Approval | Open — proposed interim: yes, reuse QualityReport / DefectReport |
| Q-LQG-3 | Register automatically in local CLI default registry after Approval? | Implementer | During first impl slice | Soft — yes for discoverability |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-19 | Cursor Cloud Agent | Initial **Draft**: second workflow SDD (`linear_quality_gate`); dual review pending; no Approval claimed |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same names as DES-0002 for gateway, traveler, gatekeeper.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions or changes-requested notes.
- **Future growth** — additional workflows get new DES ids; do not overload this SDD.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Failing test before production registration/runner wiring |
| BDD-style | Readable Given/When/Then in ordinary pytest — **not Cucumber** |
| Testing layer | `tests/unit/` + `tests/behavior/` (DES-0002-E) |
| Traceability | Link TEST-LQG-* to REQ-0011 / REQ-0019 / DES-0007-* |

### Planned TEST IDs (post-Approval)

| TEST ID | Intent |
|---|---|
| TEST-LQG-01 | Registry contains `linear_quality_gate` distinct from `starter_factory` |
| TEST-LQG-02 | Non-Approved DES-0007 → Gatekeeper denial |
| TEST-LQG-03 | Approved + force PASS → shipped |
| TEST-LQG-04 | Approved + force FAIL → escalated; routing_history has no rework return |
| TEST-LQG-05 | Behavior module uses Given/When/Then structure |

### First implementation slice (authorized only after Approval)

§13 is **not** green yet. After dual Approve, a follow-up PR may:

1. Add `src/graphs/linear_quality_gate.py` (or equivalent) + registry wiring.
2. Add TEST-LQG-01…05.
3. Document CLI example in README / adapter READMEs.
4. Do **not** change traveler schema; do **not** implement Studio; do **not** deploy AWS from CI.

---

## Review records

**None yet.** Dual review (Marcos Blazquez + Clark Bot) is required before Status may move to **Approved**. This Draft intentionally does not add a fake agent-review file under `docs/design/reviews/`.
