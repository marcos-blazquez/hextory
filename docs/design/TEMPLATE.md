# Software Design Document (SDD) Template

> Copy this file to `docs/design/NNNN-slug.md`. Replace bracketed guidance with real content. Do not leave sections empty—write `N/A` with a one-line reason if a section does not apply.

| Field | Value |
|---|---|
| **Doc ID** | DES-NNNN |
| **Title** | [Short descriptive title] |
| **Status** | Draft \| In Review \| Changes Requested \| Approved \| Superseded |
| **Authors** | [Human and/or agent names] |
| **Reviewers (human)** | [Names] |
| **Reviewers (agent)** | [Agent IDs / names] |
| **Created** | YYYY-MM-DD |
| **Last updated** | YYYY-MM-DD |
| **Related REQs** | REQ-… |
| **Supersedes** | [Doc ID or none] |

---

## 1. Introduction / overview

### 1.1 Problem statement

[What pain or opportunity does this workflow address? Who feels it?]

### 1.2 Goals

- G1: …
- G2: …

### 1.3 Success definition

[How will we know this design (and later implementation) succeeded?]

### 1.4 Scope

**In scope:** …

**Out of scope:** see Explicit non-goals below.

---

## 2. System architecture

### 2.1 Context

[Where this workflow sits in Hextory / the factory. Who calls it; what it calls.]

```
[Visual placeholder: context diagram]
Actors → Gateway → Departments → Adapters → External systems
```

### 2.2 Architectural style

[e.g. hexagonal / ports & adapters; which ports this workflow owns]

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| … | … | assembly / quality / packaging / n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| DES-… | … | … | … |

---

## 3. Data design

### 3.1 Entities / state

[DigitalTraveler fields touched, new state machines, persisted records]

| Entity | Key fields | Lifecycle |
|---|---|---|
| … | … | … |

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
```

### 3.3 Persistence & retention

[Where stored; TTL; PII concerns]

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| … | CLI / HTTP / event | … | … |

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| … | … | … |

### 4.3 Events / messages

[Topics, payloads, idempotency]

---

## 5. Component design

### 5.1 Core (pure) logic

[What lives in `src/` with no I/O? Pure functions / domain services.]

### 5.2 Adapters

[AWS / on-prem / local adapters this workflow needs]

### 5.3 Algorithms & policies

[Non-trivial rules, scoring, routing, retry]

---

## 6. UI (if any)

[Screens, CLI UX, or **N/A — no UI**; this workflow is API/CLI/agent-only.]

```
[Visual placeholder: wireframe or CLI transcript]
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-… | … | … | … |

---

## 8. Explicit non-goals

List what this workflow will **not** do (even if requested later without a new SDD):

- NG1: …
- NG2: …

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement only after gate criteria (below) are green.

| ID | Criterion | Verification method |
|---|---|---|
| AC-… | … | TEST-… / manual / metric |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| … | … | … | Quality FAIL → … |

**Rework policy defaults (override only with justification):**

- Quality department **FAIL** returns the DigitalTraveler to the owning assembly step with a structured defect report.
- Max rework attempts before human escalation: [N].
- Partial ships are forbidden unless explicitly allowed here.

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
| REQ-… | … | DES-… | TEST-… | |

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

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| … | … |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| Q-… | … | … | … | |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| YYYY-MM-DD | … | Initial draft |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — leave diagram placeholders until real diagrams land; never omit the slot if structure is non-trivial.
- **Consistency** — same names for the same components across SDDs.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; link from README / scorecard as needed.
- **Collaboration** — dual review is mandatory; record dissent in open questions or changes-requested notes.
- **Future growth** — design for new adapters/departments without rewriting the core contract.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Failing test before production code for core behavior |
| BDD-style | Readable Given/When/Then (or equivalent) in normal test modules — **not Cucumber** unless a future SDD explicitly adopts it |
| Testing layer | Name where enforcement lives (path TBD project-wide until engine SDD decides) |
| Traceability | Link TEST-* IDs to REQ-* / DES-* |

