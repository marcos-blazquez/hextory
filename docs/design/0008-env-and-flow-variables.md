# DES-0008 — Environment and in-flow variables (`{{var}}` bind + resolve)

| Field | Value |
|---|---|
| **Doc ID** | DES-0008 |
| **Title** | Environment and in-flow variables (`{{var}}` bind + resolve) |
| **Status** | **Approved** |
| **Authors** | Marcos Blazquez (direction) + Clark Bot |
| **Reviewers (human)** | Marcos Blazquez (2026-09-19 — Approve / Go, relayed by Bruce) |
| **Reviewers (agent)** | Clark Bot (2026-09-19 — checklist pass; see review record) |
| **Created** | 2026-09-19 |
| **Last updated** | 2026-09-19 (dual Approve) |
| **Related REQs** | REQ-0010 (hexagonal ports); REQ-0012 (traveler); REQ-0013 (gateway/interceptors); proposed **REQ-0020** (env + in-flow variable bind/resolve) |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**); conceptual alignment with [DES-0003](0003-workflow-studio.md) flow-variable analogy (**Draft**, ideation — no UI here) |
| **Implementation** | **Authorized** for the first env/in-flow variables slice per §9 / §13 and the end-of-doc slice list — `VariableResolverPort` + pure bind helpers + `payload["vars"]` seed + TEST-VAR-*; authoring UI remains a non-goal |

---

## 0. Document posture

This SDD (now **Approved**) is the design gate for a **public kernel** contract: Environment-scoped variables and in-flow variables that bind into node fields via `{{var}}` and resolve into the traveler / run envelope at runtime.

Authoring clients (canvas inspectors, CLI, tests) may **stub** resolve until the Authorized implementation lands. Runtime resolution must remain a **public** ports & traveler contract — consumers must not invent private traveler bags that only one product understands.

**Hard rules (must survive into any future build):**

1. Reuse DES-0002 DigitalTraveler (`hextory.digital_traveler@0.1`), Gatekeeper, RequestGateway / interceptor stack — **do not fork Gatekeeper** or invent a parallel run envelope.
2. Prefer **extending existing `payload` / RequestContext patterns** over new required core traveler fields (no schema id bump in first slice; Q-VAR-1 accepted interim).
3. Public kernel stays **consumer-agnostic**: no private sibling product names in this SDD or its tests.
4. Adapters implement the same port semantics; no deploy-target fork of bind/resolve rules.
5. Secrets must not be authored as plaintext canvas defaults (align with DES-0003 analogy map); redact in logs/metrics.

**Dual review complete (2026-09-19 America/Santiago).** Marcos Blazquez + Clark Bot **Approve**. §13 is green; first-slice implementation is authorized under the constraints below.

---

## 1. Introduction / overview

### 1.1 Problem statement

Workflow nodes need configurable field values (URLs, prompts, criteria snippets, labels) that differ by **Environment** (dev / staging / prod-shaped settings) and by **in-flow** state (values set or overridden during a run). Authoring surfaces want a small bind syntax (`{{var}}`) with autocomplete.

Without a **public** resolve contract:

- Consumers invent private traveler / envelope bags.
- Adapters disagree on undefined / escape behavior.
- Gatekeeper and departments cannot rely on a shared, testable resolution path.

### 1.2 Goals

- **G1 (REQ-0020):** Define **Environment-scoped** vs **in-flow** variables and how they compose.
- **G2:** Freeze bind syntax `{{var}}` plus escape and undefined rules for the public kernel.
- **G3:** Specify how resolved values attach to a run via existing traveler `payload` + gateway `RequestContext` (run envelope) **without** forking Gatekeeper or bumping traveler core required fields in first slice.
- **G4 (REQ-0010):** Sketch a small outbound port — **`VariableResolverPort`** — that adapters and authoring clients implement (or stub).
- **G5:** Authoring clients may stub resolve until the Authorized impl is wired; runtime and stubs share the same bind grammar.

### 1.3 Success definition

- Dual review Approves without re-litigating DES-0002 traveler core or Gatekeeper (**done 2026-09-19**).
- Agents can land `VariableResolverPort` + pure bind helpers + TEST-VAR-* without private consumer schemas.
- Authoring clients can keep stubbing until the port is wired; runtime and stubs share the same bind grammar.

### 1.4 Scope

**In scope (this Approved SDD):**

- Env vs in-flow semantics, bind grammar, precedence, attachment to run envelope / traveler payload.
- `VariableResolverPort` sketch and adapter responsibilities.
- Design decisions, acceptance criteria, TEST ID plan, gate criteria.
- Traceability to REQ-0010 / REQ-0012 / REQ-0013 / proposed REQ-0020.

**Out of scope:** see Explicit non-goals (§8). First-slice port/runtime resolve is authorized while Status is **Approved** and §13 is green; authoring UI remains deferred.

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
Authoring client / CLI / HTTP client
        │  node field templates containing {{var}}
        ▼
RequestGateway + interceptors
        │  load Environment vars → seed run envelope
        │  Gatekeeper(sdd_id) unchanged
        ▼
VariableResolverPort.resolve(...)   ← adapters implement / stub
        │
        ▼
GraphRunner / department nodes
        │  fields resolved before node logic reads them
        ▼
DigitalTraveler.payload (vars bag + ordinary work data)
```

**Who calls it:** gateway / graph runtime when preparing or reading node fields; adapters supply Environment sources.  
**What it does not call:** Gatekeeper policy is unchanged — variable resolve is **not** a second allow/deny engine.

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). This SDD owns the **variable bind/resolve boundary**: grammar + envelope attachment + `VariableResolverPort`. Engine departments, traveler schema freeze, and Gatekeeper remain DES-0002.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| Environment variable source | Adapter-owned map of env-scoped name→value for a run profile | n/a |
| In-flow variable map | Workflow-/run-scoped name→value; may update as nodes run | n/a |
| Bind grammar (`{{var}}`) | Pure string substitution rules in `src/` | n/a |
| **`VariableResolverPort`** | Protocol: build/lookup effective map; resolve templates | n/a |
| Run envelope | `RequestContext` metadata + traveler `payload["vars"]` snapshot | n/a |
| Gatekeeper | Unchanged Approved-SDD gate | n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0008-A** | Two scopes: **Environment** (run-profile / deploy binding) and **in-flow** (workflow/run mutable) | Single flat global map; OS env only | Matches authoring mental model; keeps deploy config separate from run state |
| **DES-0008-B** | Bind syntax: `{{identifier}}` where `identifier` = `[A-Za-z_][A-Za-z0-9_]*` | `${var}`; Jinja; JSONPath | Small, autocomplete-friendly, no template engine in core |
| **DES-0008-C** | Escape: a backslash before `{{` yields literal `{{` (`\{{` → `{{`); unmatched `}}` left as-is | Doubling `{{{{`; HTML entities | One escape rule; readable in docs |
| **DES-0008-D** | Undefined `{{name}}` → **fail closed** (structured resolve error; do not enter node with raw token) | Leave unsubstituted; empty string | Factory quality: silent wrong values are worse than a clear fail |
| **DES-0008-E** | Attach resolved maps via existing patterns: seed `RequestContext.metadata["vars"]` at gateway; snapshot effective map under traveler **`payload["vars"]`** (additive object). No new required DigitalTraveler core field; no Gatekeeper fork | New top-level traveler field; private `extensions.<vendor>` bags; fork Gatekeeper | Honors published `@0.1` extension/payload rules; consumer-agnostic public key; **Q-VAR-1 accepted 2026-09-19** |
| **DES-0008-F** | Port name = **`VariableResolverPort`** | `RunContextPort` (broader); inline helpers only | Capability-focused like `MetricsPort`; RunContext remains the envelope *shape*, not the port name |
| **DES-0008-G** | Precedence (highest wins): **in-flow** > **Environment** > (optional adapter defaults). Same name in both scopes: in-flow wins | Env wins; error on collision | In-flow is run-local intent; env is baseline |
| **DES-0008-H** | First-slice impl authorized after dual Approve; authoring MAY stub the port until wired | Soft-allow Draft runtime | Hard rule: only Approved SDDs authorize production resolve path |

---

## 3. Data design

### 3.1 Entities / state

| Entity | Key fields | Lifecycle |
|---|---|---|
| DigitalTraveler | unchanged DES-0002-G / `hextory.digital_traveler@0.1` | created → routed → shipped / escalated / denied |
| `payload["vars"]` | object map `string → JSON-compatible scalar/object` (first slice: prefer string values for bind) | seeded at accept; updated when in-flow vars change; checkpointed with traveler |
| Environment profile | adapter-defined id + name→value map (not a core traveler field) | loaded per run by adapter wiring |
| In-flow vars | name→value declared on workflow and/or written by nodes | mutable during run within policy |
| RequestContext.metadata["vars"] | effective map mirror for interceptors / pre-traveler phase | lives for the request; copied into traveler payload on create |
| ResolveError | code, missing names[], template snippet (redacted) | raised/returned on undefined bind |

No traveler **core schema** change in first slice. Additive use of `payload["vars"]` is allowed under `@0.1` (work inputs bag already exists). Follow-up: note the reserved key in [`docs/contracts/digital-traveler-0.1.md`](../contracts/digital-traveler-0.1.md) (**Q-VAR-1 accepted**).

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
RunRequest(sdd_id, workflow_id, payload, env_profile?)
  → Interceptors (DES-0002-H order unchanged)
  → Adapter loads Environment map for env_profile
  → VariableResolverPort.merge(env, in_flow_from_payload, defaults)
       → RequestContext.metadata["vars"] = effective
  → Gatekeeper(Approved?)  —— unchanged ——
  → Create DigitalTraveler with payload including payload["vars"] = effective
  → Before each node field read:
       VariableResolverPort.resolve_template(field, effective) → concrete value
  → Node may write in-flow updates → merge into payload["vars"] (in-flow wins)
```

**Ordinary payload keys** (non-`vars`) remain free for department work data. Bind resolution applies to **node field templates** (and any explicit resolve call sites), not to every nested string inside `payload` by default (**Q-VAR-2 accepted**: string fields only in first slice).

### 3.3 Persistence & retention

Same checkpointer ports as DES-0002 / adapter SDDs. `payload["vars"]` persists with the traveler snapshot.

| Concern | Rule |
|---|---|
| Secrets | Do not place secrets in authored defaults; adapters MAY inject secret-backed env vars at resolve time without writing secret values into canvas artifacts |
| Logs / metrics | Never label or log raw secret values; redact resolve error snippets |
| PII | Treat var values like payload: potentially sensitive |

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| Local CLI | CLI | n/a (local) | Optional `--env-profile` / payload `vars` overrides in Authorized impl |
| On-prem / AWS HTTP | HTTP JSON | per adapter SDD | Same semantic body: optional env profile id; payload may include `vars` |
| In-process (tests) | Python API | n/a | Fake `VariableResolverPort` with fixed maps |

Gatekeeper still requires Approved `sdd_id` for the **workflow** being run. This SDD’s own status gates **implementation** of the port; it does not add a second gate dimension.

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| **`VariableResolverPort`** | Merge scopes; resolve `{{var}}` templates | Undefined → fail closed (DES-0008-D); do not invoke node with unresolved binds |
| Environment source (adapter) | Load env-scoped map | Missing profile → deny or empty map per adapter policy (document in impl; default: fail closed if profile id given but missing) |
| Checkpointer | Persist traveler including `payload["vars"]` | Same as DES-0002 |
| Gatekeeper | Unchanged | Variable errors are not gate denials |

### 4.3 Events / messages

Reuse DES-0002 run lifecycle events. Optional soft signal (post-Approval): audit note when resolve fails (missing names). No new required broker topics.

---

## 5. Component design

### 5.1 Core (pure) logic

Allowed in `src/` (Authorized first slice):

```text
# Port sketch (illustrative — not implementation)

class VariableResolverPort(Protocol):
    def effective_vars(
        self,
        *,
        env: Mapping[str, Any],
        flow: Mapping[str, Any],
        defaults: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge scopes: flow > env > defaults (DES-0008-G)."""
        ...

    def resolve_template(
        self,
        template: str,
        vars: Mapping[str, Any],
    ) -> str:
        """Substitute {{identifier}}; honor \\{{ escape; undefined → error."""
        ...

    def resolve_fields(
        self,
        fields: Mapping[str, Any],
        vars: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Resolve string fields; pass through non-strings unchanged (first slice)."""
        ...
```

- Pure bind helpers (regex / scanner) with no I/O.
- Optional thin gateway hook: copy `metadata["vars"]` → `payload["vars"]` on traveler create.
- Default no-op / identity stub **only** for tests that do not exercise binds; production wiring must use a real resolver when templates are present.

Forbidden in `src/`:

- Product-specific traveler bags, private vendor extension schemas as the *only* contract, OS env reads, secret-store SDKs (those stay in adapters).

### 5.2 Adapters

| Piece | Design |
|---|---|
| Local CLI | File/JSON env profile or inline `--var`; inject `VariableResolverPort` |
| On-prem / AWS | Load env profile from config store / parameter source; same port |
| Authoring clients | May **stub** `resolve_template` (echo or static map) until Authorized impl is wired; must use the same `{{var}}` grammar |
| Fakes in `tests/` | Scripted maps + undefined-name cases |

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Identifier | `[A-Za-z_][A-Za-z0-9_]*` inside `{{` `}}` |
| Escape | `\{{` → literal `{{`; resolver consumes one backslash |
| Undefined | Fail closed with structured error listing missing names |
| Precedence | in-flow > Environment > defaults |
| Non-string templates | First slice: only resolve `str` field values; nested object walk deferred (**Q-VAR-2 accepted**) |
| Collision | Same key in env and flow: flow wins (no error) |
| Empty string value | Allowed (defined); distinct from undefined |
| Gatekeeper | Never consulted for var presence; Approved SDD still required to run workflows |

---

## 6. UI (if any)

**N/A — no UI in this SDD.** Autocomplete and inspectors belong to authoring clients under other Draft ideation (DES-0003). This document only requires that those clients eventually call the same public grammar / port.

```
[Visual placeholder: CLI transcript]
$ hextory run --sdd DES-0002 --workflow starter_factory \
    --env-profile staging \
    --payload '{"vars":{"flow_greeting":"hi"},"prompt":"Say {{flow_greeting}} to {{region}}"}'
# Authorized resolve: region from Environment, flow_greeting from in-flow;
# unresolved {{missing}} → structured failure before assembly work
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-1 | Additive `payload["vars"]` is acceptable under `@0.1` without schema bump | Reviewers require top-level field | **Q-VAR-1 accepted** — additive note under `@0.1`, no id bump |
| A-2 | DES-0002 interceptor order can host env merge without new gate stage | Ordering fights idempotency | Merge vars after idempotency replay load; document in impl slice |
| A-3 | Authoring stubs will not ship divergent grammars | Split-brain `{{var}}` | Freeze grammar in this SDD; shared test vectors in Authorized impl |
| A-4 | Dual review before any resolve implementation merge | Agents implement from Draft | Gatekeeper + CONTRIBUTING + §13 (**done 2026-09-19**) |

---

## 8. Explicit non-goals

- **NG1:** No Gatekeeper fork / soft-allow; variable resolve is not a second design-doc gate.
- **NG2:** No private traveler schemas or consumer-only envelope bags as the public contract.
- **NG3:** No authoring UI, canvas autocomplete implementation, or web app code in this SDD.
- **NG4:** No identity provider / hosted auth product design.
- **NG5:** No Jinja/Handlebars/full template language in core.
- **NG6:** No requirement to resolve every string inside arbitrary payload blobs (fields-first).
- **NG7:** No Cucumber / Gherkin toolchain.
- **NG8:** No real cloud account deploy from the implementation PR or CI.
- **NG9:** No private sibling product names in this public doc or its tests.

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement **only after** gate criteria (§13) are green (Status **Approved** — **done**).

| ID | Criterion | Verification method |
|---|---|---|
| AC-VAR-01 | `VariableResolverPort` exists under `src/ports/` with no adapter I/O imports | TEST-VAR-01 + TEST-0010 |
| AC-VAR-02 | `{{name}}` substitutes from effective map; `\{{` escapes | TEST-VAR-02 |
| AC-VAR-03 | Undefined name → fail closed (no raw token passed to node) | TEST-VAR-03 |
| AC-VAR-04 | Precedence: in-flow overrides Environment for the same key | TEST-VAR-04 |
| AC-VAR-05 | Effective map snapshot appears under `payload["vars"]` on accepted traveler | TEST-VAR-05 |
| AC-VAR-06 | Gatekeeper behavior unchanged for Approved/Draft SDD runs | TEST-VAR-06 / existing gate tests |
| AC-VAR-07 | Behavior tests use Given/When/Then style in ordinary pytest | TEST-VAR-07 |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Undefined `{{var}}` | Resolver | Structured failure; do not run node body with unresolved binds | Fix var definition or template; re-run (not quality rework by default) |
| Missing env profile id | Adapter load | Fail closed (recommended) | Supply profile |
| Secret leakage in logs | Review / tests | Redact; treat as defect | Fix adapter logging |
| Gate deny (workflow SDD) | Gatekeeper | Structured denial | Unrelated to vars |
| Impl without Approved SDD / §13 green | Process / review | Reject | Dual review + status hygiene |

**Rework policy:** Variable resolve failures are **pre-node / request** failures, not Quality FAIL→assembly rework, unless a workflow SDD explicitly maps them. Default max rework (3) unchanged for quality loops.

---

## 11. Human + agent review checklist

Reviewers must check each item. Architecture-critical items require **human** sign-off.

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☑ | ☑ | Yes |
| 2 | Architecture fits hexagonal / factory rules; no Gatekeeper fork | ☑ | ☑ | Yes |
| 3 | Interfaces and failure modes are specified | ☑ | ☑ | Yes |
| 4 | Acceptance criteria are testable | ☑ | ☑ | Yes |
| 5 | Traceability IDs are complete and unique | ☑ | ☑ | Yes |
| 6 | Gate criteria are unambiguous | ☑ | ☑ | Yes |
| 7 | Security / privacy / compliance touched? (secrets, redaction) | ☑ | ☑ | Yes |
| 8 | Glossary terms used consistently | ☑ | ☑ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☑ | ☑ | No |
| 10 | No implementation leakage that bypasses this SDD; no private product names | ☑ | ☑ | Yes |
| 11 | Port name `VariableResolverPort` and `payload["vars"]` attachment acceptable | ☑ | ☑ | Yes |
| 12 | Q-VAR-1 / Q-VAR-2 interims acceptable (additive `@0.1` note; string fields only) | ☑ | ☑ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | Marcos Blazquez | 2026-09-19 America/Santiago | **Approve** (Go, relayed by Bruce) |
| Agent reviewer | Clark Bot | 2026-09-19 America/Santiago | **Approve** |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| REQ-0020 (proposed) | Env + in-flow variables; `{{var}}` bind/resolve | DES-0008-A…H | TEST-VAR-01…07 | |
| REQ-0010 | Hexagonal ports | DES-0008-F | TEST-VAR-01, TEST-0010 | |
| REQ-0012 | DigitalTraveler; no core fork | DES-0008-E | TEST-VAR-05 | additive `payload["vars"]` |
| REQ-0013 | Gateway + interceptors | DES-0008-E | TEST-VAR-06 | metadata seed; Gatekeeper unchanged |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

All of the following must be true:

- [x] Status is **Approved** (both human and agent reviews recorded).
- [x] All **Critical** checklist items signed off by a human.
- [x] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [x] Non-goals and failure/rework policy are non-empty and specific.
- [x] Acceptance criteria are binary/testable (no vague “should be good”).
- [x] No open **blocking** questions in §15 (or each has an approved interim decision) — **Q-VAR-1/2 accepted as approved interims** (Marcos + Clark, 2026-09-19); soft Q-VAR-3/4 remain open.
- [x] Maturity / process owners acknowledge this SDD in the workflow tracker (when tooling exists).
- [x] `config/sdd_status.json` lists `"DES-0008": "Approved"` matching the Status cell.

**Only when every box is checked may agents generate implementation for this port/runtime path.**

**Current state:** Status is **Approved** — §13 is **green**. First-slice `VariableResolverPort` implementation is authorized. Authoring stubs remain allowed until the port is wired.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **Environment-scoped var** | Name/value bound to a run profile / deploy binding; baseline for a run |
| **In-flow var** | Name/value scoped to the workflow/run; may change during execution |
| **Bind** | Author-time reference `{{identifier}}` inside a node field template |
| **Resolve** | Runtime substitution of binds using the effective variable map |
| **Effective map** | Merged view after precedence (flow > env > defaults) |
| **`VariableResolverPort`** | Public kernel port for merge + template resolve |
| **Run envelope** | RequestContext + traveler payload vars snapshot for one run |
| **Fail closed (undefined)** | Missing name aborts resolve; raw `{{name}}` must not execute as a value |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) and [0002-factory-engine.md](0002-factory-engine.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-VAR-1** | Document `payload["vars"]` in `digital-traveler-0.1.md` after Approval, or wait for `@0.2`? | Dual review | Before Approval (blocking unless interim accepted) | **Accepted 2026-09-19** — additive note under `@0.1`, no id bump (Marcos + Clark dual Approve) |
| **Q-VAR-2** | Resolve nested objects / arrays inside fields in first slice? | Dual review | Before Approval (or accept interim) | **Accepted 2026-09-19** — string fields only in first slice; nested walk deferred (Marcos + Clark dual Approve) |
| **Q-VAR-3** | Allow dotted names (`{{a.b}}`) later? | Dual review | Post-MVP | Soft — first slice: flat identifiers only |
| Q-VAR-4 | Should missing env profile be deny vs empty map when id omitted vs id present? | Implementer | During first impl slice | Soft — omit id → empty env; present-but-missing → fail closed |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-19 | Cursor Cloud Agent | Initial **Draft**: Env + in-flow vars, `{{var}}` grammar, `VariableResolverPort` sketch, `payload["vars"]` attachment; dual review pending; no Approval claimed |
| 2026-09-19 | Marcos Blazquez + Clark Bot | Dual review → **Approved**; Q-VAR-1/2 interims accepted; §13 green; first env/vars slice authorized (impl follow-up) |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same names as DES-0002 for gateway, traveler, gatekeeper.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions or changes-requested notes.
- **Future growth** — deeper template features get new DES ids or amendments; do not overload this SDD.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the design produces code)

| Item | Guidance |
|---|---|
| TDD | Failing test before production port wiring |
| BDD-style | Readable Given/When/Then in ordinary pytest — **not Cucumber** |
| Testing layer | `tests/unit/` + `tests/behavior/` (DES-0002-E) |
| Traceability | Link TEST-VAR-* to REQ-0020 / REQ-0010 / DES-0008-* |

### Planned TEST IDs (Authorized first slice)

| TEST ID | Intent |
|---|---|
| TEST-VAR-01 | `VariableResolverPort` importable from `src/ports`; no adapter imports in `src/` |
| TEST-VAR-02 | Substitution + `\{{` escape |
| TEST-VAR-03 | Undefined name fail closed |
| TEST-VAR-04 | In-flow overrides Environment |
| TEST-VAR-05 | Accepted traveler has `payload["vars"]` snapshot |
| TEST-VAR-06 | Gatekeeper still denies non-Approved workflow SDDs |
| TEST-VAR-07 | Behavior module uses Given/When/Then structure |

### First implementation slice (authorized after Approval)

§13 is green. Follow-up implementation (separate from this Approval docs package) may:

1. Add `src/ports/variable_resolver.py` (`VariableResolverPort` + pure helpers / default impl).
2. Wire gateway seed of `payload["vars"]` + node-field resolve call sites as needed.
3. Add TEST-VAR-01…07.
4. Amend `docs/contracts/digital-traveler-0.1.md` with the reserved `payload["vars"]` note (Q-VAR-1 accepted).
5. Do **not** implement authoring UI; do **not** fork Gatekeeper; do **not** introduce private traveler bags.

---

## Review records

Dual Approval recorded: human Approve (Marcos Blazquez, Go relayed by Bruce 2026-09-19 America/Santiago) + agent Approve ([DES-0008-agent-review-20260919.md](reviews/DES-0008-agent-review-20260919.md)).
