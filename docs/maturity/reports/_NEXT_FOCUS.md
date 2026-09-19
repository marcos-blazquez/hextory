# Next pulse focus (sticky)

1. R-0054 overall **81.6** (Δ0 vs R-0053) — **FLAT** on score; blockers **SAME**. Main evidence tip before this pulse land is `65f01bd` (R-0053 maturity / PR #57); product tip remains `65a46c8` (46 maturity/docs/templates/smoke commits ahead).
2. Ceiling to >=90 — active blockers: **deepen observability ops** (operated scrape, alerts/SLOs, traveler journeys; aspect 8=74 — AWS-SMOKE metrics still deferred); **dual-Approve DES-0007** (or another workflow SDD; aspect 2/3 — Draft alone does not lift coverage). Draft DES-0008 (env/vars) is inventory only — not a workflow coverage fix. Optional CoC/security for aspect 10 residual (not primary).
3. Capability lenses remain explicit: code-review avoidance is one capability; open graphs remain proven via `GraphRegistry`; testing uses `tests/{unit,behavior,adapters}` with readable BDD-style behavior tests, not Cucumber.
4. AWS-SMOKE-001 + AWS-SMOKE-002 **SUCCEEDED** (held). Do **not** lift aspect 8 from smoke evidence — metrics scrape remains deferred. NG1: CI must not `sam deploy`.
5. Prefer GitHub `main` + authenticated `gh` (Mac SoT when m16 unreachable; quote `?` URLs for zsh). Public `.github/` has ISSUE_TEMPLATE/ + PULL_REQUEST_TEMPLATE.md + workflows. Documents SoT tree is not a git checkout.
6. Always run design-gates + pytest when a product clone is available. Cite live CI pytest (**108 passed / 4 skipped**). Overall <90 means continue scheduled pulses; >=90 pauses the routine.
7. Do not draft new SDDs or implement product features during pulse runs. Keep public docs agnostic of out-of-tree consumers. Draft DES-0007 and DES-0008 do **not** authorize implementation.
8. Memory note for next run: R-0054 flat 81.6 with blockers SAME — do **not** invent score lifts from docs-only tip CI, Draft DES-0008, or the approvals waiver; next movement needs operated OBS or Approved workflow SDDs.

## Parked / waived (not active punch list)

- **`required_approving_review_count ≥ 1`** — **paused/waived 2026-09-19** (solo-author interim; not feasible to require 1 approval currently). Solo merges with approvals=0 are accepted. Dual design-doc Approve (human+agent) is the review-rigor signal. Do **not** re-list approvals=0 as a blocker; do **not** change GitHub branch protection from maturity docs. Revisit only when a second reviewer exists (strict up-to-date parked with the same revisit).
