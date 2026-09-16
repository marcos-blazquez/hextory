# Hextory maturity aspects

Each aspect is scored **0–100**. Higher is more mature for operating a design-gated dark factory.

## Overall maturity

\[
\text{Overall \%} = \frac{1}{10}\sum_{i=1}^{10} \text{score}_i
\]

Because each aspect is already on a 0–100 scale, the overall maturity number **is** the arithmetic mean of the ten aspect scores (no further ÷5 scaling).

### Suggested thresholds

| Overall | Band | Meaning |
|---|---|---|
| **&lt; 40** | Ideation | Vision and process sketches; little or no gated implementation |
| **40–69** | Building foundations | Templates, dual review, early gates; engine/adapters incomplete |
| **70–89** | Operational dark factory (candidate) | Design gates enforced; quality loops and multi-target paths work in practice |
| **≥ 90** | Production-grade / public-ready bar | Docs, license, contrib, observability, and deploy readiness meet a high public bar |

Thresholds are guidance for scorecard narrative, not automated CI cut-scores (until aspect 7 matures).

## Product capabilities (lenses on the same scorecard)

Hextory is not *only* “skip code review.” When scoring and when writing pulse reports, evaluate these capabilities explicitly (they cut across aspects):

| Capability | What “good” looks like | Mostly reflected in aspects |
|---|---|---|
| **Code-review avoidance** | Agents implement; humans approve merges via **Approved SDD readiness**, not line-by-line diffs | 3, 6, 7 |
| **Open-ended workflow graphs** | New workflows = new nodes/edges/compositions (YAML/registry/SDD-defined), not a closed hard-coded catalog. Combinations of edges/nodes are unbounded in principle | 2, 5, 8 |
| **TDD + BDD-style testing** | Tests lead design; behavior described in readable Given/When/Then (or equivalent) **without Cucumber**. Enforced at the **testing layer** (exact package/layout TBD) | 4, 6, 7 |

A high overall score that still assumes a *fixed* three-department pipeline forever is incomplete. Pulse reports must call out whether design/architecture still imply a closed graph.


---

## Scoring guidance (all aspects)

| Band | Rough meaning |
|---|---|
| 0–9 | Absent / not started |
| 10–29 | Sketch or one-off notes only |
| 30–49 | Documented intent; inconsistent practice |
| 50–69 | Repeatable practice with known gaps |
| 70–84 | Enforced and evidenced; minor gaps |
| 85–100 | Robust, measured, public-ready for this aspect |

Evidence should be concrete: paths to SDDs, review records, CI configs, traces, deploy runbooks, LICENSE/CONTRIBUTING, etc.

---

## The ten aspects

### 1. Vision clarity

**What it measures:** Shared, written understanding of Hextory’s problem, dark-factory thesis, roles, and non-goals.

**Why it matters for a dark factory:** Without a clear vision, agents optimize the wrong gate (code review theater) and humans disagree on what “Approved” means.

**Evidence sources:** `README.md`, `docs/design/0001-hextory-vision.md`, glossary consistency, linked non-goals.

---

### 2. Design-doc coverage

**What it measures:** Fraction and quality of workflows covered by SDDs (template adherence, not orphan chat designs).

**Why it matters:** Coverage is the factory’s bill of materials. Uncovered work cannot be safely lights-out.

**Evidence sources:** `docs/design/*.md` inventory vs known workflows; TEMPLATE compliance; status fields.

---

### 3. Review rigor (dual human+agent)

**What it measures:** How consistently SDDs receive dual design review with recorded human + agent sign-off; architecture-critical human approval.

**Why it matters:** Dual review replaces line-by-line code review as the trust mechanism. Weak review → unsafe merge approvals.

**Evidence sources:** Checklist completions in SDDs; review comments; merge decisions citing design readiness (not diff walkthroughs).

---

### 4. Traceability (REQ ↔ DES ↔ IMPL ↔ TEST)

**What it measures:** Stable IDs and walkable links from requirements through design, implementation, and tests.

**Why it matters:** Verification against SDD is impossible without traceability; rework loops need defect→criterion mapping.

**Evidence sources:** Traceability tables in SDDs; commit/PR citations of DES/REQ/TEST; test manifests.

---

### 5. Architecture purity (hexagonal isolation + open graphs)

**What it measures:** Pure core in `src/` free of adapter I/O; ports/adapters boundaries respected across targets; **workflow topology is open-ended** (composable nodes/edges), not a single hard-wired pipeline.

**Why it matters:** Dark factories change deploy targets without rewriting domain logic. They also need endless workflow combinations — new departments, gates, and edges — without forking the engine.

**Open-graph bar:** registries or SDD-driven graph definitions; adding a workflow does not require editing a closed enum of “the only three departments.” Conditional edges and rework loops remain data/policy, not one-off special cases forever.

**Evidence sources:** Package layout; import lint/arch tests; engine SDDs; graph/registry design; `docs/architecture/factory-engine-intent.md`.


---

### 6. Determinism, testability & readable core

**What it measures:** Pure core behavior is deterministic where required, covered by automated tests, free of infra side effects, and **readable** — a human can walk through modules aloud without decoding cleverness.

**Why it matters:** Lights-out rework loops need reliable FAIL/PASS signals. Without human code review, readability is how humans audit intent at merge time against the SDD.

**Readable style bar:** clear names, small functions, explicit types, shallow nesting, documented public ports, no magic. Prefer boring structure over dense abstractions.

**TDD / BDD-style bar:** Red→green→refactor for core changes. Behavior specs use readable Given/When/Then (or equivalent narrative assertions) — **BDD style, not Cucumber** (no Gherkin feature-file toolchain required). Enforcement lives in the **testing layer**; its exact home (`tests/`, `src/...`, adapter smokes, etc.) is **TBD** and must be decided in an Approved SDD before treating the bar as met.

**Evidence sources:** Unit tests on `src/`; failing-first history or documented TDD practice; BDD-style behavior modules; golden traces; absence of I/O in core modules; spot walk-through notes in pulse reports; SDD decision on testing-layer location.


---

### 7. Automation of design gates (CI/process)

**What it measures:** Machine-enforced checks that block implementation/merge without Approved SDD + human design-readiness approval signal.

**Why it matters:** Manual discipline decays; gates must be boring and automatic for a public dark factory.

**Evidence sources:** CI workflows; status bots; branch protection requiring human merge approval tied to doc gate; templates.

---

### 8. Factory observability (traces, quality loops)

**What it measures:** Visibility into DigitalTraveler journeys, quality FAIL/rework, department timings, gate denials.

**Why it matters:** Lights-out operation fails silently without traces; humans escalate from signals, not from reading every diff.

**Evidence sources:** Trace stores; dashboards; structured quality reports; run logs.

---

### 9. Multi-target deploy readiness (local / on-prem / AWS)

**What it measures:** Same core runnable via local CLI/MemorySaver, on-prem Docker/FastAPI/Postgres, and AWS serverless adapters.

**Why it matters:** Contributors and operators need a path from laptop to production without forking the domain.

**Evidence sources:** Adapter packages; deploy docs; smoke tests per target; parity matrix.

---

### 10. Public project readiness (docs, license, contrib)

**What it measures:** LICENSE, README, contribution-via-SDD docs, Code of Conduct/security basics as needed, discoverability.

**Why it matters:** Public dark factories attract external agents/humans; unclear contrib paths recreate review chaos.

**Evidence sources:** `LICENSE`, README links, workflow docs, CONTRIBUTING (when present), issue/PR templates.

---

## Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-15 | Marcos Blazquez + New Bot | Initial aspects; 0–100 scale + thresholds |
| 2026-09-15 | New Bot | Product capabilities lenses; aspect 5 includes open-ended graphs; code-review avoidance is one capability |
| 2026-09-15 | New Bot | TDD + BDD-style (not Cucumber) capability; testing-layer location TBD |
