# Next pulse focus (sticky)

1. R-0055 overall **82.2** (+0.6 vs R-0054) — score **MOVED** (DES-0008 dual Approve via PR #59); blockers **SAME**. Main evidence tip before this pulse land is `b4df4fa` (Draft DES-0009 / PR #60); product tip remains `65a46c8` (50 maturity/docs/templates/smoke commits ahead).
2. Ceiling to >=90 — active blockers: **deepen observability ops** (operated scrape, alerts/SLOs, traveler journeys; aspect 8=74 — AWS-SMOKE metrics still deferred); **dual-Approve DES-0007** (or another workflow SDD; aspect 2/3 — Draft alone does not lift coverage). DES-0008 is now **Approved** (kernel vars; Authorized VariableResolverPort slice not yet implemented — does not close workflow gap). Draft DES-0009 is inventory only. Optional CoC/security for aspect 10 residual (not primary).
3. Capability lenses remain explicit: code-review avoidance is one capability; open graphs remain proven via `GraphRegistry`; testing uses `tests/{unit,behavior,adapters}` with readable BDD-style behavior tests, not Cucumber.
4. AWS-SMOKE-001 + AWS-SMOKE-002 **SUCCEEDED** (held). Do **not** lift aspect 8 from smoke evidence — metrics scrape remains deferred. NG1: CI must not `sam deploy`.
5. Prefer GitHub `main` + authenticated `gh` (Mac SoT when m16 unreachable; quote `?` URLs for zsh). Public `.github/` has ISSUE_TEMPLATE/ + PULL_REQUEST_TEMPLATE.md + workflows. Documents SoT tree is not a git checkout.
6. Always run design-gates + pytest when a product clone is available. Cite live CI pytest (**108 passed / 4 skipped**). Overall <90 means continue scheduled pulses; >=90 pauses the routine (weekday); weekend pulses report the boolean only.
7. Do not draft new SDDs or implement product features during pulse runs. Keep public docs agnostic of out-of-tree consumers. Draft DES-0007 and DES-0009 do **not** authorize implementation; DES-0008 Authorization requires a separate IMPL PR before aspect-4 lift.
8. Memory note for next run: R-0055 overall 82.2 (+0.6) with blockers SAME — do **not** invent further lifts from Draft DES-0009 or docs-only tip CI; next movement needs operated OBS, Approved workflow SDDs (DES-0007), or DES-0008 IMPL/TEST.

## Parked / waived (not active punch list)

- **`required_approving_review_count ≥ 1`** — **paused/waived 2026-09-19** (solo-author interim; not feasible to require 1 approval currently). Solo merges with approvals=0 are accepted. Dual design-doc Approve (human+agent) is the review-rigor signal. Do **not** re-list approvals=0 as a blocker; do **not** change GitHub branch protection from maturity docs. Revisit only when a second reviewer exists (strict up-to-date parked with the same revisit).
