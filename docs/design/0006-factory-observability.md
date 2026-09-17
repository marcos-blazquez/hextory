# DES-0006 — Factory observability (metrics + operator view)

| Field | Value |
|---|---|
| **Doc ID** | DES-0006 |
| **Title** | Factory observability — gate-denial metrics and run/quality signals |
| **Status** | **Approved** |
| **Authors** | Marcos Blazquez (direction) + Clark Bot |
| **Reviewers (human)** | Marcos Blazquez (2026-09-17 — Approve in chat) |
| **Reviewers (agent)** | Clark Bot (2026-09-17 — checklist pass; see review record) |
| **Created** | 2026-09-17 |
| **Last updated** | 2026-09-17 (dual Approve) |
| **Related REQs** | REQ-0013 (gateway / gatekeeper signals); REQ-0010 (hexagonal ports); proposed **REQ-0018** (factory metrics / operator observability) |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**), [DES-0004](0004-onprem-adapter.md) (**Approved**) as the first HTTP `/metrics` host |
| **Implementation** | **Authorized** for the first observability slice per §9 / §13 and the end-of-doc slice list — MetricsPort + Prometheus `/metrics` on on-prem + local dump + Grafana-as-code + TEST-OBS-*; Studio / tracing SaaS remain non-goals |

---

## 0. Document posture

This SDD (now **Approved**) is the design gate for **factory observability beyond traveler and checkpointer artifacts**. File and Postgres checkpointers already persist DigitalTraveler state (including quality FAIL history), and on-prem HTTP returns Gatekeeper denial as structured **HTTP 403** — but those are **not** metrics, counters, histograms, or operator dashboards. Aspect **8** sits near **~52** until structured metrics and a minimal operator view exist.

**Hard rules (must survive into any future build):**

1. Metrics are **adapter-emitted** (or adapter-hosted exporters). Pure `src/` must not import Prometheus client libraries, OpenTelemetry SDKs, Grafana tooling, or FastAPI scrape routes.
2. Core may define a thin **Metrics / Telemetry port** (protocol) that records domain facts; adapters export. Prefer recording at interceptor / gateway boundaries without forking Gatekeeper.
3. Traveler contract stays `hextory.digital_traveler@0.1` / DES-0002-G — observability does not alter traveler schema.
4. Checkpointers alone **do not** satisfy this SDD; counters / histograms (or equivalent meter instruments) are required.
5. Public kernel stays product-agnostic: never name private sibling products or out-of-tree app brands; no private Studio read models.
6. DES-0003 (Studio UI) remains Draft ideation and is **out of scope** here.
7. No PII in metric labels (no payload snippets, emails, raw secrets).

**Dual review complete (2026-09-17).** Marcos Blazquez + Clark Bot **Approve**. §13 is green; first-slice implementation is authorized under the constraints below.

---

## 1. Introduction / overview

### 1.1 Problem statement

Aspect **8** (factory observability — traces, quality loops, operator signals) is stuck near **~52**. Evidence today:

- File checkpointer / FileIdempotency under local adapters.
- Postgres checkpointer for on-prem.
- Traveler `routing_history` and quality FAIL reports as artifacts.
- On-prem Gatekeeper denial as HTTP 403 JSON.

Missing: structured **metrics** for gate denials, run accepts, terminal statuses, quality FAIL, and rework counts; and a **minimal operator view** (dashboard-as-code or scrapeable summary) that is not “read the traveler JSON by hand.”

### 1.2 Goals

- **G1 (REQ-0018 / REQ-0013):** Structured **metrics** for gate denials, run accepts, terminal statuses (`shipped` / `escalated` / `denied`), quality FAIL, and rework counts.
- **G2 (REQ-0010):** Adapter-emitted metrics without polluting pure `src/` — ports for Metrics/Telemetry; adapters export.
- **G3:** First slice: **Prometheus-compatible `/metrics`** on `adapters/onprem` (and a local CLI metrics dump or sidecar sink). OpenTelemetry metrics exporter is an alternative deferred behind **Q-OBS-1** (default proposal = Prometheus).
- **G4:** Minimal operator view: **Grafana dashboard-as-code** (JSON checked into repo) **+** `/metrics` scrape — no hosted SaaS required for first slice. (HTML/JSON summary page under adapters is a fallback if Grafana-as-code is rejected — see decisions.)
- **G5:** Tests assert metric increments on gate denial and successful run (`TEST-OBS-*`).

### 1.3 Success definition

- Dual review Approves this SDD without re-litigating DES-0002 core ports or claiming checkpointers already “are” observability (**done 2026-09-17**).
- Agents implement metrics exporters and a dashboard-as-code artifact against acceptance criteria and TEST IDs without inventing architecture.
- Tests prove counters move on Gatekeeper denial and on successful shipped runs.
- Aspect-8 evidence path exists once implemented (`/metrics` + Grafana JSON + TEST-OBS-*).

### 1.4 Scope

**In scope (this Approved SDD):**

- Metrics vocabulary (names, meanings, label rules).
- Metrics/Telemetry port shape (core protocol; adapter exporters).
- First-slice host: Prometheus `/metrics` on `adapters/onprem` + local sink option.
- Grafana dashboard-as-code posture (repo-owned JSON).
- Design decisions DES-0006-A…; acceptance criteria; gate criteria; TEST ID plan.
- Traceability to REQ-0010 / REQ-0013 / proposed REQ-0018.

**Out of scope:** see Explicit non-goals (§8). Implementation authorized while Status is **Approved** and §13 is green.

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
HTTP client / CLI
        │
        ▼
adapters/onprem FastAPI  ──► RequestGateway (src/) + interceptors
        │                           │
        │                           ├── Gatekeeper → deny fact
        │                           ├── GraphRunner → terminal status fact
        │                           └── Quality → FAIL / rework facts
        │
        ├── MetricsPort (core protocol) ◄── interceptor / gateway hooks
        │         │
        │         └── adapters export Prometheus counters/histograms
        │
        ├── GET /metrics  (Prometheus scrape)
        └── Grafana dashboard JSON (as code) ── scrapes /metrics locally
```

**Who calls it:** operators, Prometheus scrapers, CI metric assertions.  
**What it calls:** adapter metric registries; optionally scrapes on-prem `/metrics`. Core emits facts through a port; it does not open scrape endpoints.

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). This SDD owns the **observability boundary**: Metrics/Telemetry port + adapter exporters + operator view artifacts. It does not fork departments or Gatekeeper.

### 2.3 High-level components

| Component | Responsibility | Department (if any) |
|---|---|---|
| Metrics / Telemetry port (`src/ports`) | Protocol for recording domain metric facts (increment/observe) without I/O libs | n/a |
| No-op / in-memory meter (tests) | Fake implementation for unit/behavior tests | n/a |
| Prometheus exporter (`adapters/onprem`) | `/metrics` scrape endpoint; register counters/histograms | n/a |
| Local CLI metrics sink (`adapters/local`) | File/stdout dump of the same instruments (**Q-OBS-3** accepted: dump, not HTTP `/metrics`) | n/a |
| Grafana dashboard JSON | Minimal operator panels for gate denial + run outcomes | n/a |
| TEST-OBS-* suite | Assert increments on denial and successful run | n/a |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0006-A** | Observability first slice = **structured metrics** (counters/histograms), not “more traveler files” | Rely on checkpointers only; logs-only | Aspect 8 explicitly needs metrics/dashboards beyond artifacts |
| **DES-0006-B** | Core exposes a **Metrics/Telemetry port**; Prometheus (or OTel) libs live only in adapters | Import `prometheus_client` in `src/`; monkey-patch gateway | Preserves DES-0002-A / TEST-0010 purity |
| **DES-0006-C** | Default export = **Prometheus-compatible `/metrics`** on `adapters/onprem` | OTel-first exporter; StatsD-only | Lowest friction for self-hosted scrape + Grafana; **Q-OBS-1 accepted 2026-09-17** |
| **DES-0006-D** | Operator view = **Grafana dashboard-as-code** (JSON in repo) + `/metrics`; no hosted SaaS required | SaaS APM day one; HTML-only summary page | Reproducible, reviewable, CI-friendly; HTML page remains soft fallback |
| **DES-0006-E** | Emit at gateway/interceptor boundaries: gate deny, run accept, terminal status, quality FAIL, rework | Instrument every department function deeply day one | Smallest verifiable vocabulary; enough for aspect-8 lift |
| **DES-0006-F** | Label cardinality is **low by default**; no PII; allow `workflow_id` + terminal `status`; allow `sdd_id` only if cardinality stays small; forbid `traveler_id` / payload labels | High-cardinality per-traveler labels | Protect scrape cost and privacy; **Q-OBS-2 accepted 2026-09-17** |
| **DES-0006-G** | Tests under `tests/adapters/` (and unit fakes) prove counter increments — TDD/BDD-style, not Cucumber | Manual scrape only | REQ-0015 alignment; TEST-OBS-* |

---

## 3. Data design

### 3.1 Entities / state

Observability does **not** change DigitalTraveler fields. Metrics are parallel signals derived from gateway outcomes.

| Entity | Key fields | Lifecycle |
|---|---|---|
| Metric fact (logical) | name, labels (low-cardinality), value delta / observation | Emitted on gateway events; aggregated by exporter |
| Counter series | e.g. `hextory_gate_denials_total`, `hextory_runs_accepted_total`, `hextory_runs_terminal_total{status=…}`, `hextory_quality_fail_total`, `hextory_rework_total` | Monotonic within process / scrape target |
| Histogram (optional first slice) | e.g. `hextory_run_duration_seconds` | Observe on terminal run |
| Dashboard artifact | Grafana JSON panels bound to the metric names above | Versioned in repo; no runtime state |

Exact Prometheus metric names may be adjusted at impl if they keep the same semantic coverage; freeze names in TEST-OBS assertions once Approved.

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
Run request → RequestGateway
  → Gatekeeper deny → MetricsPort.inc(gate_denials) → HTTP 4xx
  → accept → MetricsPort.inc(runs_accepted) → GraphRunner
      → quality FAIL → MetricsPort.inc(quality_fail) + rework_total
      → terminal shipped|escalated|denied → MetricsPort.inc(terminal{status})
Adapters flush / expose registry → GET /metrics → Prometheus / Grafana
```

### 3.3 Persistence & retention

- **Metrics series:** process-local registry (Prometheus default); retention owned by the scraper / Prometheus TSDB operator config — not by Hextory core.
- **Dashboard JSON:** git-retained as code under e.g. `adapters/onprem/observability/` or `docs/ops/grafana/` (exact path at impl).
- **PII:** forbidden in labels and metric help strings that echo payloads. Traveler ids must not be labels (**Q-OBS-2** accepted).

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| `GET /metrics` (`adapters/onprem`) | Prometheus text exposition | none or scrape token (ops choice; default open on internal network for first slice) | Scrape counters/histograms |
| Local metrics dump (`adapters/local`) | stdout / file (**Q-OBS-3** accepted) | local user | Same instruments for CLI runs without requiring FastAPI |
| Grafana import | JSON dashboard file | n/a (file) | Import into local Grafana pointing at on-prem scrape target |

Workflow routes (`POST /runs`, etc.) remain DES-0004; this SDD adds scrape/dump surfaces only.

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| MetricsPort implementations | Record facts | Never fail the business run because metrics sink is down (best-effort; log once) |
| Prometheus scraper / Grafana | Operator view | If absent, `/metrics` still serves for tests and curl |
| Core gateway events | Source of truth for when to increment | Mis-hook → TEST-OBS failures |

### 4.3 Events / messages

Map DES-0002 §4.3 logical events to metrics:

| Domain fact | Metric action (first slice) |
|---|---|
| `run.denied` (Gatekeeper) | `hextory_gate_denials_total` += 1 |
| `run.accepted` | `hextory_runs_accepted_total` += 1 |
| `quality.failed` | `hextory_quality_fail_total` += 1; `hextory_rework_total` += 1 when rework scheduled |
| `run.shipped` / `run.escalated` / terminal denied | `hextory_runs_terminal_total{status=…}` += 1 |

No required message broker. Tracing spans / distributed trace SaaS are **non-goals** for first slice.

---

## 5. Component design

### 5.1 Core (pure) logic

Allowed in `src/` after Approval:

- A **MetricsPort** (Protocol/ABC) with methods such as `increment(name, labels=…)`, `observe(name, value, labels=…)` — pure interface, no exporter imports.
- Optional thin helpers that translate gateway outcomes → metric names (still no I/O).
- Wiring: RequestGateway / interceptors accept an optional MetricsPort (default no-op).

Forbidden in `src/`:

- `prometheus_client`, OpenTelemetry SDK/API exporters, HTTP scrape servers, Grafana APIs.

### 5.2 Adapters

#### First-slice hosts (post-Approval)

| Piece | Design |
|---|---|
| `adapters/onprem` Prometheus exporter | Register instruments; expose `GET /metrics`; inject MetricsPort into gateway wiring |
| `adapters/local` sink | Dump counters at end of CLI run and/or write a scrapeable file (stdout/file; no required HTTP `/metrics`) |
| Grafana dashboard JSON | Panels: gate denials rate, accepts, terminal status breakdown, quality FAIL, rework |
| Optional later: `adapters/aws` | Same MetricsPort; CloudWatch or Prometheus-on-Lambda — **out of first slice** unless DES-0005 also Approved and amended |

#### Explicitly not first slice

- Full distributed tracing SaaS (Jaeger/Tempo/Datadog APM as mandatory).
- Private Studio read models / UI charts (DES-0003).
- PII-bearing labels.
- Claiming File/Postgres checkpointer artifacts satisfy AC metrics criteria.

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Best-effort metrics | Metric sink failures must not change Gatekeeper or traveler outcomes |
| Label rules | Default low cardinality; follow Q-OBS-2 accepted interim |
| Denial vs auth | Auth 401 (DES-0004) is **not** a gate denial metric; only Gatekeeper denials increment `hextory_gate_denials_total` |
| Rework counting | Increment rework when core schedules rework after Quality FAIL (not on every quality check PASS) |
| Naming | Prefer `hextory_` prefix; keep stable once tests freeze names |

---

## 6. UI (if any)

**Minimal operator view — not a product UI.** Grafana dashboard-as-code is the first-slice “UI.” No React Studio. Optional simple HTML/JSON summary page under adapters is a soft alternative if dual review rejects Grafana JSON (**not** the default proposal).

```
[Visual placeholder: Grafana panels]
┌─────────────────────────────┐  ┌─────────────────────────────┐
│ Gate denials (rate)         │  │ Runs accepted               │
└─────────────────────────────┘  └─────────────────────────────┘
┌─────────────────────────────┐  ┌─────────────────────────────┐
│ Terminal status breakdown   │  │ Quality FAIL / rework       │
└─────────────────────────────┘  └─────────────────────────────┘
```

CLI transcript (local sink sketch):

```
$ python -m adapters.local.cli run --sdd DES-9999 --workflow starter_factory
… denial …
# metrics dump
hextory_gate_denials_total 1
hextory_runs_accepted_total 0
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-01 | DES-0002/0004 remain Approved; on-prem FastAPI can host `/metrics` | Nowhere to scrape | Local sink still satisfies CLI path; on-prem is preferred host |
| A-02 | Prometheus text format is acceptable default (**Q-OBS-1** accepted) | Late OTel rewrite | Port abstracts recording; exporter is swappable |
| A-03 | Operators can run Grafana locally or skip UI and use curl `/metrics` | Dashboard unused | Dashboard-as-code still reviewable; tests assert metrics not Grafana |
| A-04 | MetricsPort can be injected without core schema change | Forced traveler fields | Keep metrics orthogonal to traveler |
| A-05 | Checkpointer artifacts remain useful debug aids but are not the success metric for this SDD | Score confusion | Explicit NG + AC language |

---

## 8. Explicit non-goals

- **NG1:** Treating File/Postgres checkpointers or traveler JSON as sufficient “observability” for this SDD’s acceptance criteria.
- **NG2:** Full distributed tracing SaaS or mandatory OpenTelemetry traces in first slice.
- **NG3:** Private Studio read models, React charts, or DES-0003 UI work.
- **NG4:** PII (or traveler payload content) in metric labels.
- **NG5:** Importing Prometheus / OTel / Grafana libraries into `src/`.
- **NG6:** Shipping metrics exporter implementation while this SDD is still Draft.
- **NG7:** Requiring a hosted Grafana Cloud / vendor SaaS account.
- **NG8:** Changing DigitalTraveler `@0.1` contract for observability fields.

---

## 9. Acceptance criteria for agent implementation

Concrete, testable criteria. Agents may implement **only after** gate criteria (§13) are green (Status **Approved**).

| ID | Criterion | Verification method |
|---|---|---|
| AC-01 | MetricsPort exists in `src/ports`; no Prometheus/OTel imports under `src/` | TEST-OBS-01 + TEST-0010 |
| AC-02 | Gatekeeper denial increments `hextory_gate_denials_total` (or frozen equivalent name) | TEST-OBS-02 |
| AC-03 | Successful accepted→shipped run increments accept + terminal{status=shipped} counters | TEST-OBS-03 |
| AC-04 | Quality FAIL increments quality-fail counter; rework path increments rework counter | TEST-OBS-04 |
| AC-05 | `adapters/onprem` exposes Prometheus-compatible `GET /metrics` including the above series | TEST-OBS-05 |
| AC-06 | Grafana dashboard JSON as code exists and references the frozen metric names | TEST-OBS-06 / file review |
| AC-07 | Local adapter provides a stdout/file metrics dump per Q-OBS-3 | TEST-OBS-07 |
| AC-08 | Metric labels obey cardinality/PII rules (no traveler payload; no emails) | TEST-OBS-08 |
| AC-09 | Adapter tests live under `tests/adapters/` (plus unit fakes) with BDD-style readability; not Cucumber | layout / docstrings |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Metrics sink exception | Exporter/port catch | Log; continue run | Fix exporter; do not alter traveler |
| Scrape endpoint down | Ops / CI curl | Fail TEST-OBS-05; business API may still work | Restore `/metrics` route |
| Miscounted denial (auth 401 counted as gate deny) | TEST-OBS-02 / review | Fix instrumentation boundary | TDD fix |
| High-cardinality label explosion | Scrape cardinality alerts | Drop labels; follow Q-OBS-2 | Amend label policy |
| Quality FAIL without metric | TEST-OBS-04 | Fail CI | Wire quality interceptor |

**Rework policy defaults:** inherit DES-0002-H for workflow runs. Metrics bugs do not create traveler rework loops; they fail TEST-OBS and block merge of the observability slice.

---

## 11. Human + agent review checklist

Reviewers must check each item. Architecture-critical items require **human** sign-off.

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☑ | ☑ | Yes |
| 2 | Architecture fits hexagonal / factory rules (no core pollution) | ☑ | ☑ | Yes |
| 3 | Interfaces and failure modes are specified | ☑ | ☑ | Yes |
| 4 | Acceptance criteria are testable | ☑ | ☑ | Yes |
| 5 | Traceability IDs are complete and unique | ☑ | ☑ | Yes |
| 6 | Gate criteria are unambiguous | ☑ | ☑ | Yes |
| 7 | Security / privacy / compliance touched? (no PII labels) | ☑ | ☑ | Yes |
| 8 | Glossary terms used consistently | ☑ | ☑ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☑ | ☑ | No |
| 10 | No implementation leakage that bypasses this SDD | ☑ | ☑ | Yes |
| 11 | Checkpointers explicitly insufficient; counters required | ☑ | ☑ | Yes |
| 12 | Q-OBS-1 interim (Prometheus default) acceptable to Marcos or resolved | ☑ | ☑ | Yes |
| 13 | Studio / tracing SaaS explicitly non-goals for first slice | ☑ | ☑ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | Marcos Blazquez | 2026-09-17 | **Approve** |
| Agent reviewer | Clark Bot | 2026-09-17 | **Approve** |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| **REQ-0018** | Factory metrics / operator observability (proposed) | **DES-0006-A…G** | TEST-OBS-01…08 | New REQ for aspect-8 path |
| REQ-0010 | Hexagonal engine core + ports | DES-0002-A, **DES-0006-B** | TEST-OBS-01, TEST-0010 | MetricsPort only in core |
| REQ-0013 | Gateway + interceptors + gatekeeper | DES-0006-E | TEST-OBS-02, TEST-OBS-03 | Emit at gateway boundaries |
| REQ-0015 | Testing layer + TDD/BDD-style | DES-0006-G | TEST-OBS-* | `tests/adapters/` + unit fakes |
| REQ-0003 | Multi-target factory intent (ops readiness) | DES-0006-C/D | TEST-OBS-05…07 | On-prem + local sinks |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

All of the following must be true:

- [x] Status is **Approved** (both human and agent reviews recorded).
- [x] All **Critical** checklist items signed off by a human.
- [x] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [x] Non-goals and failure/rework policy are non-empty and specific.
- [x] Acceptance criteria are binary/testable (no vague “should be good”).
- [x] No open **blocking** questions in §15 (or each has an approved interim decision) — **Q-OBS-1/2/3 accepted as approved interims** (Marcos + Clark, 2026-09-17); soft Q-OBS-4…6 remain open.
- [x] Maturity / process owners acknowledge this SDD in dual review (Marcos + Clark).

**Only when every box is checked may agents generate implementation for this workflow.**

**Post-approval note:** Gate criteria are green. Implementation may proceed for the **first observability slice only** (MetricsPort + Prometheus `/metrics` on on-prem + local dump/sink + Grafana dashboard-as-code + TEST-OBS-* per §9 and end-of-doc slice list). Studio / tracing SaaS remain non-goals (NG2/NG3).

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **MetricsPort** | Core protocol for recording metric facts without exporter libraries |
| **Gate-denial metric** | Counter incremented only on Gatekeeper refusal (not auth 401) |
| **`/metrics`** | Prometheus text exposition endpoint on `adapters/onprem` |
| **Dashboard-as-code** | Grafana JSON (or equivalent) versioned in git |
| **Low-cardinality labels** | Label keys/values safe for long-term scrape (no per-traveler ids by default) |
| **Checkpointer artifact** | Persisted traveler/checkpoint document — useful debug, **not** a substitute for metrics here |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md) and [0002-factory-engine.md](0002-factory-engine.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-OBS-1** | Prometheus `/metrics` first vs OpenTelemetry metrics exporter first? | Marcos | Before Approval (blocking unless interim accepted) | **Accepted 2026-09-17** — Prometheus `/metrics` on on-prem first; OTel later additive (Marcos + Clark dual Approve) |
| **Q-OBS-2** | Label cardinality rules — allow `sdd_id`? `workflow_id`? forbid `traveler_id`? | Marcos | Before Approval (or accept interim) | **Accepted 2026-09-17** — allow `workflow_id` + terminal `status`; allow `sdd_id` only if cardinality stays small; **forbid** `traveler_id` and payload-derived labels (Marcos + Clark dual Approve) |
| **Q-OBS-3** | Must `adapters/local` expose `/metrics`, or is file/stdout dump enough for first slice? | Marcos | Before Approval (or accept interim) | **Accepted 2026-09-17** — stdout/file metrics dump for local CLI; HTTP `/metrics` required only on on-prem (Marcos + Clark dual Approve) |
| Q-OBS-4 | Exact Prometheus metric name freeze + histogram buckets? | Implementer after Approval | During first impl slice | Soft — freeze in TEST-OBS |
| Q-OBS-5 | Dashboard path (`adapters/onprem/observability/` vs `docs/ops/grafana/`)? | Dual review | Soft | Soft |
| Q-OBS-6 | Scrape auth for `/metrics` (open internal vs bearer)? | Ops / Marcos | Before production-hardening | Soft — default open on Compose network for first slice |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-17 | Marcos Blazquez (direction) + Clark Bot | Initial Draft: MetricsPort + Prometheus `/metrics` + Grafana dashboard-as-code; gate-denial and run/quality counters; checkpointers insufficient; no implementation |
| 2026-09-17 | Marcos Blazquez + Clark Bot | Dual review → **Approved**; Q-OBS-1/2/3 interims accepted; §13 green; first observability slice authorized (impl follow-up) |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same gateway/gatekeeper/traveler names as DES-0002 / DES-0004.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions or changes-requested notes.
- **Future growth** — OTel and AWS exporters can bind the same MetricsPort later.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Failing TEST-OBS before exporter/wiring code |
| BDD-style | Readable Given/When/Then in ordinary pytest — **not Cucumber** |
| Testing layer | `tests/adapters/` for `/metrics` + denial/run increments; `tests/unit/` for MetricsPort fakes |
| Traceability | Link TEST-OBS-* to REQ-0018 / REQ-0010 / REQ-0013 / DES-0006-* |

### First implementation slice (authorized after Approval)

§13 is green. Follow-up implementation (separate from this Approval docs package) may:

1. Add MetricsPort to `src/ports` + no-op/fake; wire gateway/interceptors to emit facts.
2. Expose Prometheus `GET /metrics` on `adapters/onprem`; add local CLI metrics dump/sink.
3. Check in Grafana dashboard JSON as code referencing frozen metric names.
4. Add TEST-OBS-01…08 under `tests/adapters/` (and unit fakes).
5. Do **not** add tracing SaaS, Studio UI, PII labels, or claim checkpointers satisfy this SDD.

---

## Review records

Dual Approval recorded: human Approve (Marcos Blazquez, chat 2026-09-17) + agent Approve ([DES-0006-agent-review-20260917.md](reviews/DES-0006-agent-review-20260917.md)).
