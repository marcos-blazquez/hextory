# Contributing to Hextory

Hextory is a **design-gated dark factory**: Approved Software Design Documents (SDDs) are the primary quality gate. Humans approve design readiness; agents implement. **Line-by-line human code review is not required** for main-line merges — human merge approval is grounded in an **Approved** SDD and green gates (DES-0001-B / DES-0002-D).

This guide is the contributor on-ramp. Process detail lives in [`docs/workflows/design-doc-review.md`](docs/workflows/design-doc-review.md).

> **Repo note:** Public GitHub + Actions CI + branch ruleset (PR + required checks + 1 review) are live. DigitalTraveler published contract: [`docs/contracts/digital-traveler-0.1.md`](docs/contracts/digital-traveler-0.1.md) (`hextory.digital_traveler@0.1`).

---

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# Optional LangGraph runner + parity tests:
# pip install -e ".[dev,langgraph]"
pytest
python -m adapters.local.cli run --sdd DES-0002 --workflow starter_factory --force-quality PASS
# Optional: --runtime langgraph (default is pure)
```

Python **3.11+**. See [`README.md`](README.md) for layout and CLI notes.

---

## What you may change without an Approved SDD

| Allowed | Not allowed |
|---|---|
| Docs ideation / **Draft** SDDs | Product/engine code for a workflow whose SDD is not **Approved** |
| Tests that fail first against an Approved SDD (TDD) | Shipping or merging implementation that cites only a Draft SDD |
| Maturity reports, CONTRIBUTING, CI config | Bypassing Gatekeeper / soft-allow on SDD read errors |
| Bugfixes that stay in scope of an Approved SDD | New deploy targets (AWS) until DES-0005 **Approved**; observability exporters until DES-0006 **Approved**; Studio UI until DES-0003 Approved |
| | Cucumber / Gherkin toolchains (BDD-*style* in ordinary pytest only) |
| | Studio / React / xyflow / `adapters/web` until DES-0003 (or a build SDD) is **Approved** |

---

## Design-doc path (required for implementation)

1. Copy [`docs/design/TEMPLATE.md`](docs/design/TEMPLATE.md) → `docs/design/NNNN-slug.md`.
2. Set **Status** to a bare token in the field table: `Draft` \| `In Review` \| `Changes Requested` \| `Approved` \| `Superseded`.  
   **Do not** put parentheticals in the Status cell (the local status reader parses that cell; prose belongs in other rows or §0).
3. Update [`config/sdd_status.json`](config/sdd_status.json) to the **same** status (Q-GATE-1: when both exist they must agree; mismatch → deny / ERROR).
4. Dual review: **human + agent** per [`docs/workflows/design-doc-review.md`](docs/workflows/design-doc-review.md). Record reviews under `docs/design/reviews/` when applicable.
5. Only after **Approved**: implement under that SDD’s acceptance criteria and TEST IDs.
6. Verify against the SDD; Quality FAIL → rework (default max 3), then escalate — never silent ship.

**Authoritative SDDs today**

| Doc | Status | Role |
|---|---|---|
| [DES-0001](docs/design/0001-hextory-vision.md) | Approved | Vision / operating model |
| [DES-0002](docs/design/0002-factory-engine.md) | Approved | Factory engine; first slice authorized |
| [DES-0003](docs/design/0003-workflow-studio.md) | Draft | Hextory Studio ideation — **no UI implementation** |
| [DES-0004](docs/design/0004-onprem-adapter.md) | Approved | On-prem adapter (`adapters/onprem`) — first slice in tree; AWS/Studio still out of scope |
| [DES-0005](docs/design/0005-aws-adapter.md) | Draft | AWS adapter (`adapters/aws`) — LocalStack/moto first; **no impl** until Approved |
| [DES-0006](docs/design/0006-factory-observability.md) | Draft | Factory observability — metrics + `/metrics`; **no impl** until Approved |

---

## Hexagonal rules (DES-0002)

- `src/` must **not** import `adapters/` or `langgraph` (enforced in tests / CI). Optional LangGraph lives in `adapters/local/` behind the `GraphRunner` port; CLI default is `--runtime pure`.
- Side effects (CLI, files, HTTP, LLM clients) live in adapters.
- Open-ended graphs: register nodes/edges via registry — do not hard-code a closed three-node catalog as the only forever topology.
- Gatekeeper **fail closed**: missing / non-Approved / ERROR / UNKNOWN → deny; no assembly entry.
- Architecture policy stays in `src/`; UIs must not re-implement Gatekeeper or become a second engine (DES-0003 posture).

---

## Testing (DES-0002-E)

| Layout | Purpose |
|---|---|
| `tests/unit/` | Pure core / policy |
| `tests/behavior/` | Given/When/Then scenarios in ordinary pytest (**not** Cucumber) |
| `tests/adapters/` | Local CLI / reader smokes + on-prem HTTP parity (TEST-ONP-*) |

TDD: prefer failing tests first for new behavior. Keep TEST-xxxx IDs in test docstrings when mapping to an SDD.

```bash
pytest
pytest tests/unit -q
pytest -m behavior -q
```

---

## Pull requests / merge (when git exists)

1. Cite the **Approved** `sdd_id` (and workflow id) in the PR description.
2. CI must be green (tests + design-gate checks).
3. Human approve merge based on **design-doc readiness** (Approved SDD, in-scope change, gates green) — not a code walkthrough.
4. Do not merge implementation for Draft-only SDDs (including DES-0003 Studio, DES-0005 AWS, DES-0006 observability). On-prem impl must cite **Approved** DES-0004.

---

## CI (design-gate automation)

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

On push/PR (once the repo is on GitHub) it:

1. Installs the package with dev deps and runs **pytest**.
2. Runs **design-gate** checks (`scripts/ci_design_gates.py`): import boundary already in pytest; plus SDD status hygiene (manifest ↔ markdown), no Cucumber dependency, CONTRIBUTING present.

Locally:

```bash
python scripts/ci_design_gates.py
pytest
```

---

## Code style (DES-0002-F)

Prefer readable, walk-through-friendly core: explicit names, shallow modules, clarity over cleverness. Comments explain *why* on policy edges.

---

## License

By contributing, you agree your contributions are licensed under the MIT License ([LICENSE](LICENSE)).
