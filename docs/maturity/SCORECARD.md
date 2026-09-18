# Hextory maturity scorecard

| Field | Value |
|---|---|
| **Date** | 2026-09-18 13:45 America/Santiago |
| **Stage** | Operational dark factory (candidate) — DES-0006 OBS + DES-0005 AWS first slices; AWS-SMOKE-001 real DynamoDB smoke SUCCEEDED |
| **Latest pulse** | [R-0036](reports/R-0036-20260918-1345.md) |
| **Scorers** | Clark Bot (maturity pulse); prior: Marcos Blazquez + New Bot |
| **Method** | Per [ASPECTS.md](ASPECTS.md); each aspect 0–100; overall = mean |

## Scores

| # | Aspect | Score (0–100) | Rationale |
|---|---|---|---|
| 1 | Vision clarity | **76** | DES-0001/0002/0004/0005/0006 **Approved**; AWS + observability direction explicit and first-slice implemented; DES-0003 bare Draft ideation. |
| 2 | Design-doc coverage | **76** | TEMPLATE + five Approved SDDs (vision/engine/on-prem/AWS/OBS); Draft Studio; no Approved *workflow* SDDs. |
| 3 | Review rigor (dual human+agent) | **70** | Five dual Approvals; PR #16/#18/#28/#29 under Approved DES; `required_approving_review_count: 0` caps further lift. |
| 4 | Traceability (REQ↔DES↔IMPL↔TEST) | **86** | DES-0004/0005/0006 live IMPL + TEST-ONP/TEST-AWS/TEST-OBS; traveler@0.1; AWS-SMOKE-001 evidence; pytest **115 passed / 1 skipped**. |
| 5 | Architecture purity (hexagonal isolation) | **88** | Pure `src/` + ports; LangGraph/Echo/OpenAI/Prometheus/boto adapter-only; open GraphRegistry; `adapters/{local,onprem,aws}`. |
| 6 | Determinism, testability & readable core | **88** | `tests/{unit,behavior,adapters}`; GWT BDD-style not Cucumber; CI bans cucumber; OBS+AWS parity; 115 passed / 1 skipped. |
| 7 | Automation of design gates (CI/process) | **85** | Gatekeeper + Q-GATE-1 + `ci_design_gates.py` + ruleset **requires** design-gates + pytest on PR→main; tip CI Success on `cc2ec42` (docs; Actions run 35364565916 / #75); product tip ci #63 on `65a46c8`; approvals=0 and not strict up-to-date. |
| 8 | Factory observability (traces, quality loops) | **74** | MetricsPort + on-prem GET `/metrics` + local dump + Grafana JSON + TEST-OBS + gateway counters. First-slice only — not production-grade ops (85+); AWS-SMOKE metrics deferred. |
| 9 | Multi-target deploy readiness | **82** | Local CLI + on-prem FastAPI/JWT/Postgres/Compose + **AWS** Lambda/DynamoDB/moto + LocalStack Compose + uneployed SAM + **AWS-SMOKE-001 SUCCEEDED** (real DynamoDB us-east-2); no full SAM/HTTP API deploy; CI must not deploy (NG1). |
| 10 | Public project readiness | **84** | Public GitHub + MIT + README + CONTRIBUTING; **v0.1.0**; ruleset active; traveler contract; PRs through #35; no issue/PR templates. |

### Overall maturity

| Metric | Value |
|---|---|
| Sum of aspect scores | 76+76+70+86+88+88+85+74+82+84 = **809** |
| **Overall maturity** | **80.9** |
| Band | **70–89 — Operational dark factory (candidate)** |
| Meets ≥90? | **NO** |
| Δ vs R-0035 | **0.0** (80.9 → 80.9) — flat reconfirm; no new ops/deploy/templates/workflow-SDD evidence; tip `cc2ec42` (R-0035 docs) |

## Next actions

1. Deepen observability beyond first slice (operated scrape/alerts / traveler-journey visibility) — aspect 8 toward 85+.
2. Strengthen AWS multi-target path beyond table+handler smoke (fuller SAM/HTTP evidence); keep NG1 (no CI real-account deploy) clear — aspect 9.
3. Add issue/PR templates for SDD contribution path (aspect 10).
4. More Approved *workflow* SDDs under dual review (aspects 2, 3).
5. When a second reviewer exists: re-enable ≥1 required approving review; consider strict up-to-date (aspects 3, 7).
6. Keep DES-0003 Draft ideation only — no product UI during pulse; out-of-tree consumers stay out of public kernel score.
7. Continue weekday hourly pulses until overall ≥ 90; do not invent score lifts without new evidence.
8. Land R-0036 maturity trio on main (R-0035 already via #35).
9. When Mac returns online: refresh SoT working tree from GitHub `main`.

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
| 2026-09-17 13:27 | Clark Bot | Pulse R-0022: OBS PR #16 + AWS PR #18 → overall **80.5** (+4.1); aspects 8/9 primary lifts |
| 2026-09-17 13:39 | Clark Bot | Pulse R-0023: flat reconfirm **80.5** (Δ0) after R-0022 docs @ `965c201` / tip ci #43; Mac SoT connected but stale |
| 2026-09-17 14:32 | Clark Bot | Pulse R-0024: flat reconfirm **80.5** (Δ0) after R-0023 docs @ `bc4f16b` / tip ci #45; Mac SoT connected but stale |
| 2026-09-17 15:28 | Clark Bot | Pulse R-0025: flat reconfirm **80.5** (Δ0) after R-0024 docs @ `6f72bde` / tip ci #47; Mac SoT connected but stale |
| 2026-09-17 16:27 | Clark Bot | Pulse R-0026: flat reconfirm **80.5** (Δ0) after R-0025 docs @ `62318d7` / tip ci #49; Mac SoT connected but stale |
| 2026-09-17 17:28 | Clark Bot | Pulse R-0027: flat reconfirm **80.5** (Δ0) after R-0026 docs @ `bada2de` / tip ci #51; Mac SoT connected but stale |
| 2026-09-17 18:27 | Clark Bot | Pulse R-0028: flat reconfirm **80.5** (Δ0) after R-0027 docs @ `d7265e5` / tip ci #53; Mac SoT connected but stale |
| 2026-09-17 19:26 | Clark Bot | Pulse R-0029: flat reconfirm **80.5** (Δ0) after R-0028; main tip still `d7265e5` / tip ci #53; R-0028 PR #25 OPEN (ci #54); Mac SoT connected but stale |
| 2026-09-18 08:24 | Clark Bot | Pulse R-0030: overall **80.9** (+0.4); aspect 9 78→82 from AWS-SMOKE-001 + PR #28/#29; tip `65a46c8` / ci #63; Mac SoT offline |
| 2026-09-18 09:38 | Clark Bot | Pulse R-0031: flat reconfirm **80.9** (Δ0) after R-0030 docs @ `1a0d940` / tip ci #65; product tip still `65a46c8` / ci #63; Mac SoT offline |
| 2026-09-18 10:36 | Clark Bot | Pulse R-0032: flat reconfirm **80.9** (Δ0) after R-0031 docs @ `f9836cd` / tip ci #67; product tip still `65a46c8` / ci #63; Mac SoT offline |
| 2026-09-18 10:51 | Clark Bot | Pulse R-0033: flat reconfirm **80.9** (Δ0) after R-0032 docs @ `15d9df9` / tip CI Success (Actions run 35351829374); product tip still `65a46c8` / ci #63; Mac SoT offline |
| 2026-09-18 11:45 | Clark Bot | Pulse R-0034: flat reconfirm **80.9** (Δ0) after R-0033 docs @ `5a50937` / tip CI Success (Actions run 35354099441 / #71); product tip still `65a46c8` / ci #63; Mac SoT offline |
| 2026-09-18 12:40 | Clark Bot | Pulse R-0035: flat reconfirm **80.9** (Δ0) after R-0034 docs @ `704cabc` / tip CI Success (Actions run 35359406843 / #73); product tip still `65a46c8` / ci #63; Mac SoT offline |
| 2026-09-18 13:45 | Clark Bot | Pulse R-0036: flat reconfirm **80.9** (Δ0) after R-0035 docs @ `cc2ec42` / tip CI Success (Actions run 35364565916 / #75); product tip still `65a46c8` / ci #63; Mac SoT unused |
