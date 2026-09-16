# Hextory maturity scorecard

| Field | Value |
|---|---|
| **Date** | 2026-09-16 17:31 America/Santiago |
| **Stage** | Building foundations — ruleset + v0.1.0 + traveler@0.1; approaching operational candidate |
| **Latest pulse** | [R-0011](reports/R-0011-20260916-1731.md) |
| **Scorers** | Clark Bot (maturity pulse); prior: Marcos Blazquez + New Bot |
| **Method** | Per [ASPECTS.md](ASPECTS.md); each aspect 0–100; overall = mean |

## Scores

| # | Aspect | Score (0–100) | Rationale |
|---|---|---|---|
| 1 | Vision clarity | **70** | DES-0001/0002 **Approved**; DES-0002 Approved-body hygiene + published traveler contract; DES-0003 bare Draft ideation. |
| 2 | Design-doc coverage | **60** | TEMPLATE + Approved vision + Approved engine + Draft Studio ideation; no new Approved workflow SDDs. |
| 3 | Review rigor (dual human+agent) | **55** | Two dual Approvals; PR merge-via-doc practiced (#1/#2); `required_approving_review_count: 0` caps further lift. |
| 4 | Traceability (REQ↔DES↔IMPL↔TEST) | **76** | DES-0002 §12 + live IMPL + published `hextory.digital_traveler@0.1`; pytest **72 passed**. |
| 5 | Architecture purity (hexagonal isolation) | **80** | Pure `src/` + ports; LangGraph/Echo/OpenAI adapter-only; open GraphRegistry; only `adapters/local`. |
| 6 | Determinism, testability & readable core | **84** | `tests/{unit,behavior,adapters}`; GWT BDD-style not Cucumber; CI bans cucumber; 72 tests passed. |
| 7 | Automation of design gates (CI/process) | **84** | Gatekeeper + Q-GATE-1 + `ci_design_gates.py` + ruleset **requires** design-gates + pytest on PR→main; approvals=0 and not strict up-to-date. |
| 8 | Factory observability (traces, quality loops) | **52** | FileCheckpointer persists travelers + quality FAIL under `.hextory/`; FileIdempotency; no dashboards. |
| 9 | Multi-target deploy readiness | **40** | Local CLI + File/Memory checkpointers; dual runtime ≠ second target; only `adapters/local`. |
| 10 | Public project readiness | **82** | Public GitHub + MIT + README + CONTRIBUTING; **v0.1.0**; ruleset active; traveler contract; PR habit; no issue/PR templates. |

### Overall maturity

| Metric | Value |
|---|---|
| Sum of aspect scores | 70+60+55+76+80+84+84+52+40+82 = **683** |
| **Overall maturity** | **68.3** |
| Band | **40–69 — Building foundations** (approaching operational candidate) |
| Meets ≥90? | **NO** |
| Δ vs R-0010 | **+3.5** (64.8 → 68.3) — ruleset required checks + v0.1.0 + traveler@0.1 + PR habit + DES-0002 hygiene |

## Next actions

1. Second deploy adapter beyond `adapters/local` with traveler/Gatekeeper parity (aspect 9) — dual runtime ≠ multi-target.
2. Observability: dashboards / gate-denial metrics beyond file artifacts (aspect 8).
3. Add issue/PR templates for SDD contribution path (aspect 10).
4. More Approved workflow SDDs under dual review (aspects 2, 3).
5. When a second reviewer exists: re-enable ≥1 required approving review; consider strict up-to-date (aspects 3, 7).
6. Keep DES-0003 Draft ideation only — no product UI during pulse; out-of-tree consumers stay out of public kernel score.
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
| 2026-09-16 17:31 | Clark Bot | Pulse R-0011: ruleset + v0.1.0 + traveler@0.1 + PR habit → overall **68.3** (+3.5) |
