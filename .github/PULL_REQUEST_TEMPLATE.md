## Summary

<!-- What does this PR change, and why? Keep it public-kernel / consumer-agnostic. -->

## Design gate

| Field | Value |
|---|---|
| **Related DES-####** | <!-- e.g. DES-0002, DES-0007 — or `n/a` for docs/CI-only --> |
| **SDD status** | <!-- Draft \| In Review \| Changes Requested \| Approved \| n/a --> |
| **Workflow id (if any)** | <!-- e.g. `starter_factory`, `linear_quality_gate`, or `n/a` --> |
| **In scope of Approved SDD?** | <!-- Yes / No / Docs-only Draft / n/a --> |

- [ ] I checked `config/sdd_status.json` agrees with the cited SDD Status cell (when both exist).
- [ ] This PR does **not** merge product/engine implementation for a Draft-only SDD.
- [ ] Human merge gate is **design-doc readiness** (Approved SDD + green gates + in-scope), not a line-by-line code walkthrough.

## Change type

- [ ] Docs / SDD / maturity / templates (no runtime behavior change)
- [ ] Tests only (TDD against an Approved SDD)
- [ ] Implementation under an **Approved** SDD
- [ ] CI / process / repo hygiene

## Verification

- [ ] `pytest` (or CI) green
- [ ] Design-gate checks green (`python scripts/ci_design_gates.py` / CI job)
- [ ] Acceptance / TEST IDs from the cited SDD addressed or explicitly deferred

## Explicit non-goals for this PR

<!-- e.g. No Gatekeeper fork; no real AWS deploy; no Studio UI while DES-0003 is Draft. -->

-

## Notes for reviewers

<!-- Dual-review status for new/changed SDDs; open questions; anything maturity pulse should notice. -->
