# Next pulse focus (sticky)

1. R-0043 is a flat reconfirm at **80.9** (Δ0 vs R-0042). Main evidence tip before this pulse land is `59f3cb5` (R-0042 / PR #42); product tip remains `65a46c8` (21 maturity-only commits ahead). Do not invent lifts from docs-only tip CI.
2. Ceiling to ≥90 — next material items: **deepen observability ops** (operated scrape, alerts/SLOs, traveler journeys; aspect 8=74); **strengthen AWS** beyond bounded DynamoDB/table + in-process handler smoke with fuller SAM/HTTP evidence while NG1 keeps CI from deploying (aspect 9=82); add issue/PR templates (aspect 10=84); and add more Approved workflow SDDs under dual review (aspects 2–3).
3. Capability lenses remain explicit: code-review avoidance is one capability; open graphs remain proven via `GraphRegistry`; testing uses `tests/{unit,behavior,adapters}` with readable BDD-style behavior tests, not Cucumber.
4. Keep AWS-SMOKE-001 bounded: **SUCCEEDED** table + handler round-trip, but metrics scrape is deferred and SAM/HTTP API is not deployed. Do not lift aspect 8 or claim full AWS deployment from this evidence.
5. Prefer GitHub `main` + authenticated `gh` (m16) when box api.github.com is rate-limited. Mac SoT is disconnected this weekend; do not infer product progress from it. Public `.github/` remains workflows-only — no issue/PR templates.
6. Always run `python scripts/ci_design_gates.py` + pytest when a product clone is available. Overall <90 means continue scheduled pulses; ≥90 pauses the routine.
7. Do not draft new SDDs or implement product features during pulse runs. Keep public docs agnostic of out-of-tree consumers.
8. Memory note for next run: R-0030's aspect-9 lift was followed by R-0031…R-0043 flat reconfirms. Only operated OBS, fuller AWS deploy evidence, contribution templates, or Approved workflow-SDD evidence can move scores.
