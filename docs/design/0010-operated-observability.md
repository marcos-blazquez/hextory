# DES-0010 — Operated observability (scrape, alerts-as-code, traveler journeys)

| Field | Value |
|---|---|
| **Doc ID** | DES-0010 |
| **Title** | Operated observability — real scrape, alert rules as code, traveler-journey tracking, AWS metrics wiring |
| **Status** | Draft |
| **Authors** | Marcos Blazquez (direction) + Clark Bot (draft) |
| **Reviewers (human)** | TBD — Marcos Blazquez |
| **Reviewers (agent)** | TBD — Clark Bot |
| **Created** | 2026-09-28 |
| **Last updated** | 2026-09-28 (r2: proposed defaults for blocking questions) |
| **Related REQs** | REQ-0010 (hexagonal ports); REQ-0012 (traveler); REQ-0013 (gateway / gatekeeper signals); REQ-0018 (factory metrics — DES-0006); proposed **REQ-0022** (operated observability: scrape, alerting, journey tracking) |
| **Supersedes** | none — **extends** [DES-0006](0006-factory-observability.md) |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**), [DES-0004](0004-onprem-adapter.md) (**Approved**), [DES-0005](0005-aws-adapter.md) (**Approved**), [DES-0006](0006-factory-observability.md) (**Approved**) |
| **Implementation** | **Not authorized** while Status is Draft — no exporter, rule, journey, or AWS metrics code may merge until dual Approve + §13 green |

---

## 0. Document posture

DES-0006 delivered the **first observability slice**: `MetricsPort` in `src/ports`, five frozen counters emitted at gateway boundaries, Prometheus text exposition on `adapters/onprem` `GET /metrics`, a local stdout/file dump, and a Grafana dashboard as code. That slice is *instrumented*, not *operated*: nothing scrapes it by default, nothing alerts, a single traveler's path across stations can only be reconstructed by reading traveler JSON, and AWS runs emit no metrics (the AWS smoke metrics item was explicitly deferred).

This Draft specifies the **operated** layer on top of DES-0006 without re-litigating it.

**Hard rules (must survive into any future build):**

1. Everything in DES-0006 §0 still holds: exporter libraries live only in adapters; `src/` stays pure (TEST-0010); no PII or per-traveler ids in metric labels; traveler contract stays `hextory.digital_traveler@0.1`.
2. **Vendor-neutral by default.** The scrape format is Prometheus text exposition (OpenMetrics-compatible); alert rules use the Prometheus rule-file format, which Prometheus-compatible backends consume. No hosted SaaS account is required to run, test, or evaluate anything in this SDD.
3. **Journeys are events, not labels.** Correlation ids and traveler ids appear in journey events / structured logs and the journey timeline API — never as metric labels.
4. **Alert rules are code with tests.** Every rule ships with a unit test that proves it fires and that it stays quiet; CI fails on an untested rule.
5. No real cloud deploy from CI (DES-0005 NG1). AWS metrics are proven in CI by format tests and live only via manual, opt-in smoke.
6. Observability never fails a business run (DES-0006 `SafeMetrics` posture extends to journeys).
7. Public kernel stays consumer-agnostic: no private product names, no consumer-specific stations or dashboards.

---

## 1. Introduction / overview

### 1.1 Problem statement

Operators today can see counters if they curl `/metrics`, but they cannot:

- Rely on a scraper being configured (no scrape config, no Compose service).
- Be told when something is wrong (no alert rules; no thresholds; no tests for thresholds).
- Follow one traveler across stations (assembly → quality → packaging, rework loops) as an ordered, timed journey, or tie it to the caller's request id.
- See AWS-hosted runs at all (Lambda path injects no `MetricsPort` by default).
- Detect a traveler that entered the factory and never reached a terminal status.

Aspect 8 (factory observability) is capped at first-slice level until these exist.

### 1.2 Goals

- **G1 (REQ-0022):** A **real scrape path**: repo-owned scrape config + an opt-in Compose `observability` profile that scrapes on-prem `/metrics` and loads the existing dashboard.
- **G2 (REQ-0022):** **Alert rules as code** for gate-failure rate, quality-failure rate, stuck traveler, run error rate, and scrape-target down — each with a **unit-test harness** run in CI.
- **G3 (REQ-0022 / REQ-0012):** **Traveler-journey tracking**: a correlation id carried from the inbound request through every station, journey events per station transition, and a journey timeline readable via API / CLI.
- **G4 (REQ-0018):** New low-cardinality instruments needed by the alerts: run duration, station duration, run errors, in-flight travelers, oldest in-flight age.
- **G5 (REQ-0022 / DES-0005):** **AWS metrics wiring**: the same `MetricsPort` facts reach CloudWatch from Lambda without new runtime dependencies, verified by CI format tests and a manual opt-in smoke (AWS-SMOKE-003).
- **G6 (REQ-0010):** All of the above via ports in `src/` and exporters in `adapters/`; zero new imports of exporter libraries in `src/`.

### 1.3 Success definition

- Dual review Approves (or requests changes) without re-opening DES-0006 decisions.
- After Approval, `docker compose --profile observability up` gives a scraping Prometheus + dashboard against the on-prem API with no manual config.
- CI runs alert-rule unit tests and fails if a rule is added without a test or references an unknown metric.
- For any run, an operator can fetch an ordered, timed journey by traveler id and find it by correlation id in structured logs.
- A Lambda-hosted run emits the frozen counters as CloudWatch metrics (proven by AWS-SMOKE-003 evidence, manual).

### 1.4 Scope

**In scope:**

- Additive `MetricsPort` capability (gauges) and new metric names/labels.
- `JourneyPort` + pure journey timeline builder; correlation-id policy.
- On-prem: journey endpoint, in-flight tracker/collector, scrape config, Compose profile, alert rules + tests.
- Local CLI: journey command + journey dump.
- AWS: CloudWatch Embedded Metric Format (EMF) `MetricsPort` adapter + structured journey log lines; opt-in wiring; smoke procedure.
- Acceptance criteria, TEST-OOB-* plan, gate criteria, traceability.

**Out of scope:** see Explicit non-goals (§8).

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
Client (HTTP / CLI / Lambda event)  ── X-Correlation-Id (optional)
        │
        ▼
RequestGateway (src/) ── interceptors ── Gatekeeper
        │  correlation_id resolved (inbound or = traveler_id)
        │
        ├── MetricsPort ──► PrometheusMetrics (onprem)  ──► GET /metrics ◄── Prometheus (Compose profile)
        │                ├► InMemoryMetrics (local dump)                        │
        │                └► EmfMetrics (aws; stdout JSON) ──► CloudWatch        ├─ rules: alerts/*.rules.yml
        │                                                                        └─ Alertmanager (optional, null receiver)
        ├── JourneyPort  ──► InflightTracker + JSON log sink (onprem) ──► gauges on /metrics
        │                ├► file/stdout sink (local)
        │                └► JSON log sink (aws; CloudWatch Logs)
        │
        └── GraphRunner (pure / LangGraph) ── station steps ── routing_history (append-only)
                                                        │
                                  build_journey_timeline(traveler) ──► GET /runs/{id}/journey · hextory journey <id>
```

**Who calls it:** operators, Prometheus-compatible scrapers, alert evaluators, CI.  
**What it calls:** adapter exporters and log sinks only. Core emits facts; it never opens sockets or writes files.

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). This SDD adds one new port (`JourneyPort`), extends one port additively (`MetricsPort.set_gauge`), adds one pure domain builder (journey timeline), and adds adapter-side exporters, collectors, and ops-as-code artifacts. No department, Gatekeeper, or traveler-schema change.

### 2.3 High-level components

| Component | Placement | Responsibility |
|---|---|---|
| `MetricsPort.set_gauge` (additive) | `src/ports/metrics.py` | Record point-in-time values; `NoOpMetrics` / `InMemoryMetrics` / `SafeMetrics` gain it |
| New metric name constants + `station` label key | `src/ports/metrics.py` | Frozen names for DES-0010 instruments; `station` added to `ALLOWED_LABEL_KEYS` |
| `JourneyEvent` + `JourneyPort` + `NoOpJourney` / `InMemoryJourney` | `src/ports/journey.py` | Record station-transition facts with correlation id |
| Correlation-id policy | `src/policies/correlation.py` (pure) + interceptor in `src/policies/interceptors.py` | Validate inbound id; default to `traveler_id` |
| `build_journey_timeline()` | `src/domain/journey.py` (pure) | Ordered, timed station timeline from `routing_history` |
| Gateway hooks | `src/gateway/request_gateway.py` | Emit journey events, run duration, station durations, run errors (best-effort) |
| `PrometheusMetrics` gauges/histograms + `InflightCollector` | `adapters/onprem/prometheus_metrics.py`, `adapters/onprem/journey.py` | Export new instruments; in-flight count + oldest age |
| `GET /runs/{traveler_id}/journey` | `adapters/onprem/app.py` | Journey timeline JSON (same auth as `/runs`) |
| Scrape config + Compose profile | `adapters/onprem/observability/prometheus.yml`, `docker-compose.yml` (`profiles: [observability]`) | Real scrape of `api:8080/metrics`; dashboard provisioning |
| Alert rules + rule tests | `adapters/onprem/observability/alerts/hextory.rules.yml`, `.../alerts/hextory.rules.test.yml` | Alerts as code + synthetic-series unit tests |
| Local journey CLI + dump | `adapters/local/cli.py`, `adapters/local/journey_dump.py` | `hextory journey <traveler_id>`; JSONL journey sink |
| `EmfMetrics` + JSON journey log sink | `adapters/aws/emf_metrics.py`, `adapters/aws/journey_log.py`; wiring in `adapters/aws/wiring.py` | CloudWatch metrics via EMF on stdout; opt-in by env |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0010-A** | Scrape format stays **Prometheus text exposition** from the existing on-prem `/metrics`; add repo-owned scrape config + opt-in Compose profile | OTLP push first; new metrics port/process | Vendor-neutral, already implemented; OTLP remains additive later (DES-0006 Q-OBS-1) |
| **DES-0010-B** | Alert rules in **Prometheus rule-file YAML**, tested with rule unit tests (`promtool test rules`) in a dedicated CI job, plus a pytest lint that cross-checks metric names | Grafana-managed alerts; Python re-implementation of PromQL | Standard, portable format; real evaluator semantics; lint keeps names in sync with `src/ports/metrics.py` |
| **DES-0010-C** | **Correlation id** = validated inbound `X-Correlation-Id` (HTTP) / `--correlation-id` (CLI) / event field (AWS); else `traveler_id` | Always mint a new id; W3C `traceparent` only | Lets callers (incl. DES-0009 consumers) join their logs; safe default needs no caller change |
| **DES-0010-D** | Correlation id stored as `payload["_correlation_id"]` (same reserved-underscore pattern as `_deadline`); **no traveler schema bump** | New top-level traveler field (`@0.2`) | Honors DES-0006 NG8 / traveler `@0.1`; promotion to a first-class field is an open question (Q-OOB-2) |
| **DES-0010-E** | **Journey timeline** is derived purely from append-only `routing_history` (`seq`, `at`, `node_id`, `decision`) | Separate journey store | Single source of truth; works for pure and LangGraph runners and after restart via checkpointer |
| **DES-0010-F** | **JourneyPort** events emitted at gateway boundaries (accepted, station transitions after run, terminal, resume) — best-effort like `SafeMetrics` | Instrument inside each department; runner callbacks | No department changes; live per-step hook deferred to Q-OOB-3 |
| **DES-0010-G** | New instruments: `hextory_run_duration_seconds` (histogram), `hextory_station_duration_seconds{workflow_id,station}` (histogram), `hextory_run_errors_total{workflow_id,kind}` (counter), `hextory_travelers_inflight{workflow_id}` (gauge), `hextory_traveler_oldest_inflight_age_seconds{workflow_id}` (gauge) | Per-traveler series | Minimum needed by the alerts; `station` is bounded by registered node ids; `kind` is a fixed enum |
| **DES-0010-H** | **Stuck traveler** = in-flight (accepted, non-terminal) longer than a threshold; first slice measures **in-process** in-flight via `InflightCollector` | Checkpointer scan sweeper first | Smallest correct slice; cross-restart detection deferred (Q-OOB-4) |
| **DES-0010-I** | AWS metrics via **CloudWatch Embedded Metric Format** JSON on stdout from an `EmfMetrics` adapter; opt-in via `HEXTORY_METRICS=emf` | `boto3 put_metric_data`; ADOT collector + remote write | Zero new runtime deps, no extra IAM for metrics, no network call on the run path; collector path deferred |
| **DES-0010-J** | Alertmanager (if enabled) ships with a **null / example webhook receiver only**; real routing is operator config outside the repo | Commit paging integrations | Public kernel stays vendor/consumer-neutral |

---

## 3. Data design

### 3.1 Entities / state

| Entity | Key fields | Lifecycle |
|---|---|---|
| DigitalTraveler | unchanged `@0.1`; `payload["_correlation_id"]` reserved key | as DES-0002 |
| JourneyEvent (logical) | `correlation_id`, `traveler_id`, `workflow_id`, `seq`, `at`, `station` (node id or `gateway`), `decision`, `kind` (`accepted`/`station`/`terminal`/`resumed`/`denied`) | Emitted best-effort; written to log/file sinks; never a metric label |
| JourneyTimeline | `traveler_id`, `correlation_id`, `workflow_id`, `status`, `entries[]` (`seq`, `station`, `decision`, `entered_at`, `duration_ms`), `total_duration_ms`, `rework_count` | Computed on read from `routing_history` |
| Metric series (new) | names in DES-0010-G; labels ⊆ {`workflow_id`, `status`, `station`, `kind`} | Per scrape target / Lambda log group |
| Alert rule | `alert`, `expr`, `for`, labels `severity`, annotations `summary`, `runbook` | Versioned in git; tested in CI |

### 3.2 Data flow

```
[Visual placeholder: data-flow diagram]
RunRequest(+correlation id?) → CorrelationInterceptor → Gatekeeper
  deny  → JourneyEvent(kind=denied) + DES-0006 denial counters
  allow → JourneyEvent(accepted) + inflight.start(correlation_id, workflow_id, t0)
        → GraphRunner … routing_history grows
        → on return: station durations from routing_history deltas → histograms
                     JourneyEvent(station) per new routing entry; JourneyEvent(terminal)
                     run duration → histogram; inflight.end(...)
        → on exception: hextory_run_errors_total{kind}; inflight.end(...); re-raise
Scrape: Prometheus → GET /metrics (counters, histograms, inflight gauges)
Rules:  Prometheus evaluates alerts/*.rules.yml → Alertmanager (optional)
Read:   GET /runs/{id}/journey → checkpointer/store → build_journey_timeline()
AWS:    EmfMetrics → stdout EMF JSON → CloudWatch Metrics (namespace Hextory)
        journey JSON lines → CloudWatch Logs (query by correlation_id)
```

### 3.3 Persistence & retention

No new stores. Journey timeline reads existing checkpointers (file / Postgres / DynamoDB). Journey event sinks are logs/files with operator-owned retention. Prometheus TSDB in the Compose profile uses a local volume with default retention; production retention is operator config (non-goal). Correlation ids are caller-supplied opaque strings: validated to `[A-Za-z0-9._:-]{1,128}` and never logged alongside payload content.

---

## 4. Interface design

### 4.1 Inbound interfaces

| Interface | Protocol | Auth | Contract summary |
|---|---|---|---|
| `GET /metrics` (on-prem) | HTTP, Prometheus text | unchanged (DES-0006 Q-OBS-6) | Adds DES-0010-G series |
| `GET /runs/{traveler_id}/journey` (on-prem) | HTTP JSON | same JWT as `/runs` | `JourneyTimeline`; 404 unknown traveler |
| `X-Correlation-Id` request header (on-prem `POST /runs`) | HTTP header | n/a | Optional; invalid → ignored, defaults to `traveler_id`, `correlation_id_rejected` note in journey |
| Response header `X-Correlation-Id` | HTTP header | n/a | Echoes effective correlation id |
| `hextory run … --correlation-id ID` / `hextory journey <traveler_id>` (local) | CLI | local | Same semantics; journey printed as table or `--json` |
| Lambda event `correlation_id` / header (AWS) | API Gateway / event | per DES-0005 | Same semantics as on-prem |

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| Prometheus-compatible scraper | Pull `/metrics` | Scrape failure → `HextoryScrapeTargetDown`; business API unaffected |
| Alertmanager (optional) | Route alerts | Null receiver by default; absence does not break rule evaluation |
| CloudWatch (via Lambda stdout) | Ingest EMF metrics + journey logs | Malformed EMF → dropped by CloudWatch; covered by format tests; run unaffected |
| Journey sinks (log/file) | Persist events | Sink exception swallowed + logged (`SafeJourney`) |

### 4.3 Events / messages

`JourneyEvent` JSON line (one per event), e.g.:

```json
{"schema":"hextory.journey_event@0.1","correlation_id":"req-7f3a","traveler_id":"trv_…","workflow_id":"starter_factory","seq":3,"at":"2026-09-28T04:30:00Z","station":"quality","decision":"rework","kind":"station"}
```

Additive, versioned independently of the traveler contract. No payload content.

---

## 5. Component design

### 5.1 Core (pure) logic

- `src/ports/metrics.py`: add `set_gauge(name, value, *, labels=None)` to `MetricsPort`, `NoOpMetrics`, `InMemoryMetrics`, `SafeMetrics`; add constants `METRIC_RUN_DURATION`, `METRIC_STATION_DURATION`, `METRIC_RUN_ERRORS`, `METRIC_TRAVELERS_INFLIGHT`, `METRIC_OLDEST_INFLIGHT_AGE`; extend `ALLOWED_LABEL_KEYS` with `station`, `kind`; add `correlation_id` to `FORBIDDEN_LABEL_KEYS`.
- `src/ports/journey.py`: `JourneyEvent` (pydantic/dataclass), `JourneyPort` protocol (`record(event)`), `NoOpJourney`, `InMemoryJourney`, `SafeJourney`.
- `src/policies/correlation.py`: `resolve_correlation_id(inbound, traveler_id) -> (effective_id, rejected: bool)`.
- `src/domain/journey.py`: `build_journey_timeline(traveler) -> JourneyTimeline`; `station_durations(traveler) -> list[(station, seconds)]`.
- `src/gateway/request_gateway.py`: accept optional `journey: JourneyPort`; emit facts per §3.2; wrap runner call to count errors by fixed `kind` ∈ {`runner`, `checkpointer`, `unknown`} and re-raise.
- No new third-party imports under `src/`.

### 5.2 Adapters

| Adapter | Additions |
|---|---|
| `adapters/onprem` | Histograms/gauges in `PrometheusMetrics`; `InflightCollector` (implements `JourneyPort`, exposes two gauges via a custom collector using the injected `Clock`); JSON-log journey sink; `/runs/{id}/journey`; `X-Correlation-Id` in/out; `observability/prometheus.yml`, `observability/alerts/*.yml`; Compose `observability` profile (Prometheus, optional Alertmanager, Grafana with existing dashboard JSON provisioned) — images pinned by tag |
| `adapters/local` | `--correlation-id`; `journey` subcommand; JSONL journey dump next to metrics dump |
| `adapters/aws` | `EmfMetrics` (namespace `Hextory`, dimensions from sanitized labels, histograms as EMF value arrays); JSON-line journey sink; enabled when `HEXTORY_METRICS=emf` (default off → `NoOpMetrics`); optional `GET /runs/{id}/journey` route in `template.yaml` (Q-OOB-6) |

### 5.3 Algorithms & policies

| Policy | Rule |
|---|---|
| Correlation id | Valid inbound id wins; otherwise `traveler_id`; invalid inbound recorded as a journey note, never echoed into logs raw |
| Station duration | For consecutive `routing_history` entries *i*, *i+1*: `at[i+1] − at[i]` attributed to `node_id[i]`; last entry has no duration; gateway entries excluded |
| In-flight | `start` on accept, `end` on terminal/denied/exception; oldest age = `now − min(start)` per `workflow_id`, `0` when empty |
| Alert: gate-failure rate | `sum by (workflow_id)(rate(hextory_gate_denials_total[10m])) / clamp_min(sum by (workflow_id)(rate(hextory_gate_denials_total[10m]) + rate(hextory_runs_accepted_total[10m])), 1e-9) > 0.5` for 10m — severity `warning` |
| Alert: quality-fail rate | `rate(hextory_quality_fail_total[15m]) / clamp_min(rate(hextory_runs_accepted_total[15m]), 1e-9) > 0.3` for 15m — `warning` |
| Alert: stuck traveler | `max by (workflow_id)(hextory_traveler_oldest_inflight_age_seconds) > 900` for 5m — `critical` |
| Alert: run error rate | `rate(hextory_run_errors_total[10m]) / clamp_min(rate(hextory_runs_accepted_total[10m]), 1e-9) > 0.05` for 10m — `critical` |
| Alert: scrape down | `up{job="hextory"} == 0` for 2m — `critical` |
| Thresholds | Values above are Draft defaults (Q-OOB-5); every rule carries `summary` + `runbook` annotations |

---

## 6. UI (if any)

**N/A — no product UI.** Operator view remains the DES-0006 Grafana dashboard as code, extended with journey-adjacent panels (in-flight, oldest age, station duration p95, error rate). DES-0003 Studio remains Draft ideation and is out of scope.

```
[Visual placeholder: CLI transcript]
$ hextory run --sdd DES-0002 --force-quality FAIL --correlation-id req-7f3a
$ hextory journey trv_01H…
seq  station    decision  entered_at            duration_ms
1    gateway    accept    2026-09-28T04:30:00Z  -
2    assembly   enter     2026-09-28T04:30:00Z  12
3    quality    rework    2026-09-28T04:30:00Z  8
…    …          escalate  …                     -
correlation_id=req-7f3a status=escalated rework_count=3 total_ms=61
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-1 | `routing_history.at` is set per station for both pure and LangGraph runners | Durations wrong for one runtime | TEST-OOB-05 runs both runtimes |
| A-2 | Adding `set_gauge` to `MetricsPort` is additive (all in-tree implementers updated in the same PR) | Out-of-tree implementers break | Document in CHANGELOG/README; default `NotImplemented`-safe via `SafeMetrics` |
| A-3 | `promtool` (pinned version) can be fetched in CI | CI job cannot run | Pin + checksum; pytest lint still guards names; Q-OOB-1 |
| A-4 | Lambda stdout is ingested by CloudWatch Logs (default) and EMF is extracted | No AWS metrics | AWS-SMOKE-003 manual verification |
| A-5 | Single on-prem replica for first slice | In-flight gauges per-process | Rules aggregate with `max by`; multi-replica sweeper in Q-OOB-4 |

---

## 8. Explicit non-goals

- **NG1:** No distributed-tracing backend or mandatory OpenTelemetry spans; journeys are events + timeline (an OTel span mapping may come later).
- **NG2:** No `traveler_id`, `correlation_id`, payload, or other high-cardinality/PII values in metric labels.
- **NG3:** No traveler schema bump (`@0.1` stays); correlation id uses a reserved payload key.
- **NG4:** No hosted SaaS requirement (Grafana Cloud, APM vendors); no committed paging/chat integrations.
- **NG5:** No real AWS deploy or CloudWatch alarm creation from CI.
- **NG6:** No Studio / product UI (DES-0003).
- **NG7:** No Gatekeeper fork, no department changes, no new engine.
- **NG8:** No long-term metrics storage, HA Prometheus, or log-shipping stack (Loki/ELK) design.
- **NG9:** No Cucumber / Gherkin toolchain.
- **NG10:** No implementation while this SDD is Draft.

---

## 9. Acceptance criteria for agent implementation

Concrete only after Status is **Approved** and §13 is green.

| ID | Criterion | Verification method |
|---|---|---|
| AC-OOB-01 | `MetricsPort.set_gauge` exists on port + all in-tree implementations; `src/` gains no exporter imports | TEST-OOB-01 + TEST-0010 |
| AC-OOB-02 | A shipped run observes `hextory_run_duration_seconds` once and `hextory_station_duration_seconds` once per non-terminal station entry | TEST-OOB-02 |
| AC-OOB-03 | A runner exception increments `hextory_run_errors_total{kind}` with `kind` in the fixed enum and re-raises; in-flight is cleared | TEST-OOB-03 |
| AC-OOB-04 | Valid inbound correlation id propagates to traveler payload, journey events, and response header; absent → `traveler_id`; invalid → `traveler_id` + rejection note | TEST-OOB-04 |
| AC-OOB-05 | `build_journey_timeline` returns ordered entries with durations for PASS and rework→escalate paths on both runtimes | TEST-OOB-05 |
| AC-OOB-06 | `GET /runs/{id}/journey` returns the timeline, 404 for unknown, 401 without auth | TEST-OOB-06 |
| AC-OOB-07 | In-flight gauges report count and oldest age under a fake clock and reset on terminal | TEST-OOB-07 |
| AC-OOB-08 | `/metrics` exposition never contains `traveler_id`, `correlation_id`, or payload values | TEST-OOB-08 |
| AC-OOB-09 | Every rule has `severity`, `summary`, `runbook`; every metric referenced by a rule is a frozen name in `src/ports/metrics.py` (or `up`) | TEST-OOB-09 |
| AC-OOB-10 | Each alert has ≥1 firing and ≥1 non-firing rule unit test; CI job runs them and fails on an untested alert | TEST-OOB-10 |
| AC-OOB-11 | Compose `observability` profile config validates and scrapes `api:8080/metrics` | TEST-OOB-11 |
| AC-OOB-12 | `EmfMetrics` emits valid EMF JSON (namespace, dimensions, metrics, values) with sanitized labels only | TEST-OOB-12 |
| AC-OOB-13 | AWS wiring uses `EmfMetrics` + journey log sink only when `HEXTORY_METRICS=emf`; default remains no-op | TEST-OOB-13 |
| AC-OOB-14 | Behavior tests use Given/When/Then narrative in ordinary pytest | TEST-OOB-14 |
| AC-OOB-15 | Manual opt-in AWS-SMOKE-003 records frozen counters in CloudWatch namespace `Hextory` and a journey queryable by correlation id; evidence filed under `docs/maturity/evidence/` | AWS-SMOKE-003 (manual; not CI) |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Metrics/journey sink raises | `SafeMetrics` / `SafeJourney` | Log; continue run | Fix adapter; TEST-OOB-03/07 |
| Label cardinality leak | TEST-OOB-08; scrape cardinality | Fail CI | Drop label; amend policy |
| Alert rule references unknown metric | TEST-OOB-09 | Fail CI | Rename/freeze metric or fix rule |
| Alert never fires / always fires | TEST-OOB-10 | Fail CI | Adjust expr/threshold via SDD revision |
| Scrape target down | `HextoryScrapeTargetDown` | Operator restores API / network | n/a |
| Stuck traveler | `HextoryTravelerStuck` | Operator inspects `/runs/{id}/journey` | Per DES-0002 resume / escalation |
| EMF malformed | TEST-OOB-12; missing CloudWatch metrics in smoke | Fix adapter | AWS-SMOKE-003 re-run |
| Correlation id abuse (oversized/injection) | Validation policy | Replace with `traveler_id` + note | TEST-OOB-04 |

**Rework policy defaults:** inherit DES-0002-H for workflow runs. Observability defects fail TEST-OOB-* and block merge of the slice; they never create traveler rework.

---

## 11. Human + agent review checklist

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent with DES-0006 | ☐ | ☐ | Yes |
| 2 | Architecture fits hexagonal rules (no exporter imports in `src/`) | ☐ | ☐ | Yes |
| 3 | Interfaces and failure modes are specified | ☐ | ☐ | Yes |
| 4 | Acceptance criteria are testable | ☐ | ☐ | Yes |
| 5 | Traceability IDs are complete and unique | ☐ | ☐ | Yes |
| 6 | Gate criteria are unambiguous | ☐ | ☐ | Yes |
| 7 | Security / privacy: no PII / ids in labels; correlation-id validation; `/journey` auth | ☐ | ☐ | Yes |
| 8 | Glossary terms used consistently | ☐ | ☐ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☐ | ☐ | No |
| 10 | No implementation leakage; no private product names | ☐ | ☐ | Yes |
| 11 | Alert thresholds (Q-OOB-5) and promtool-in-CI (Q-OOB-1) acceptable or resolved | ☐ | ☐ | Yes |
| 12 | Correlation-id storage interim (Q-OOB-2) acceptable | ☐ | ☐ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | | | Approve / Changes requested |
| Agent reviewer | | | Approve / Changes requested |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| **REQ-0022** (proposed) | Operated observability: scrape, alerting, journey tracking | DES-0010-A…J | TEST-OOB-01…14, AWS-SMOKE-003 | |
| REQ-0018 | Factory metrics / operator observability | DES-0006-*, DES-0010-G | TEST-OOB-01/02/03/07/08 | extends frozen names |
| REQ-0010 | Hexagonal ports | DES-0006-B, DES-0010-F | TEST-OOB-01, TEST-0010 | `JourneyPort`, `set_gauge` |
| REQ-0012 | DigitalTraveler unchanged | DES-0010-D/E | TEST-OOB-04/05 | reserved payload key |
| REQ-0013 | Gateway + interceptors | DES-0010-C/F | TEST-OOB-03/04 | correlation interceptor |
| REQ-0015 | TDD + BDD-style testing | DES-0010-B | TEST-OOB-09/10/14 | rules tested in CI |
| REQ-0003 | Multi-target ops readiness | DES-0010-A/I | TEST-OOB-11/12/13, AWS-SMOKE-003 | on-prem + AWS |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

- [ ] Status is **Approved** (both human and agent reviews recorded).
- [ ] All **Critical** checklist items signed off by a human.
- [ ] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [ ] Non-goals and failure/rework policy are non-empty and specific.
- [ ] Acceptance criteria are binary/testable.
- [ ] No open blocking questions in §15 (or each has an approved interim decision).
- [ ] `config/sdd_status.json` lists `"DES-0010": "Approved"` matching the Status cell.

**Current state:** Status is **Draft** — §13 is **not** green. No implementation authorized.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **Operated observability** | Instrumentation that is scraped, alerted on, and navigable per traveler — beyond DES-0006's first slice |
| **Correlation id** | Opaque caller- or system-supplied id joining a request, its traveler, journey events, and logs |
| **Journey** | Ordered, timed sequence of a traveler's station transitions |
| **Station** | A registered graph node id (e.g. `assembly`, `quality`, `packaging`) — DES-0002 department node |
| **In-flight traveler** | Accepted and not yet terminal (`shipped` / `escalated` / `denied`) |
| **Stuck traveler** | In-flight longer than the alert threshold |
| **EMF** | CloudWatch Embedded Metric Format — structured JSON log lines that CloudWatch turns into metrics |
| **Rule unit test** | Synthetic time-series test asserting an alert fires / stays quiet |

Prefer project glossary terms from [0001-hextory-vision.md](0001-hextory-vision.md), [0002-factory-engine.md](0002-factory-engine.md), and [0006-factory-observability.md](0006-factory-observability.md) when overlapping.

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-OOB-1** | Is fetching a pinned `promtool` binary in CI acceptable, or must rule tests run without an external binary (pure-Python evaluator for a PromQL subset)? | Marcos | Before Approval (blocking unless interim accepted) | **Proposed, pending human Approve:** yes — pinned + checksummed `promtool` in a separate `alert-rules` CI job; pytest lint always runs |
| **Q-OOB-2** | Correlation id as reserved `payload["_correlation_id"]` (no schema bump) vs a first-class traveler field in a future `@0.2`? | Marcos | Before Approval (or accept interim) | **Proposed, pending human Approve:** reserved `payload["_correlation_id"]` now; promote to a first-class traveler field in `@0.2` |
| Q-OOB-3 | Add an optional per-step observer hook to `GraphRunner` for *live* station events, or keep post-run derivation from `routing_history`? | Dual review | During first impl slice | Soft — interim: post-run derivation (DES-0010-F) |
| Q-OOB-4 | Stuck detection across restarts / replicas: add a checkpointer scan ("sweeper") needing a list-non-terminal capability on the checkpointer port? | Maintainers | Follow-up SDD / slice | Soft — interim: in-process `InflightCollector` only |
| **Q-OOB-5** | Default alert thresholds and windows (gate-failure 50%/10m, quality-fail 30%/15m, stuck 15m, error 5%/10m, scrape 2m) — acceptable defaults, and should they be overridable via a values file? | Marcos | Before Approval (or accept interim) | **Proposed, pending human Approve:** thresholds as drafted in §5.3; thresholds live only in rule YAML |
| Q-OOB-6 | Expose `/runs/{id}/journey` on the AWS HTTP API in this slice, or on-prem + local only? | Dual review | During first impl slice | Soft — interim: on-prem + local; AWS journey via CloudWatch Logs query |
| Q-OOB-7 | Scrape auth for `/metrics` beyond the Compose network (carries DES-0006 Q-OBS-6)? | Ops / Marcos | Before production hardening | Soft — interim: open on Compose network |
| Q-OOB-8 | Ship CloudWatch alarms mirroring the Prometheus rules in `template.yaml` (parameter-gated, default off), or leave AWS alerting to operators? | Marcos | During AWS sub-slice | Soft — interim: leave to operators; document EMF metric names |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-28 | Marcos Blazquez (direction) + Clark Bot | Initial **Draft**: operated observability extending DES-0006 — scrape config + Compose profile, alert rules as code with rule unit tests, correlation id + journey timeline, new instruments, AWS EMF metrics wiring; dual review pending; no implementation |
| 2026-09-28 | Marcos Blazquez + Clark Bot | r2: Q-OOB-1 (pinned `promtool` in CI), Q-OOB-2 (reserved payload key now, first-class field in `@0.2`), Q-OOB-5 (thresholds as drafted) marked **Proposed, pending human Approve** |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Visuals** — diagram placeholders until real diagrams land.
- **Consistency** — same names as DES-0002 / DES-0006 for gateway, traveler, MetricsPort, frozen metrics.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval; record dissent in open questions.
- **Traceability** — REQ ↔ DES ↔ IMPL ↔ TEST must stay walkable after ship.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Each TEST-OOB-* is written failing first, then the smallest change makes it pass |
| BDD-style | Given/When/Then narrative in docstrings + section comments in ordinary pytest — **not Cucumber** |
| Testing layer | `tests/unit/` (ports, policies, timeline builder, rule lint), `tests/behavior/` (journey + stuck narratives), `tests/adapters/` (on-prem endpoint/collector, EMF, AWS wiring), CI `alert-rules` job (rule unit tests) |
| Traceability | Test docstrings cite TEST-OOB-NN and DES-0010-* |

### Planned TEST IDs (post-Approval)

| TEST ID | Layer | Given / When / Then |
|---|---|---|
| TEST-OOB-01 | unit | **Given** `NoOpMetrics`, `InMemoryMetrics`, `SafeMetrics` **When** `set_gauge` is called **Then** no error, in-memory value is last-write-wins, and `src/` imports no exporter library |
| TEST-OOB-02 | unit | **Given** an Approved starter run forced PASS with a fake clock **When** it ships **Then** run-duration is observed once and station-duration once per station entry with `station` label |
| TEST-OOB-03 | unit | **Given** a runner that raises **When** the gateway runs **Then** `hextory_run_errors_total{kind="runner"}` = 1, the exception propagates, and in-flight is 0 |
| TEST-OOB-04 | unit + adapters | **Given** inbound id `req-7f3a` / none / `"bad id\n"` **When** a run is accepted **Then** effective id is `req-7f3a` / `traveler_id` / `traveler_id` + rejection note, echoed in `X-Correlation-Id` |
| TEST-OOB-05 | unit | **Given** a rework→escalate traveler from pure and LangGraph runtimes **When** `build_journey_timeline` runs **Then** entries are ordered by `seq`, durations are non-negative, and `rework_count` matches |
| TEST-OOB-06 | adapters | **Given** an on-prem app with a completed run **When** `GET /runs/{id}/journey` with / without JWT / unknown id **Then** 200 timeline / 401 / 404 |
| TEST-OOB-07 | behavior | **Given** an accepted run held mid-flight and a fake clock **When** the clock advances 20 minutes **Then** oldest-inflight-age ≥ 1200 and inflight = 1; **When** it terminates **Then** both reset |
| TEST-OOB-08 | adapters | **Given** runs with correlation ids and payloads **When** `/metrics` is scraped **Then** no `traveler_id`, `correlation_id`, or payload value appears |
| TEST-OOB-09 | unit | **Given** the rule YAML **When** parsed **Then** every rule has `severity`/`summary`/`runbook` and references only frozen metric names or `up` |
| TEST-OOB-10 | CI (`promtool test rules`) | **Given** synthetic series per alert **When** evaluated **Then** each alert fires in its firing case and stays quiet in its healthy case; a guard test fails if any alert lacks a case |
| TEST-OOB-11 | CI / adapters | **Given** `observability/prometheus.yml` and the Compose profile **When** validated (`promtool check config`, compose config parse) **Then** a `hextory` job targets `api:8080/metrics` and rule files are loaded |
| TEST-OOB-12 | adapters | **Given** `EmfMetrics` **When** counters/histograms are recorded **Then** stdout lines are valid EMF (`_aws.CloudWatchMetrics`, namespace `Hextory`, sanitized dimensions) |
| TEST-OOB-13 | adapters (moto) | **Given** `HEXTORY_METRICS` unset / `emf` **When** the Lambda handler runs **Then** no EMF output / EMF + journey JSON lines carrying the correlation id |
| TEST-OOB-14 | behavior | **Given** the behavior modules for DES-0010 **When** inspected **Then** each test has Given/When/Then narrative (extends existing structure test) |
| AWS-SMOKE-003 | manual, opt-in | **Given** an authorized smoke stack **When** a run is executed with `HEXTORY_METRICS=emf` **Then** CloudWatch shows the frozen counters in `Hextory` and Logs Insights returns the journey by correlation id; evidence filed; never from CI |

### First implementation slice (authorized only after Approval)

§13 is **not** green. After dual Approve, follow-up PRs may, in order:

1. Core: `set_gauge`, new names/labels, `JourneyPort`, correlation policy/interceptor, timeline builder, gateway hooks (TEST-OOB-01…05).
2. On-prem: collectors, `/journey`, correlation header, scrape config, Compose profile, alert rules + rule tests + CI job (TEST-OOB-06…11).
3. Local CLI journey command + dump.
4. AWS: `EmfMetrics`, journey log sink, opt-in wiring (TEST-OOB-12/13); then manual AWS-SMOKE-003.
5. Do **not** change traveler schema, add tracing SaaS, commit paging integrations, or deploy from CI.

---

## Review records

**None yet.** Dual review (Marcos Blazquez + Clark Bot) is required before Status may move to **Approved**.
