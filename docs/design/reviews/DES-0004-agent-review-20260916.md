# Agent review — DES-0004

| Field | Value |
|---|---|
| **Doc** | DES-0004 on-prem adapter (`adapters/onprem`) |
| **Reviewer** | Clark Bot |
| **Date** | 2026-09-16 America/Santiago |
| **Human counterpart** | Marcos Blazquez (Approve — chat 2026-09-16) |
| **Verdict** | **Approve** |

## Findings

1. **Pass** — Hexagonal: reuses RequestGateway / Gatekeeper / DigitalTraveler / GraphRunner ports; no core fork; `src/` stays free of FastAPI/Postgres/`adapters` imports (DES-0004-D, REQ-0010).
2. **Pass** — On-prem-first vs AWS: DES-0004-A correctly sequences second deploy target; AWS remains explicit non-goal (NG1).
3. **Pass** — JWT bearer default for first on-prem slice (DES-0004-B); mTLS deferred as optional later.
4. **Pass** — Postgres checkpointer + Docker Compose ops path matches DES-0002 §5.2 sketch (DES-0004-C/F).
5. **Pass** — HTTP semantic parity with local CLI (`POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/resume`) with TDD/BDD-style tests under `tests/adapters/` (DES-0004-E/G, REQ-0016).
6. **Pass** — Traveler published contract `hextory.digital_traveler@0.1` unchanged (NG3); public kernel stays agnostic of private sibling products.
7. **Pass** — DES-0003 Studio / React / `adapters/web` remains out of scope (NG2).
8. **Resolved** — Q-ONP-1: human Approve of Draft confirms **JWT bearer** for first slice; Clark Approve concurs. Q-ONP-2/3 stay open with non-blocking proposed interims for first scaffold.

## Recommendation

**Approved.** Agents may implement the first on-prem slice only after §13 is green (checked on dual Approve). This Approval package is docs-only — FastAPI/Postgres/Compose code is a follow-up after merge.
