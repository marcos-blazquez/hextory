# Hextory maturity scorecard

| Field | Value |
|---|---|
| **Date** | 2026-09-16 16:26 America/Santiago |
| **Stage** | Building foundations — public git + live CI + interceptors/LLM |
| **Latest pulse** | [R-0010](reports/R-0010-20260916-1626.md) |
| **Scorers** | Clark Bot (maturity pulse); prior: Marcos Blazquez + New Bot |
| **Method** | Per [ASPECTS.md](ASPECTS.md); each aspect 0–100; overall = mean |

## Scores

| # | Aspect | Score (0–100) | Rationale |
|---|---|---|---|
| 1 | Vision clarity | **65** | DES-0001/0002 **Approved**; public README; DES-0003 bare Draft; leftover Draft wording in Approved DES-0002 body. |
| 2 | Design-doc coverage | **60** | TEMPLATE + Approved vision + Approved engine + Draft Studio ideation; no other concrete workflow SDDs. |
| 3 | Review rigor (dual human+agent) | **50** | Two dual Approvals with agent review records; DES-0003 reviewers TBD. |
| 4 | Traceability (REQ↔DES↔IMPL↔TEST) | **74** | DES-0002 §12 + live IMPL + FileCheckpointer/GraphRunner + idempotency/LLM tests; pytest **72 passed**. |
| 5 | Architecture purity (hexagonal isolation) | **80** | Pure `src/` + ports (GraphRunner, IdempotencyStore, LlmPort); LangGraph/Echo/OpenAI adapter-only; open GraphRegistry. |
| 6 | Determinism, testability & readable core | **84** | `tests/{unit,behavior,adapters}`; GWT BDD-style not Cucumber; CI bans cucumber; 72 tests passed. |
| 7 | Automation of design gates (CI/process) | **70** | Runtime Gatekeeper + Q-GATE-1 + `ci_design_gates.py` + hosted Actions **Success** on main (`03b2ebf`); **no branch protection** yet. |
| 8 | Factory observability (traces, quality loops) | **52** | FileCheckpointer persists travelers + quality FAIL under `.hextory/`; FileIdempotency; CLI status from disk; no dashboards. |
| 9 | Multi-target deploy readiness | **40** | Local CLI + File/Memory checkpointers; dual runtime ≠ second target; only `adapters/local`. |
| 10 | Public project readiness | **73** | Public GitHub + MIT + README + CONTRIBUTING; CI passing; git deferral lifted; no issue/PR templates. |

### Overall maturity

| Metric | Value |
|---|---|
| Sum of aspect scores | 65+60+50+74+80+84+70+52+40+73 = **648** |
| **Overall maturity** | **64.8** |
| Band | **40–69 — Building foundations** (public git + live CI + interceptors/LLM) |
| Meets ≥90? | **NO** |
| Δ vs R-0009 | **+5.4** (59.4 → 64.8) — public repo + Actions Success + interceptors/LLM + 72 tests |

## Next actions

1. Branch protection on `main`: require design-gates (+ pytest) before merge (aspects 7, 10).
2. Scrub leftover Draft / “may change in review” wording in Approved DES-0002; keep Status cells bare for Q-GATE-1.
3. Add issue/PR templates for SDD contribution path.
4. Keep DES-0003 Draft ideation only — no React/xyflow/`adapters/web` until a later Approved build SDD.
5. Observability next: dashboards / gate-denial metrics beyond file artifacts.
6. Sync maturity artifacts to Mac SoT when reachable.
7. Continue weekday hourly pulses until overall ≥ 90; do not invent score lifts without new evidence.

## Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-15 | Marcos Blazquez + New Bot | Baseline ideation scores on 0–100 scale |
| 2026-09-15 | New Bot | Aligned with pulse R-0001; aspect 6 includes readable-core bar |
| 2026-09-15 ~15:34 | Clark Bot / New Bot | Post–DES-0001 Approval lift → overall **16.4** |
| 2026-09-15 16:16 | Clark Bot | Pulse R-0002: confirm **16.4**; README hygiene flagged |
| 2026-09-15 17:24 | Clark Bot | Pulse R-0003: DES-0002 Draft → overall **24.7**; dual Approval is blocker |
| 2026-09-15 | Clark Bot | DES-0002 dual review Approved; interim overall ~33.8 pending R-0004 |
| 2026-09-15 18:15 | Clark Bot | Pulse R-0004: DES-0002 Approval evidenced → overall **35.3**; first-slice still unstarted |
| 2026-09-15 19:23 | Clark Bot | Pulse R-0005: flat **35.3** (Δ0); no disk progress; edge cases deepened |
| 2026-09-16 08:23 | Clark Bot | Pulse R-0006: first-slice scaffold evidenced → overall **53.0** (+17.7) |
| 2026-09-16 09:38 | Clark Bot | Pulse R-0007: flat **53.0** (Δ0); reconfirm + edge-case deepening |
| 2026-09-16 10:50 | Clark Bot | Pulse R-0008: CONTRIBUTING + CI gates + DES-0003 hygiene → overall **56.9** (+3.9) |
| 2026-09-16 11:45 | Clark Bot | Pulse R-0009: FileCheckpointer + GraphRunner/LangGraph → overall **59.4** (+2.5) |
| 2026-09-16 16:26 | Clark Bot | Pulse R-0010: public git + Actions Success + interceptors/LLM → overall **64.8** (+5.4) |
