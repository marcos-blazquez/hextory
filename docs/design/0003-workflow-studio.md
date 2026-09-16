# DES-0003 — Hextory Studio (managed workflow canvas) — ideation

| Field | Value |
|---|---|
| **Doc ID** | DES-0003 |
| **Title** | Hextory Studio — managed dark-factory workflow canvas |
| **Status** | **Draft** |
| **Authors** | Marcos Blazquez + Clark Bot |
| **Reviewers (human)** | TBD |
| **Reviewers (agent)** | TBD |
| **Created** | 2026-09-15 |
| **Last updated** | 2026-09-15 |
| **Related REQs** | REQ-0001, REQ-0002, REQ-0003, REQ-0004, REQ-0010, REQ-0011 (plus future UI REQs below) |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**) |
| **Implementation** | **Out of scope for current Hextory slice** — refine here until a later dual review Approves a build plan |

---

## 0. Document posture

This SDD is an **ideation and refinement** vehicle for a Twilio Studio–style managed authoring/ops experience aimed at Hextory’s dark factory. It captures product intent, boundaries, and open questions so we can iterate without writing React, xyflow, or `adapters/web` code yet.

**Hard rules already agreed (must survive into any future build):**

1. Architecture rules and Gatekeeper policy live in `src/` — the UI must not re-implement hexagonal boundaries or become a second engine.
2. Canvas edits produce or update a **workflow definition** (and ideally a Draft SDD / patch). **Approved** status is required before `run`.
3. Visualization of Approved graphs and live runs is safer than freehand “draw and ship.”
4. Deploy-target / adapter selection in the UI is **profile wiring only** (local | on-prem | AWS), not a fork of department logic.

---

## 1. Introduction / overview

### 1.1 Problem statement

The factory engine (DES-0002) already defines open-ended graphs, Gatekeeper, DigitalTraveler, and a local CLI. Authoring and operating those graphs as JSON/YAML alone will not scale for humans who must:

- Design and dual-review workflow topology before implementation.
- See traveler progress, rework loops, and escalations without reading logs.
- Manage versions, publish/approve gates, and choose which adapter stack a run binds to.

Operators of comparable systems (e.g. **Twilio Studio**) get a **fully managed** visual flow builder: drag nodes, wire transitions, configure widgets, publish versions, test, and observe executions — without owning the underlying orchestration substrate.

Hextory needs the **same class of experience**, remapped to dark-factory semantics: design-doc gate, Approved-before-run, hexagonal multi-target adapters, and agent-first implementation after approval.

### 1.2 Analogy map (Twilio Studio → Hextory Studio)

| Twilio Studio concept | Hextory Studio counterpart |
|---|---|
| Flow | Workflow definition (`workflow_id` + graph) linked to an SDD |
| Widget / Step | Department node or registered custom node (assembly, quality, packaging, …) |
| Transition / connector | Graph edge (pass / fail / rework / escalate / ship / deny) |
| Flow variables | Traveler `payload` + typed ports (no secrets in canvas defaults) |
| Publish | Promote Draft → dual review → **Approved** SDD + immutable workflow version |
| Test / Trigger | Dry-run / simulate against fakes; real `run` only if Gatekeeper allows |
| Execution log | DigitalTraveler `routing_history`, quality reports, audit |
| Subflow | Nested / reusable subgraph registered in the open-ended registry |
| Studio is managed SaaS | **Managed Studio product** (hosting, auth, versioning, collaboration) — exact deploy home TBD |

The analogy is **product UX and lifecycle**, not a copy of Twilio’s telephony widgets or Twilio’s cloud.

### 1.3 Goals

- **G1 (REQ-UI-01):** Specify a managed Studio experience for visualize / create / edit / version workflow graphs.
- **G2 (REQ-UI-02):** Keep Studio subordinate to DES-0001/0002: no run without Approved SDD; core remains authority.
- **G3 (REQ-UI-03):** Define “fully managed” meaning for Hextory (auth, hosting, collaboration, publish pipeline) without locking AWS vs on-prem Studio hosting yet.
- **G4 (REQ-UI-04):** Map canvas actions to workflow definition + Draft SDD artifacts suitable for dual review.
- **G5 (REQ-UI-05):** Support live-run and historical traveler visualization (read models) without mutating engine policy in the browser.
- **G6 (REQ-UI-06):** Allow selecting active adapter profile (local / on-prem / AWS) as binding metadata only.
- **G7:** Prefer stack direction for a future build: React + xyflow canvas + shadcn/ui (Marcos lifetime shadcn.io license / MCP ready) — **directional, not mandated until Approval**.

### 1.4 Success definition (ideation phase)

- Dual review can Approve, request changes, or park this SDD without touching the DES-0002 first-slice backlog.
- Open questions (§14) are listed with owners; no silent assumptions about “Studio writes Approved.”
- A future implementation SDD (or amendment) can slice MVP (read-only canvas → edit Draft → publish gate → live overlay) without re-litigating boundaries.

### 1.5 Scope

**In scope (this Draft):** product vision, UX flows, lifecycle, data contracts at a conceptual level, architecture placement (`adapters/web` or sibling app), non-goals, risks, open questions.

**Out of scope (this Draft and current Hextory implementation):**

- Any React / xyflow / shadcn code, CI for UI, production hosting.
- Changing DES-0002 package layout or Gatekeeper rules.
- Replacing the design-doc gate with “publish in Studio = Approved.”

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: Studio context]
Human designer / dual reviewer / operator
        │
        ▼
Hextory Studio (managed UI — ideation)
  · Canvas (xyflow) · Inspector · Versioning · Run console
        │  HTTPS / events (future)
        ▼
RequestGateway + ports  ←── ONLY authority for allow/deny/run
        │
        ▼
src/ graphs · policies · departments
        │
        ▼
adapters: local | on-prem | AWS   ← profile selected in Studio, executed in adapters
```

Studio is a **client + managed control plane** over the engine. It never bypasses Gatekeeper.

### 2.2 Architectural style

- **Hexagonal:** Studio lives outside `src/` (e.g. `adapters/web` or a separate `apps/studio` talking to the same HTTP/CLI-facing facade later).
- **CQRS-ish split (directional):** commands that mutate workflow drafts / request review; queries that project traveler state onto the canvas.
- **Source of truth:** Approved SDD + versioned workflow definition in factory storage — not the React state tree.

### 2.3 High-level components (conceptual)

| Component | Responsibility | Notes |
|---|---|---|
| Canvas | Render/edit nodes & edges (xyflow) | Custom node types per department / registry |
| Node palette | Catalog from graph registry + Approved node kinds | Open-ended: custom nodes appear when registered |
| Inspector | Edit node config, edge conditions, workflow metadata | Validates against schemas published by core |
| Lifecycle panel | Draft → In Review → Approved / Changes Requested | Mirrors SDD status; may open SDD diff |
| Adapter profile picker | Select local / on-prem / AWS binding for a run or env | Does not fork departments |
| Run console | Start (if Allowed), status, routing_history tail, escalate view | Calls gateway; shows structured denials |
| Collaboration (managed) | Auth, sharing, comments on Draft graphs | Twilio Studio–like multi-user later |
| Artifact bridge | Export/import workflow JSON; generate Draft SDD stubs / patches | Keeps design-doc gate honest |

### 2.4 Design decisions (proposed)

| ID | Decision | Alternatives | Rationale |
|---|---|---|---|
| **DES-0003-A** | Studio is managed product UX; engine remains DES-0002 core | Embed policy in browser; Studio-only runtime | Preserves dark-factory gate and multi-target parity |
| **DES-0003-B** | Canvas → workflow definition + Draft SDD artifacts; run requires Approved | Draw-and-run; Studio status overrides SDD | Aligns with DES-0001 / Gatekeeper |
| **DES-0003-C** | Read-only visualization of Approved + live travelers before full edit MVP | Full editor first | Lower risk; proves value faster when we build |
| **DES-0003-D** | Directional UI stack: React + xyflow + shadcn/ui | Vue Flow; custom canvas; no component system | Fit for graphs; Marcos shadcn lifetime license ready |
| **DES-0003-E** | Adapter profile is run/env metadata, not a second architecture | Separate graphs per cloud | Hexagonal: one graph, many adapters |
| **DES-0003-F** | “Fully managed” = hosted Studio control plane (auth, versions, collab) with pluggable engine backends | Self-host-only IDE plugin | Matches Twilio Studio expectation; engine still multi-target |

---

## 3. Data design (conceptual)

### 3.1 Entities

| Entity | Key fields | Lifecycle |
|---|---|---|
| StudioProject | `project_id`, name, members | Created in managed Studio |
| WorkflowDraft | `workflow_id`, graph JSON, `sdd_id`, version, status | editable → submitted for review |
| WorkflowRelease | immutable graph snapshot + `sdd_id` Approved | runnable via Gatekeeper |
| CanvasLayout | positions, groups (presentation only) | may diverge from pure graph semantics |
| RunView | traveler_id, projected node highlights | derived from DigitalTraveler |
| AdapterProfile | `local` \| `onprem` \| `aws` (+ config refs) | selected per env/run |

### 3.2 Graph contract (must stay engine-owned)

Studio edits a **WorkflowDefinition** compatible with DES-0002 registry:

- `workflow_id`, `sdd_id`, `nodes[]`, `edges[]`, optional `max_rework`, metadata.
- Presentation layout is additive and **must not** be required for the engine to execute.
- Unknown node types: Studio may show placeholders; Gatekeeper/registry still decide executability.

### 3.3 Draft SDD bridge

When a designer saves a meaningful graph change, Studio should (directional):

1. Update WorkflowDraft.
2. Offer / auto-generate a **Draft SDD section or patch** (topology, ACs touched, adapter profile assumptions).
3. Require dual review path already defined in DES-0001 before status becomes Approved.
4. Only then expose **Run** as enabled (Gatekeeper still re-checks at runtime).

---

## 4. Interface design (future)

### 4.1 Inbound (users)

| Surface | Purpose |
|---|---|
| Studio web app | Author, review, observe |
| Deep links from SDD | Open graph for `sdd_id` / `workflow_id` |
| Embeds (later) | Read-only graph in docs portal |

### 4.2 Outbound (to engine)

| Call | Semantics |
|---|---|
| List/get workflow definitions | Query |
| Save WorkflowDraft | Command (no run) |
| Submit for review / attach review record | Process |
| `run` / `status` / `resume` | Same as CLI — via gateway |
| Resolve SDD status | Same SddStatusReader contract (fail closed) |

### 4.3 Events (directional)

`draft.saved`, `review.requested`, `workflow.approved` (mirrors SDD), `run.accepted|denied`, `node.completed`, `run.escalated|shipped` — for live canvas overlays.

---

## 5. UX flows (ideation)

### 5.1 Author a new workflow (Studio-like)

1. Create WorkflowDraft from template (starter assembly→quality→packaging) or blank registry.
2. Drag nodes from palette; wire pass/fail/rework edges.
3. Configure inspector fields (criteria ids, max_rework override with justification).
4. Save → generate/update Draft SDD patch.
5. Submit dual review — **Run stays disabled**.

### 5.2 Approve and run

1. Human + agent Approve linked SDD (existing process).
2. Studio shows Approved badge; creates WorkflowRelease snapshot.
3. Operator picks AdapterProfile; clicks Run.
4. Gatekeeper denies or accepts; canvas animates routing_history.

### 5.3 Rework / escalate visibility

- FAIL edge highlight; `rework_count/max_rework` badge; escalate terminal state styled distinctly.
- DefectReport summary in inspector (read-only from traveler).

### 5.4 Open-ended extension

- Registering a new node kind (via Approved SDD + registry) makes it appear in the palette without shipping a Studio core fork — palette is registry-driven.

---

## 6. “Fully managed” definition (Hextory)

For this ideation, **fully managed** means operators should not assemble the authoring stack themselves to get value:

| Concern | Managed expectation | Open |
|---|---|---|
| Hosting | Studio URL provided / hosted control plane | Who hosts (Hextory cloud vs customer VPC) — Q-UI-1 |
| Auth | Accounts, roles (designer, reviewer, operator) | SSO — Q-UI-2 |
| Versioning | Drafts, releases, rollback of graph snapshots | Retention — Q-UI-3 |
| Collaboration | Comments, review requests, presence (later) | Realtime stack — Q-UI-4 |
| Engine binding | Point Studio at local / on-prem / AWS engine endpoints | Multi-tenant — Q-UI-5 |
| Compliance | No secrets in canvas; audit of publishes | PII in traveler projections — Q-UI-6 |

**Non-managed:** the factory **engine** itself remains hexagonal and multi-target per DES-0002 — Studio manages the **experience**, not a single lock-in runtime.

---

## 7. Assumptions and dependencies

| ID | Assumption | Risk if wrong | Mitigation |
|---|---|---|---|
| A-01 | DES-0002 registry + traveler APIs will be exposable over HTTP | Studio blocked on CLI-only | Plan thin facade in a future SDD |
| A-02 | xyflow + shadcn suffice for Studio-class UX | Canvas limits | Spike later under Approved build SDD |
| A-03 | Designers accept SDD dual review instead of Studio-only publish | Process friction | UX must make Draft→Approved the happy path |
| A-04 | Layout can be non-semantic | Layout-breaking merges | Keep layout separate from executable graph |
| A-05 | “Managed” can ship after local engine maturity | Premature SaaS | Keep this doc ideation until engine slice is solid |

---

## 8. Explicit non-goals

- **NG1:** Implementing Studio in the current Hextory first-slice backlog.
- **NG2:** Browser-side Gatekeeper or “soft allow” on read errors.
- **NG3:** Replacing SDDs with canvas screenshots as the approval artifact.
- **NG4:** Forking department logic per adapter profile in the UI.
- **NG5:** Cloning Twilio’s telephony widget catalog.
- **NG6:** Requiring Cucumber or any BDD toolchain for UI tests (when built: ordinary tests + BDD-style narrative where useful).
- **NG7:** Making Studio the only way to run the factory (CLI/API remain first-class).

---

## 9. Acceptance criteria (for a *future* implementation SDD)

These are **not** build tickets today. They define what “done” would mean when implementation is authorized.

| ID | Criterion |
|---|---|
| AC-UI-01 | Studio cannot start a run when SDD is not Approved (server-enforced). |
| AC-UI-02 | Saving a graph updates WorkflowDraft; executable release requires Approved link. |
| AC-UI-03 | Canvas can render starter + custom registry nodes without editing Studio core. |
| AC-UI-04 | Live run view projects routing_history onto nodes/edges. |
| AC-UI-05 | Adapter profile selection changes binding only; same workflow_id executes. |
| AC-UI-06 | No `src/` imports from Studio app; Studio uses public facade/ports only. |
| AC-UI-07 | Export produces workflow JSON (+ optional Draft SDD patch) suitable for dual review. |

---

## 10. Failure modes (product)

| Failure | Detection | Response |
|---|---|---|
| Designer expects draw-and-ship | Run disabled + copy explaining Gatekeeper | Education in UX; docs |
| Stale Draft vs Approved SDD | Version mismatch banner | Block run; prompt re-review |
| Layout-only change marked as release | Diff shows no semantic graph change | Allow layout publish without new SDD if policy says so (Q-UI-7) |
| Engine deny | Structured denial in run console | Do not fake success on canvas |
| Registry unknown node | Placeholder + non-runnable badge | Require SDD/registry update |

---

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Studio becomes shadow engine | Gate bypass, architecture drift | DES-0003-A/B; reviews reject browser policy |
| Premature UI vs engine depth | Maturity stall | Keep implementation unauthorized until engine APIs ready |
| Managed hosting scope creep | Endless SaaS build | Slice: self-hosted Studio MVP before full multi-tenant |
| Over-fidelity to Twilio | Wrong domain widgets | Stick to factory node kinds |

---

## 12. Traceability (seed)

| REQ ID | Description | DES |
|---|---|---|
| REQ-0001 | Design-doc gate | DES-0003-B |
| REQ-0004 / REQ-0011 | Open-ended graphs | DES-0003 palette/registry |
| REQ-0010 | Hexagonal core | DES-0003-A, AC-UI-06 |
| REQ-UI-01…06 | Studio goals §1.3 | this Draft |

---

## 13. Gate criteria (this ideation doc)

| Gate | Status |
|---|---|
| Dual review of product boundaries (human + agent) | ☐ Pending |
| Agreement that implementation stays unauthorized | ☑ Stated in §0 |
| Engine first-slice APIs sufficient for MVP Studio | ☐ Not yet (CLI-only today) |
| Hosting model chosen (Q-UI-1) | ☐ Open |

**Implementation of Studio code is forbidden until this SDD (or a dedicated build SDD) is Approved and DES-0002 runtime facade needs are met.**

---

## 14. Open questions

| ID | Question | Suggested owner |
|---|---|---|
| Q-UI-1 | Host Studio as Hextory-managed SaaS, customer-VPC, or both? | Marcos |
| Q-UI-2 | Auth: local accounts vs SSO first? | Marcos |
| Q-UI-3 | Retention of drafts/releases/run projections | Marcos |
| Q-UI-4 | Realtime collaboration priority vs single-editor MVP | Marcos |
| Q-UI-5 | Multi-engine binding (one Studio → many factory backends)? | Marcos + Clark Bot |
| Q-UI-6 | How much traveler payload is safe to project in UI? | Marcos |
| Q-UI-7 | Do layout-only changes require SDD amendment? | Dual review |
| Q-UI-8 | MVP order: read-only Approved view → Draft editor → managed hosting? | Marcos (recommend yes) |
| Q-UI-9 | Sibling `apps/studio` vs `adapters/web` package home? | Future build SDD |
| Q-UI-10 | Name: “Hextory Studio” vs other product name? | Marcos |

---

## 15. Recommended refinement next steps (still no code)

1. Answer Q-UI-1, Q-UI-8, Q-UI-10 in a short review pass.
2. Sketch 3–5 wireframe panels (palette, canvas, inspector, lifecycle, run console) — optional images later.
3. Define minimal WorkflowDraft JSON schema aligned with DES-0002 registry (doc-only).
4. When DES-0002 exposes a stable HTTP/status facade, open a **build** SDD (or Promote this doc) for dual review before any React work.
5. Keep shadcn MCP + xyflow notes as directional stack only.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| Hextory Studio | Proposed managed visual authoring/ops product for factory workflows |
| WorkflowDraft | Editable graph + metadata not yet runnable |
| WorkflowRelease | Immutable graph snapshot tied to Approved SDD |
| Adapter profile | Binding choice among local / on-prem / AWS adapters |
| Fully managed | Hosted Studio experience (auth, versions, collab) without DIY authoring stack |

---

## 17. Changelog

| Date | Change |
|---|---|
| 2026-09-15 | Initial Draft ideation: Twilio Studio–like managed canvas for dark factory; out of current implementation scope |
