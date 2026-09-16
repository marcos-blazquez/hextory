# Next pulse focus (sticky)

1. DES-0001/0002 **Approved**; **ruleset + v0.1.0 + `hextory.digital_traveler@0.1` are done**. R-0011 **68.3** (Δ+3.5 vs R-0010). Active ruleset requires `design-gates` + pytest on PR→main (`required_approving_review_count: 0` for solo merges — re-enable ≥1 when a second reviewer exists). Do not treat “no branch protection” or “no release” as the ceiling.
2. Ceiling to ≥90 — next items: **second deploy adapter** (aspect 9 ≈ 40 — only `adapters/local`; dual runtime ≠ multi-target); **observability** dashboards / gate-denial metrics (aspect 8 ≈ 52); **issue/PR templates** (aspect 10); **more Approved workflow SDDs** under dual review (aspects 2–3); re-enable required approvals when possible.
3. Capability lenses: code-review avoidance as one capability; open graphs proven; testing layer `tests/{unit,behavior,adapters}` (not Cucumber). Keep local `python scripts/ci_design_gates.py` + pytest green (~72 with langgraph).
4. Product track (outside pulse): observability / second deploy adapter — not DES-0003 UI. Watch: DES-0003 stays **Draft** ideation (Hextory Studio Draft OK); do not score dual runtime as multi-target; keep public kernel agnostic of out-of-tree consumers; downstream adapters and out-of-tree apps must not fork Gatekeeper/traveler core (see `docs/contracts/digital-traveler-0.1.md`).
5. Mac SoT / box mirror may lag public HEAD — prefer https://github.com/marcos-blazquez/hextory @ main; sync SoT when path returns.
6. Always report; ≥90 self-pause unchanged. Do not draft new SDDs or implement product features during pulse.
