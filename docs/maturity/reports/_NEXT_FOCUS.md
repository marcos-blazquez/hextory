# Next pulse focus (sticky)

1. R-0050 overall **81.6** (+0.7 vs R-0049). Main evidence tip before this pulse land is `87b822e` (AWS-SMOKE-002 / PR #51); product tip remains `65a46c8` (37 maturity/docs/templates/smoke commits ahead). Material lifts: aspect 9 82→86 (full SAM+HTTP live smoke), aspect 10 84→87 (issue/PR templates).
2. Ceiling to >=90 — next material items: **deepen observability ops** (operated scrape, alerts/SLOs, traveler journeys; aspect 8=74 **held** — SMOKE-002 metrics still deferred); **dual-Approve DES-0007** (or another workflow SDD; aspect 2/3 — Draft alone does not lift coverage); when a second reviewer exists, re-enable >=1 required approval (aspects 3/7); optional CoC/security for aspect 10 residual.
3. Capability lenses remain explicit: code-review avoidance is one capability; open graphs remain proven via `GraphRegistry`; testing uses `tests/{unit,behavior,adapters}` with readable BDD-style behavior tests, not Cucumber.
4. AWS-SMOKE-002 **SUCCEEDED**: live SAM stack `hextory-aws-smoke` + HTTP API → Lambda → DynamoDB (health/runs/fetch/scan). Do **not** lift aspect 8 from this evidence — metrics scrape remains deferred. NG1: CI must not `sam deploy`.
5. Prefer GitHub `main` + authenticated `gh` (Mac SoT when m16 unreachable; quote `?` URLs for zsh). Public `.github/` now has ISSUE_TEMPLATE/ + PULL_REQUEST_TEMPLATE.md + workflows.
6. Always run design-gates + pytest when a product clone is available. Overall <90 means continue scheduled pulses; >=90 pauses the routine.
7. Do not draft new SDDs or implement product features during pulse runs. Keep public docs agnostic of out-of-tree consumers. Draft DES-0007 does **not** authorize implementation.
8. Memory note for next run: R-0050 broke the long flat-80.9 streak with justified AWS + templates lifts. Next movement needs operated OBS, Approved workflow SDDs, or ruleset second-reviewer — not more docs-only tip CI.
