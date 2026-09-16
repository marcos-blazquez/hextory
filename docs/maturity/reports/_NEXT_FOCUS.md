# Next pulse focus (sticky)

1. DES-0001/0002 **Approved**; **public git + CI + branch ruleset are live** (PRs + required checks + 1 human review). R-0010 **64.8** (Δ+5.4 vs R-0009). Git-init deferral is **lifted** — do not treat “no local `.git` on box” as the blocker.
2. Ceiling to ≥90 — next items (not git-init): **release tag / package publish**; **DES-0002 Approved-body hygiene** (this PR closes residual Draft / “may change in review” wording + DigitalTraveler `@0.1` contract); **multi-target deploy still thin** (aspect 9 ≈ 40 — only `adapters/local`); issue/PR templates; observability dashboards.
3. Capability lenses: code-review avoidance as one capability; open graphs proven; testing layer `tests/{unit,behavior,adapters}` (not Cucumber). Keep local `python scripts/ci_design_gates.py` + pytest green (~72 with langgraph).
4. Product track (outside pulse): observability / second deploy adapter — not DES-0003 UI. Watch: DES-0003 Draft scope creep; do not score dual runtime as multi-target; keep public kernel agnostic of out-of-tree consumers; downstream adapters and out-of-tree apps must not fork Gatekeeper/traveler core (see `docs/contracts/digital-traveler-0.1.md`).
5. Mac SoT may be unreachable from box — always write `/workspace/hextory` (or clone root) and sync SoT when path returns.
6. Always report; ≥90 self-pause unchanged. Do not draft new SDDs or implement product features during pulse.
