# Hextory maturity scorecard

| Field | Value |
|---|---|
| **Date** | 2026-09-17 12:45 America/Santiago |
| **Stage** | Operational dark factory (candidate) — DES-0005/0006 Approved (docs); OBS + AWS impl still pending |
| **Latest pulse** | [R-0021](reports/R-0021-20260917-1245.md) |
| **Scorers** | Clark Bot (maturity pulse); prior: Marcos Blazquez + New Bot |
| **Method** | Per [ASPECTS.md](ASPECTS.md); each aspect 0–100; overall = mean |

## Scores

| # | Aspect | Score (0–100) | Rationale |
|---|---|---|---|
| 1 | Vision clarity | **76** | DES-0001/0002/0004/0005/0006 **Approved**; AWS + observability direction explicit; DES-0003 bare Draft ideation. |
| 2 | Design-doc coverage | **76** | TEMPLATE + five Approved SDDs (vision/engine/on-prem/AWS/OBS); Draft Studio; no Approved *workflow* SDDs. |
| 3 | Review rigor (dual human+agent) | **70** | Five dual Approvals; PR #15 merge-via-doc; `required_approving_review_count: 0` caps further lift. |
| 4 | Traceability (REQ↔DES↔IMPL↔TEST) | **80** | DES-0004 + live `adapters/onprem` IMPL + TEST-ONP; traveler@0.1; sdd_status has DES-0005/0006; no AWS/OBS IMPL yet; pytest **84 passed / 1 skipped**. |
| 5 | Architecture purity (hexagonal isolation) | **85** | Pure `src/` + ports; LangGraph/Echo/OpenAI adapter-only; open GraphRegistry; `adapters/local` + `adapters/onprem` only — no `adapters/aws`. |
| 6 | Determinism, testability & readable core | **86** | `tests/{unit,behavior,adapters}`; GWT BDD-style not Cucumber; CI bans cucumber; on-prem parity tests; 84 passed / 1 skipped. |
| 7 | Automation of design gates (CI/process) | **85** | Gatekeeper + Q-GATE-1 + `ci_design_gates.py` + ruleset **requires** design-gates + pytest on PR→main; ci #34 Success on `e5dd7d1` (docs); product ci #21 on `fcbe5b0`; approvals=0 and not strict up-to-date. |
| 8 | Factory observability (traces, quality loops) | **52** | FileCheckpointer + Postgres checkpointer + FileIdempotency; DES-0006 Approved but **no** MetricsPort / Prometheus `/metrics` / dashboards yet. |
| 9 | Multi-target deploy readiness | **70** | Local CLI + on-prem FastAPI/JWT/Postgres/Compose with parity tests; DES-0005 Approved but **no** `adapters/aws` yet. |
| 10 | Public project readiness | **84** | Public GitHub + MIT + README + CONTRIBUTING; **v0.1.0**; ruleset active; traveler contract; PRs through #15; no issue/PR templates. |

### Overall maturity

| Metric | Value |
|---|---|
| Sum of aspect scores | 76+76+70+80+85+86+85+52+70+84 = **764** |
| **Overall maturity** | **76.4** |
| Band | **70–89 — Operational dark factory (candidate)** |
| Meets ≥90? | **NO** |
| Δ vs R-0020 | **+2.2** (74.2 → 76.4) — DES-0005/0006 dual Approve on main @ `e5dd7d1`; aspects 8/9 held flat (no impl) |

## Next actions

1. Observability first slice per DES-0006: MetricsPort + Prometheus `/metrics` + gate-denial counters (aspect 8).
2. AWS first slice per DES-0005: `adapters/aws` LocalStack/moto + parity — no real account deploy (aspect 9).
3. Add issue/PR templates for SDD contribution path (aspect 10).
4. More Approved *workflow* SDDs under dual review (aspects 2, 3).
5. When a second reviewer exists: re-enable ≥1 required approving review; consider strict up-to-date (aspects 3, 7).
6. Keep DES-0003 Draft ideation only — no product UI during pulse; out-of-tree consumers stay out of public kernel score.
7. Continue weekday hourly pulses until overall ≥ 90; do not invent score lifts without new evidence.
8. Refresh Mac SoT working tree from GitHub `main` when practical (currently missing onprem / DES-0004+ / `.git`).

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
| 2026-09-16 17:41 | Clark Bot | Pulse R-0012: flat reconfirm **68.3** (Δ0) after PR #3 / ci #7 |
| 2026-09-16 18:26 | Clark Bot | Pulse R-0013: flat reconfirm **68.3** (Δ0) after PR #4 / ci #9 |
| 2026-09-16 19:28 | Clark Bot | Pulse R-0014: flat reconfirm **68.3** (Δ0) after PR #5 / ci #11 |
| 2026-09-16 19:45 | Clark Bot | Pulse R-0015: flat reconfirm **68.3** (Δ0) after PR #6 / ci #13 / main `187dda7` |
| 2026-09-17 08:23 | Clark Bot | Pulse R-0016: DES-0004 / `adapters/onprem` → overall **74.2** (+5.9); aspect 8 flat 52 |
| 2026-09-17 09:34 | Clark Bot | Pulse R-0017: flat reconfirm **74.2** (Δ0) after PR #10 / ci #23 / main `421ac29`; Mac SoT offline |
| 2026-09-17 10:40 | Clark Bot | Pulse R-0018: flat reconfirm **74.2** (Δ0) after R-0017 docs @ `359ce5e` / ci #25; Mac SoT offline |
| 2026-09-17 11:06 | Clark Bot | Pulse R-0019: flat reconfirm **74.2** (Δ0) after R-0018 docs @ `de42c94` / ci #27; Mac SoT offline |
| 2026-09-17 11:47 | Clark Bot | Pulse R-0020: flat reconfirm **74.2** (Δ0) after R-0019 docs @ `e9ad938` / ci #29; Mac SoT connected but stale |
| 2026-09-17 12:45 | Clark Bot | Pulse R-0021: DES-0005/0006 dual Approve on main @ `e5dd7d1` → overall **76.4** (+2.2); aspects 8/9 held |
