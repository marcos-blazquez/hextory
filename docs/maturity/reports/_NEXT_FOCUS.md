# Next focus (sticky)

Last pulse: **R-0056** (2026-09-20 09:21 America/Santiago) — overall **82.2** (Δ0 vs R-0055); score **FLAT**; blockers **SAME**.

## Active blockers (punch list)

1. **Observability first-slice (aspect 8 = 74)** — MetricsPort + /metrics + Grafana JSON + TEST-OBS exist; need operated scrape/alerts and traveler-journey visibility toward 85+. AWS-SMOKE metrics scrape still deferred.
2. **Thin Approved *workflow* SDD coverage** — **Draft DES-0007** (linear quality gate) still not dual-Approved. DES-0008 Approved is kernel vars, not workflow coverage. Draft DES-0009 (RequestGateway run bind) is inventory only.

## Parked / waived (not active)

- `required_approving_review_count ≥ 1` — paused/waived **2026-09-19** solo-author interim. Dual design-doc Approve remains the review-rigor signal. Do not re-list approvals=0 as a blocker; do not change GitHub branch protection from maturity docs.

## Evidence landmarks

- Main tip (before R-0056 land): `d83236f` (merge PR #61 / R-0055)
- Product tip: `65a46c8` (unchanged; ahead_by 52 vs main are maturity/docs/templates/smoke)
- DES Approved: 0001, 0002, 0004, 0005, 0006, **0008**; Draft: 0003, 0007, 0009, 9999
- AWS-SMOKE-001 + AWS-SMOKE-002 **SUCCEEDED** (held); NG1: CI must not `sam deploy`
- Pytest CI: **108 passed / 4 skipped** (3.11/3.12); design-gates OK (9 docs; 10 manifest keys)
- Ruleset: required checks design-gates + pytest; approvals=0 waived/parked; strict up-to-date false

## Ordered next actions

1. Deepen observability beyond first slice (operated scrape/alerts / traveler-journey) — aspect 8 toward 85+.
2. Dual-review DES-0007 (or another thin workflow SDD) to **Approved** — aspects 2, 3.
3. Optional: implement DES-0008 first-slice VariableResolverPort + TEST-VAR-* (Authorized) — aspect 4 (does not close workflow gap).
4. Optional: dual-review DES-0009 when ready — does not substitute for workflow coverage.
5. Optional: CoC/security for aspect 10 residual.
6. Keep DES-0003 Draft ideation only — no product UI during pulse; out-of-tree consumers stay out of public kernel score.
7. Continue scheduled pulses until overall ≥ 90; do not invent score lifts without new evidence.
8. When convenient: refresh Mac Documents SoT working tree from GitHub `main`.

## Capability lenses

- Code-review avoidance is one capability among others; dual SDD Approve is the review-rigor signal under solo-author waiver.
- Open graphs remain proven via GraphRegistry; Draft DES-0007 does not authorize impl.
- Testing: tests/{unit,behavior,adapters}, BDD-style not Cucumber.

## Scoring discipline

- Prefer GitHub `main` + authenticated `gh` (Mac when available; quote `?` for zsh). Do not score Approved set from stale Mac Documents SoT alone.
- Docs-only tip commits and Draft inventory must not lift aspects.
- Always separate tip CI from product CI landmark `65a46c8`.
- Memory note: R-0056 overall 82.2 (Δ0) with blockers SAME — next movement needs operated OBS, Approved workflow SDDs (DES-0007), or DES-0008 IMPL/TEST.

## Parked / waived (not active punch list)

- **`required_approving_review_count ≥ 1`** — **paused/waived 2026-09-19** (solo-author interim; not feasible to require 1 approval currently). Solo merges with approvals=0 are accepted. Dual design-doc Approve (human+agent) is the review-rigor signal. Do **not** re-list approvals=0 as a blocker; do **not** change GitHub branch protection from maturity docs. Revisit only when a second reviewer exists (strict up-to-date parked with the same revisit).
