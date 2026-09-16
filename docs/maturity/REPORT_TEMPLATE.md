# Hextory maturity pulse report — TEMPLATE

Use this structure for every hourly maturity run. Save each run as `docs/maturity/reports/R-NNNN-YYYYMMDD-HHMM.md` (America/Santiago wall clock in the filename). Keep the body concise; evidence paths beat prose.

| Field | Value |
|---|---|
| **Report ID** | R-NNNN |
| **Date / time** | YYYY-MM-DD HH:MM America/Santiago |
| **Scorer** | New Bot (maturity pulse) |
| **Repo path** | `/Users/mblazquez/Documents/dev/pixpod/hextory` |
| **Method** | [ASPECTS.md](ASPECTS.md); scores 0–100; overall = mean |
| **90+ bar** | Overall ≥ 90 → production / public-ready; pause further pulses unless human restarts |

---

## 1. Executive verdict

| Metric | Value |
|---|---|
| **Overall maturity** | NN.N |
| **Band** | Ideation / Foundations / Operational candidate / Production (≥90) |
| **Meets ≥90?** | YES / NO |
| **One-line summary** | … |

If YES: state that the pulse will pause itself and await human instruction.  
If NO: state the single biggest blocker to 90+.

---

## 2. Aspect scores

| # | Aspect | Score | Δ vs prior | Evidence (paths / facts) | Gap to 90 for this aspect |
|---|---|---|---|---|---|
| 1 | Vision clarity | | | | |
| 2 | Design-doc coverage | | | | |
| 3 | Review rigor | | | | |
| 4 | Traceability | | | | |
| 5 | Architecture purity | | | | |
| 6 | Determinism & readable core | | | | |
| 7 | Automation of design gates | | | | |
| 8 | Factory observability | | | | |
| 9 | Multi-target deploy readiness | | | | |
| 10 | Public project readiness | | | | |

**Readable code bar (cross-cutting):** Prefer clear names, small functions, explicit types, walk-through-friendly modules, and minimal cleverness. Score aspect 6 down when code exists but is hard to narrate aloud.

---

## 3. Capability lenses

| Lens | Status this run | Note |
|---|---|---|
| Code-review avoidance (one capability, not the whole product) | Strong / Partial / Weak / N/A | |
| Open-ended workflow graphs (unbounded node/edge composition) | Strong / Partial / Weak / Closed-catalog risk | |
| TDD + BDD-style (not Cucumber); testing-layer home | Strong / Partial / Weak / Location TBD | |

---

## 3b. Gate & merge posture

| Check | Status |
|---|---|
| Approved SDD required before implementation | |
| Human merge approval = design-doc readiness (not code walkthrough) | |
| Any merge/implementation without Approved SDD? | |

---

## 4. Edge cases & risks examined this run

List at least 3 concrete edge cases or failure modes probed this hour (even if still open). Examples: unsigned dual review, orphan workflow without SDD, hexagonal leak (`src/` importing infra), unreadable generated code, missing REQ↔TEST link, public leak of secrets, adapter drift across targets, **treating code-review avoidance as the only product goal**, **closed hard-coded graph that cannot add nodes/edges**, **implementation without TDD**, **Cucumber-only BDD assumption**, **unclear testing-layer home**.

| Edge case | Severity | Status | Note |
|---|---|---|---|
| | High/Med/Low | Open / Mitigated / Accepted | |

---

## 5. Learning for next run

What context, memory, or checklist items were updated so the *next* pulse is stricter/more thorough? Bullet list. If overall &lt; 90, this section is mandatory and non-empty.

---

## 6. Next actions (ordered)

1. …  
2. …  
3. …

---

## 7. Artifacts touched

| Path | Change |
|---|---|
| `docs/maturity/SCORECARD.md` | Rescored |
| | |

---

## Revision

| Date | Author | Note |
|---|---|---|
| | | Initial report for this ID |
