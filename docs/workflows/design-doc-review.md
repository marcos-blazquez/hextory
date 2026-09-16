# Design-doc review workflow

This workflow is the **only** path from idea to shippable implementation in Hextory. It enforces the design-doc-over-code-review principle.

**Related:** [SDD template](../design/TEMPLATE.md) · [Vision DES-0001](../design/0001-hextory-vision.md) · [Scorecard](../maturity/SCORECARD.md)

---

## State machine

```
Ideation
   → Draft SDD
   → Review (human)
   → Review (agent)
   → Changes requested ──┐
   → Approved            │
   → Implementation allowed
   → Verification against SDD
   → Shipped

Any Review_* or Verification may transition to Changes requested,
which returns to Draft SDD (or a focused revision) and re-enters review.
```

| State | Meaning | Who acts |
|---|---|---|
| **Ideation** | Problem sensed; no formal SDD yet | Human or agent |
| **Draft SDD** | `docs/design/NNNN-slug.md` exists; status Draft | Authors |
| **Review (human)** | Human checklist + architecture-critical sign-off | Human reviewer |
| **Review (agent)** | Structured agent checklist pass | Agent reviewer |
| **Changes requested** | Dual review found gaps; must revise | Authors |
| **Approved** | Both reviews recorded; gates green | Process / authors update status |
| **Implementation allowed** | Agents may generate code for this SDD only | Agent implementers |
| **Verification against SDD** | Artifacts checked vs acceptance criteria & traceability | Quality (agent + optional human) |
| **Shipped** | Verification passed; release metadata recorded | Packaging / maintainers |

Order of human vs agent review may be parallel or sequential; **both** must Approve before **Approved**. If either requests changes, status is **Changes requested**.

---

## Hard rules

1. **No code merge/ship without Approved SDD.** Product/implementation code for a workflow must not merge or ship unless that workflow’s SDD is **Approved**.
2. **Agents may draft SDDs.** Drafting is encouraged. Drafting ≠ approval.
3. **Humans must approve architecture-critical sections.** See template checklist items marked Critical / Yes for human.
4. **Dual design review required.** Human + agent on the SDD. Single-party approval is insufficient.
5. **Verification is mandatory.** Implementation allowed is not Shipped; verification against the SDD must pass.
6. **Rework is explicit.** Failures go to Changes requested (design) or Quality FAIL rework (implementation), never silent force-merge.
7. **One workflow ↔ one primary SDD.** Large changes that break prior acceptance criteria need a new SDD or a versioned revision that re-enters review.
8. **Human merge approval is design-doc readiness, not a code walkthrough.** Merges to the main line require a human to approve—but that approval is grounded in the Approved SDD and green gate criteria (scope fit, acceptance criteria, traceability). **No human line-by-line CODE review is required.** Humans do not need to read the implementation diff as the merge gate.

---

## How to iterate

1. Copy [TEMPLATE.md](../design/TEMPLATE.md) → new `NNNN-slug.md` (or revise an existing Draft).
2. Fill every section; use `N/A` + reason only where truly inapplicable.
3. Set status to **Draft**; open review (issue/PR/discussion—see PR policy below).
4. Human reviewer completes checklist; agent reviewer completes checklist.
5. If changes requested: update the SDD, bump revision history, re-review delta.
6. When both approve and gate criteria are green: set status **Approved**.
7. Agent implementers work only under that Approved SDD; keep REQ/DES/TEST IDs in commits/PRs.
8. Run verification mapped to acceptance criteria; on FAIL, rework per SDD failure policy.
9. On PASS, mark **Shipped** and update maturity evidence when relevant.

---

## Where files live

| Artifact | Path |
|---|---|
| SDD template | `docs/design/TEMPLATE.md` |
| Workflow SDDs | `docs/design/NNNN-slug.md` |
| This workflow | `docs/workflows/design-doc-review.md` |
| Engine intent (not an Approved SDD) | `docs/architecture/factory-engine-intent.md` |

Do not keep “side” design docs in chat logs or private notes as the source of truth. Promote durable decisions into `docs/design/`.

---

## Naming

- **Pattern:** `NNNN-slug.md`
  - `NNNN` — zero-padded decimal, monotonically increasing (`0001`, `0002`, …).
  - `slug` — lowercase kebab-case, short, stable (`hextory-vision`, `gatekeeper-api`).
- **Doc ID** inside the file: `DES-NNNN` matching the number.
- **Do not renumber** after review has started; supersede with a new number if needed and point `Supersedes` / `Superseded by`.

---

## Review sequencing tips

- Prefer **human review of architecture-critical sections before** heavy agent implementation planning.
- Agent review should flag: missing non-goals, untestable acceptance criteria, broken traceability, hexagonal violations, vague failure policy.
- Disagreements: capture in Open questions or a “Dissent” note under revision history; do not Approve until resolved or explicitly deferred with owner.

---

## PR policy (later — public git)

When the repository is public and PR-based:

1. **SDD changes** land via PR titled `docs(design): DES-NNNN …` with reviewers assigned (human + agent summary comment).
2. **Implementation PRs** must cite `DES-NNNN` (Approved) in the description; CI (when available) checks the citation and status.
3. PRs that add implementation **without** an Approved SDD citation are rejected.
4. **Main-line merge requires human approval** that the design-doc gate is satisfied (Approved SDD, green gates, in-scope). The human is **not** required to perform line-by-line code review of the diff.
5. Mechanical refactors that do not change behavior still need a thin SDD or an approved amendment if they alter architecture boundaries.
6. LICENSE, typo-only doc fixes, and scorecard updates may proceed without a full SDD but must not smuggle behavior changes.

Until public git automation exists, enforce these rules manually in review discussions.

---

## Mapping to DigitalTraveler statuses (future engine)

When the factory engine exists, traveler `status` should align with the states above (plus department-local substates). The gatekeeper refuses `Implementation allowed` transitions unless `sdd_id` points at an Approved doc.

---

## Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-15 | Marcos Blazquez + New Bot | Initial workflow for ideation pack |
