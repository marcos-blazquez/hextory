# DES-0011 — ExternalJobPort (provider-agnostic long-running external jobs)

| Field | Value |
|---|---|
| **Doc ID** | DES-0011 |
| **Title** | `ExternalJobPort` — start / poll / fetch_logs / cancel for long-running external jobs |
| **Status** | Draft |
| **Authors** | Marcos Blazquez (direction) + Clark Bot (draft) |
| **Reviewers (human)** | TBD — Marcos Blazquez |
| **Reviewers (agent)** | TBD — Clark Bot |
| **Created** | 2026-09-28 |
| **Last updated** | 2026-09-28 |
| **Related REQs** | REQ-0010 (hexagonal ports); REQ-0012 (traveler); REQ-0014 (quality outcomes / rework); REQ-0015 (TDD + BDD-style testing); proposed **REQ-0023** (external job execution from stations) |
| **Supersedes** | none |
| **Depends on** | [DES-0001](0001-hextory-vision.md) (**Approved**), [DES-0002](0002-factory-engine.md) (**Approved**); related: [DES-0006](0006-factory-observability.md) (**Approved**) for metrics, [DES-0008](0008-env-and-flow-variables.md) (**Approved**) for secret-bearing variables |
| **Implementation** | **Not authorized** while Status is Draft — no port, fake adapter, or station wiring may merge until dual Approve + §13 green |

---

## 0. Document posture

Stations often need work done **outside** the factory process: a build, a test suite, a render, a data export — anything that is started remotely, runs for seconds to hours, and finishes with a status and logs. Today each such integration would be hand-rolled inside a department or adapter, with its own timeout, retry, log and error semantics.

This Draft defines one **provider-agnostic port** in the public kernel so stations can drive external jobs uniformly, plus a **local fake adapter** for tests. Concrete providers (e.g. a CI provider, a batch queue, a container runner) are future adapters under `adapters/` and are **out of scope** here.

**Hard rules (must survive into any future build):**

1. The port lives in `src/ports/`; no provider SDK, HTTP client, or vendor name appears under `src/` (TEST-0010 extended).
2. **Secrets never appear in logs, journey/traveler events, metric labels, errors, or exceptions** surfaced by the port. Redaction is enforced by the kernel, not left to each adapter.
3. Job outcomes map to **station outcomes** (success / failure / error) by one pure, tested policy — adapters never decide routing.
4. `start` is **idempotent** per idempotency key; a retried station never launches a duplicate job.
5. Every job has a **deadline**; there is no unbounded wait.
6. Traveler contract stays `hextory.digital_traveler@0.1`; no Gatekeeper fork; no new engine.
7. Public kernel stays consumer- and vendor-agnostic.

---

## 1. Introduction / overview

### 1.1 Problem statement

Without a shared port, each station that calls an external system will re-invent: how to start work, how to wait, what "timed out" means, how much log to pull back, how to keep tokens out of logs, and whether a failed job means *rework* or *escalate*. That produces inconsistent routing, leaked secrets, and untestable stations.

### 1.2 Goals

- **G1 (REQ-0023 / REQ-0010):** A minimal `ExternalJobPort` protocol: `start(job_spec) -> JobHandle`, `poll(handle) -> JobStatus`, `fetch_logs(handle, mode) -> JobLogs`, `cancel(handle) -> JobStatus`.
- **G2:** A closed status vocabulary: `queued`, `running`, `succeeded`, `failed`, `cancelled`, `timed_out`.
- **G3:** Explicit **timeout** semantics (queue timeout, run timeout, overall deadline) enforced by the kernel.
- **G4:** Mandatory **log redaction / masking** of secrets and declared sensitive values before logs leave the port boundary.
- **G5:** **Idempotent** start keyed by traveler + station + attempt.
- **G6 (REQ-0014):** Deterministic mapping from job status to station outcome (success / failure / error) and on into DES-0002 routing (PASS / FAIL→rework / escalate).
- **G7 (REQ-0015):** A local **fake adapter** (`FakeExternalJobs`) with scriptable timelines so every behavior is testable offline.

### 1.3 Success definition

- Dual review Approves the port shape, status vocabulary, outcome mapping, timeout and redaction rules.
- After Approval, a station can run an external job end-to-end against the fake adapter with TEST-EXJ-* green and no provider code in `src/`.
- A later provider adapter needs only to implement four methods and pass a shared contract test suite.

### 1.4 Scope

**In scope:** port protocol and value types; status vocabulary and transitions; timeout, idempotency, redaction, and error-mapping policies; a pure `run_external_job` driver (start → poll loop → logs → outcome) using injected `Clock` / sleeper; `FakeExternalJobs` adapter; contract test suite reusable by future adapters; metrics facts via DES-0006 `MetricsPort`.

**Out of scope:** see Explicit non-goals (§8).

---

## 2. System architecture

### 2.1 Context

```
[Visual placeholder: context diagram]
Department / station node (src/departments/*)
        │  JobSpec (+ secret refs, never secret values in logs)
        ▼
run_external_job()  (pure driver in src/policies/external_job.py)
        │   Clock + Sleeper ports; Redactor; outcome policy
        ▼
ExternalJobPort (src/ports/external_job.py)
        │
        ├── FakeExternalJobs (adapters/local/fake_external_jobs.py)   ← tests / local CLI
        └── <future provider adapters> (adapters/<target>/…)          ← e.g. a CI provider, a batch queue — NOT in this SDD
        │
        ▼
StationOutcome(success | failure | error) → DES-0002 routing (PASS / FAIL→rework / escalate)
```

### 2.2 Architectural style

Hexagonal / ports & adapters (DES-0002-A). Core owns the protocol, value types, policies, and the polling driver; adapters own transport and provider specifics. The driver is synchronous and deterministic under injected time so it runs identically in the pure runner and the LangGraph runtime.

### 2.3 High-level components

| Component | Placement | Responsibility |
|---|---|---|
| `ExternalJobPort` protocol + value types | `src/ports/external_job.py` | `JobSpec`, `JobHandle`, `JobStatus`, `JobState`, `LogMode`, `JobLogs`, `JobError` |
| `Sleeper` port | `src/ports/clock.py` (additive) | Injected wait so tests never sleep |
| `Redactor` | `src/policies/redaction.py` (pure) | Mask declared secret values + built-in patterns in any string leaving the port |
| `run_external_job` driver | `src/policies/external_job.py` (pure) | start (idempotent) → poll with backoff until terminal or deadline → cancel on timeout → fetch logs per mode → outcome |
| Outcome policy | `src/policies/external_job.py` | `JobState`/`JobError` → `StationOutcome` |
| `FakeExternalJobs` | `adapters/local/fake_external_jobs.py` | Scriptable state timelines, log bodies, injected failures; in-memory idempotency |
| Contract test suite | `tests/contracts/test_external_job_contract.py` | Parametrized over adapters; fake is the first subject |

### 2.4 Design decisions

| ID | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| **DES-0011-A** | Four-operation port: `start`, `poll`, `fetch_logs`, `cancel` | Single blocking `run()`; callback/webhook port | Polling works for every provider and for resume-after-restart; webhooks can feed `poll` later |
| **DES-0011-B** | Closed `JobState` enum: `queued`, `running`, `succeeded`, `failed`, `cancelled`, `timed_out`; terminal = last four | Free-form provider strings | Stable routing and metrics; adapters map provider states in |
| **DES-0011-C** | Timeouts enforced by the **kernel driver** (queue timeout, run timeout, overall deadline); on expiry the driver calls `cancel` and reports `timed_out` even if the provider disagrees | Trust provider timeouts only | Bounded waits regardless of provider; consistent semantics |
| **DES-0011-D** | Redaction is **mandatory and centralized**: every string in `JobLogs`, `JobError.message`, journey/traveler notes passes `Redactor` before crossing the port boundary; secret values are supplied as refs and resolved only inside the adapter | Per-adapter masking | One tested choke point; adapters cannot forget |
| **DES-0011-E** | Idempotency key = `sha256(traveler_id, station, attempt)` by default (caller may override); `start` with a seen key returns the existing handle | Provider-native dedupe only | Safe retries / resume; works with fake and all providers |
| **DES-0011-F** | Outcome mapping: `succeeded` → **success** (PASS); `failed` → **failure** (FAIL → DES-0002-H rework policy); `cancelled` / `timed_out` / adapter or transport error / unknown → **error** (escalate; no rework) | Treat timeouts as FAIL (rework) | A job's *verdict* is rework-worthy; infrastructure faults are not — avoids burning rework budget on outages |
| **DES-0011-G** | `fetch_logs(mode)` with `none`, `tail(N)` (N ≤ configurable cap, default 200 lines), `full` → returns an **artifact ref** (URI + digest), never an inline full body | Always inline full logs | Keeps traveler/events small; full logs stay in provider/artifact storage |
| **DES-0011-H** | Handle is opaque, serializable, and stored on the traveler as an `ArtifactRef(kind="external_job", uri=<handle>)` so a resumed run re-polls instead of restarting | Keep handle in memory | Resume after restart (DES-0002 checkpointers) without schema change |
| **DES-0011-I** | Test-first with `FakeExternalJobs` + a shared contract suite; no provider adapter in this SDD | Ship a first real provider now | Provider-agnostic kernel; real adapters get their own SDD |

---

## 3. Data design

### 3.1 Entities / state

| Entity | Key fields | Notes |
|---|---|---|
| `JobSpec` | `kind` (opaque string), `inputs` (dict of non-secret values), `secret_refs` (names only), `idempotency_key`, `queue_timeout_s`, `run_timeout_s`, `deadline_s`, `log_mode`, `labels` (low-cardinality) | Serializable; contains **no secret values** |
| `JobHandle` | `adapter` (id), `job_id` (opaque), `idempotency_key` | Serializable; safe to persist and log |
| `JobStatus` | `state: JobState`, `started_at?`, `finished_at?`, `exit_code?`, `detail` (redacted), `provider_state` (redacted, informational) | Returned by `poll` / `cancel` |
| `JobLogs` | `mode`, `lines[]` (redacted, tail only), `artifact?: ArtifactRef`, `truncated: bool` | `full` → artifact only |
| `JobError` | `code` (`start_failed` / `poll_failed` / `transport` / `auth` / `not_found` / `unknown`), `message` (redacted), `retryable: bool` | Raised by adapters; never contains secrets |
| `StationOutcome` | `success` / `failure` / `error`, `reason`, `handle`, `state` | Consumed by the calling department |

### 3.2 Status transitions

```
queued ──► running ──► succeeded
   │          ├──────► failed
   │          ├──────► cancelled   (cancel requested)
   │          └──────► timed_out   (run timeout / deadline — kernel-enforced)
   ├──────────────────► cancelled
   └──────────────────► timed_out  (queue timeout / deadline)
Terminal states are absorbing; poll on a terminal handle returns the same state.
```

### 3.3 Data flow

```
station → JobSpec → run_external_job
  start(spec)  [idempotent by key] → handle → traveler.artifacts += ArtifactRef(external_job)
  loop: poll(handle) with backoff (Sleeper) until terminal or timeout
        timeout → cancel(handle) → state=timed_out
  fetch_logs(handle, mode) → Redactor → JobLogs
  outcome_policy(state | JobError) → StationOutcome → department sets PASS / FAIL / escalate
  MetricsPort: hextory_external_jobs_total{status}, hextory_external_job_duration_seconds
```

### 3.4 Persistence & retention

Only the handle (as an `ArtifactRef`) and a redacted outcome note are persisted on the traveler via existing checkpointers. Tail lines are **not** persisted on the traveler by default (Q-EXJ-3); full logs remain wherever the provider/artifact store keeps them.

---

## 4. Interface design

### 4.1 Port (inbound to adapters)

```python
class ExternalJobPort(Protocol):
    def start(self, spec: JobSpec) -> JobHandle: ...
    def poll(self, handle: JobHandle) -> JobStatus: ...
    def fetch_logs(self, handle: JobHandle, mode: LogMode) -> JobLogs: ...
    def cancel(self, handle: JobHandle) -> JobStatus: ...
```

| Operation | Contract |
|---|---|
| `start` | Returns a handle for a new or existing (same idempotency key) job; raises `JobError(start_failed/auth/transport)` |
| `poll` | Returns current `JobStatus`; terminal states absorbing; unknown handle → `JobError(not_found)` |
| `fetch_logs` | `none` → empty; `tail(N)` → ≤ N redacted lines; `full` → `ArtifactRef` only; may be called in any state |
| `cancel` | Idempotent; on terminal job returns the existing terminal status; otherwise requests cancellation and returns latest status |

### 4.2 Outbound interfaces

| Dependency | Purpose | Failure behavior |
|---|---|---|
| Provider (future adapters) | Execute the job | Mapped to `JobError`; driver maps to **error** outcome |
| `Clock` / `Sleeper` | Deadlines and backoff | Injected; fakes in tests |
| `MetricsPort` (DES-0006) | Job counts / durations | Best-effort (`SafeMetrics`) |
| Secret resolution (e.g. DES-0008 environment vars) | Resolve `secret_refs` inside the adapter | Missing secret → `JobError(auth)`; value never echoed |

### 4.3 Events / messages

Traveler `routing_history` note on the calling station: `external_job state=<state> outcome=<outcome> handle=<adapter>:<job_id>` (redacted). No new event topics. Metric labels limited to `workflow_id`, `status` (job state) — never handle, job id, or spec inputs.

---

## 5. Component design

### 5.1 Core (pure) logic

- `run_external_job(port, spec, *, clock, sleeper, redactor, metrics, poll_interval_s=2, backoff=1.5, max_interval_s=30) -> StationOutcome`.
- Timeouts: queue timeout counts while `queued`; run timeout counts from first `running`; overall `deadline_s` counts from `start`. First to expire wins → `cancel` → `timed_out`.
- Transient `JobError(retryable=True)` from `poll` is retried within the deadline (bounded, Q-EXJ-4); non-retryable → **error** outcome immediately.
- `Redactor`: masks (a) every resolved secret value registered for the job (exact and URL-encoded / base64 forms), (b) built-in patterns (bearer tokens, `password=`/`token=`/`secret=` pairs, private-key blocks), replacing with `***`. Applied to log lines, error messages, status detail, and routing notes.

### 5.2 Adapters

| Adapter | Scope |
|---|---|
| `adapters/local/fake_external_jobs.py` | **In scope.** `FakeExternalJobs(script=...)`: per-kind scripted timelines (e.g. `[queued×2, running×3, succeeded]`), scripted log bodies (may include fake secrets to prove redaction), injectable `JobError`s, honors cancel, in-memory idempotency map. Deterministic under fake clock. |
| Future provider adapters | **Out of scope.** Each needs its own SDD and must pass `tests/contracts/test_external_job_contract.py`. |

### 5.3 Algorithms & policies

| Job result | StationOutcome | DES-0002 routing |
|---|---|---|
| `succeeded` | success | PASS → next station |
| `failed` | failure | FAIL → rework per `max_rework` (DES-0002-H) |
| `cancelled` | error | escalate |
| `timed_out` | error | escalate |
| `JobError` (non-retryable, or retryable past deadline) | error | escalate |
| Unknown / unmapped provider state | error | escalate |

---

## 6. UI (if any)

**N/A — no UI.** Port + fake adapter only.

```
[Visual placeholder: test transcript]
Given a fake job scripted queued→running→succeeded with a secret in its logs
When the station runs it with log mode tail(50)
Then the outcome is success and no log line contains the secret
```

---

## 7. Assumptions and dependencies

| ID | Assumption / dependency | Risk if wrong | Mitigation |
|---|---|---|---|
| A-1 | Most providers expose start / status / logs / cancel or equivalents | Some provider cannot cancel | `cancel` may return non-terminal; driver still reports `timed_out` and records `cancel_unconfirmed` |
| A-2 | Synchronous polling inside a station is acceptable for first slice | Long jobs hold a worker | Resume via persisted handle (DES-0011-H); async/park-and-resume in Q-EXJ-1 |
| A-3 | Secret values are known to the adapter at start time | Redactor misses unknown secrets | Built-in patterns + contract test with seeded secrets |
| A-4 | `ArtifactRef` suffices to persist handles without schema change | Need richer fields | Q-EXJ-2 |

---

## 8. Explicit non-goals

- **NG1:** No concrete provider adapter (no specific CI vendor, cloud batch service, or container platform) in this SDD.
- **NG2:** No webhook / push callback ingestion (may feed `poll` later).
- **NG3:** No workflow-level parallel fan-out / job DAGs; one job per station call.
- **NG4:** No inline storage of full logs on the traveler or in events.
- **NG5:** No secret storage or secret manager; the port consumes refs only.
- **NG6:** No traveler schema change, Gatekeeper fork, or new engine.
- **NG7:** No UI; no Cucumber / Gherkin toolchain.
- **NG8:** No implementation while this SDD is Draft.

---

## 9. Acceptance criteria for agent implementation

Concrete only after Status is **Approved** and §13 is green.

| ID | Criterion | Verification method |
|---|---|---|
| AC-EXJ-01 | Port + value types exist in `src/ports/external_job.py`; no provider/HTTP imports under `src/` | TEST-EXJ-01 + TEST-0010 |
| AC-EXJ-02 | State machine: only allowed transitions; terminal states absorbing | TEST-EXJ-02 |
| AC-EXJ-03 | `succeeded` → success/PASS; `failed` → failure/FAIL (rework policy applies) | TEST-EXJ-03 |
| AC-EXJ-04 | `cancelled`, `timed_out`, non-retryable `JobError`, unknown state → error/escalate with `rework_count` unchanged | TEST-EXJ-04 |
| AC-EXJ-05 | Queue timeout, run timeout, and deadline each produce `timed_out` and a `cancel` call, with zero real sleeping | TEST-EXJ-05 |
| AC-EXJ-06 | Same idempotency key → same handle, one underlying job; resume re-polls the persisted handle | TEST-EXJ-06 |
| AC-EXJ-07 | `fetch_logs`: `none` empty; `tail(N)` ≤ N lines and capped; `full` returns `ArtifactRef` only | TEST-EXJ-07 |
| AC-EXJ-08 | Seeded secrets (plain, URL-encoded, base64) and built-in patterns never appear in logs, errors, status detail, routing notes, or metric labels | TEST-EXJ-08 |
| AC-EXJ-09 | `cancel` idempotent; cancel on terminal returns the terminal status | TEST-EXJ-09 |
| AC-EXJ-10 | Retryable `JobError` retried within deadline; exhausted → error | TEST-EXJ-10 |
| AC-EXJ-11 | Metrics facts emitted with only `workflow_id` / `status` labels | TEST-EXJ-11 |
| AC-EXJ-12 | Shared contract suite passes for `FakeExternalJobs` and is parametrizable for future adapters | TEST-EXJ-12 |
| AC-EXJ-13 | Behavior tests use Given/When/Then narrative in ordinary pytest | TEST-EXJ-13 |

---

## 10. Failure modes & rework policy

| Failure mode | Detection | Immediate action | Rework loop |
|---|---|---|---|
| Job verdict failed | `poll` → `failed` | Station FAIL | DES-0002-H rework (max_rework) |
| Job hangs in queue / running | Kernel timeouts | `cancel`; `timed_out` → escalate | None |
| Provider outage / auth error | `JobError` | Retry if retryable within deadline; else escalate | None |
| Cancel not honored | `cancel` returns non-terminal | Report `timed_out` + `cancel_unconfirmed` note | None |
| Secret leak attempt in logs | Redactor | Mask before crossing boundary | TEST-EXJ-08 guards |
| Duplicate start on retry | Idempotency key | Return existing handle | None |
| Process restart mid-job | Persisted handle | Resume re-polls | None |

---

## 11. Human + agent review checklist

| # | Check | Human | Agent | Critical? |
|---|---|---|---|---|
| 1 | Goals and non-goals are clear and consistent | ☐ | ☐ | Yes |
| 2 | Architecture fits hexagonal rules (no provider code in `src/`) | ☐ | ☐ | Yes |
| 3 | Interfaces and failure modes are specified | ☐ | ☐ | Yes |
| 4 | Acceptance criteria are testable | ☐ | ☐ | Yes |
| 5 | Traceability IDs are complete and unique | ☐ | ☐ | Yes |
| 6 | Gate criteria are unambiguous | ☐ | ☐ | Yes |
| 7 | Security: redaction choke point, secret refs only, no secrets in labels/events | ☐ | ☐ | Yes |
| 8 | Glossary terms used consistently | ☐ | ☐ | No |
| 9 | Visuals / diagrams present or explicitly deferred | ☐ | ☐ | No |
| 10 | No implementation leakage; provider-agnostic; no private product names | ☐ | ☐ | Yes |
| 11 | Outcome mapping (timeouts/cancel = error, not rework) acceptable | ☐ | ☐ | Yes |

**Sign-off**

| Role | Name | Date | Decision |
|---|---|---|---|
| Human reviewer | | | Approve / Changes requested |
| Agent reviewer | | | Approve / Changes requested |

---

## 12. Traceability

| REQ ID | Description | DES IDs | TEST IDs | IMPL notes (post-approval) |
|---|---|---|---|---|
| **REQ-0023** (proposed) | External job execution from stations | DES-0011-A…I | TEST-EXJ-01…13 | |
| REQ-0010 | Hexagonal ports | DES-0011-A/I | TEST-EXJ-01/12, TEST-0010 | port in `src/ports` |
| REQ-0012 | Traveler unchanged | DES-0011-H | TEST-EXJ-06 | handle as `ArtifactRef` |
| REQ-0014 | Quality outcomes / rework | DES-0011-F | TEST-EXJ-03/04 | outcome policy |
| REQ-0015 | TDD + BDD-style | DES-0011-I | TEST-EXJ-12/13 | fake + contract suite |
| REQ-0018 | Factory metrics | DES-0011 §4.3 | TEST-EXJ-11 | via MetricsPort |

IDs must remain stable once Approved. New work gets new IDs; do not reuse.

---

## 13. Gate criteria (must be green before code generation)

- [ ] Status is **Approved** (both human and agent reviews recorded).
- [ ] All **Critical** checklist items signed off by a human.
- [ ] Every `REQ-*` maps to at least one `DES-*` and planned `TEST-*`.
- [ ] Non-goals and failure/rework policy are non-empty and specific.
- [ ] Acceptance criteria are binary/testable.
- [ ] No open blocking questions in §15 (or each has an approved interim decision).
- [ ] `config/sdd_status.json` lists `"DES-0011": "Approved"` matching the Status cell.

**Current state:** Status is **Draft** — §13 is **not** green. No implementation authorized.

---

## 14. Glossary (document-local)

| Term | Meaning in this SDD |
|---|---|
| **External job** | Work executed outside the factory process, started and observed via `ExternalJobPort` |
| **Handle** | Opaque, serializable reference to one external job |
| **Station outcome** | `success` / `failure` / `error` — the port's verdict handed to the department |
| **Redaction** | Replacing secret values / patterns with `***` before data crosses the port boundary |
| **Kernel-enforced timeout** | Deadline evaluated by the driver with the injected `Clock`, independent of the provider |
| **Contract suite** | Adapter-agnostic tests every `ExternalJobPort` implementation must pass |

---

## 15. Open questions

| ID | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| **Q-EXJ-1** | Synchronous poll-in-station for first slice, or park the traveler (non-terminal "waiting" status) and resume on a later tick? | Marcos | Before Approval (blocking unless interim accepted) | Open — proposed interim: synchronous with persisted handle for resume; parking deferred (would need a new traveler status) |
| **Q-EXJ-2** | Persist the handle as `ArtifactRef(kind="external_job")` (no schema change) vs a first-class traveler field? | Marcos | Before Approval (or accept interim) | Open — proposed interim: `ArtifactRef` |
| **Q-EXJ-3** | Should redacted tail lines be attached to the traveler (e.g. on failure only) or only returned to the station? | Dual review | Before Approval (or accept interim) | Open — proposed interim: attach ≤ 50 redacted tail lines on `failed` only, as a DefectReport detail |
| Q-EXJ-4 | Default poll interval / backoff / retry budget for retryable errors? | Implementer | During first impl slice | Soft — 2s start, ×1.5, cap 30s; retries only within deadline |
| Q-EXJ-5 | Should `failed` with a provider "infrastructure" reason be reclassified as **error**? Needs a provider-neutral hint field | Dual review | Future provider SDD | Soft — interim: `failed` is always failure |
| Q-EXJ-6 | Where do station-level job specs come from — department code only, or bindable via DES-0008 `{{var}}`? | Maintainers | Follow-up | Soft — interim: department code; string inputs may use DES-0008 bind |

---

## 16. Revision history

| Date | Author | Change |
|---|---|---|
| 2026-09-28 | Marcos Blazquez (direction) + Clark Bot | Initial **Draft**: provider-agnostic `ExternalJobPort` (start/poll/fetch_logs/cancel), status vocabulary, kernel timeouts, mandatory redaction, idempotency, outcome mapping, fake adapter + contract suite; no implementation |

---

## Best-practice reminders (keep this SDD healthy)

- **Clear language** — prefer concrete nouns and measurable verbs.
- **Consistency** — same names as DES-0002 for traveler, departments, rework policy; DES-0006 for metrics.
- **Keep current** — update status and revision history on every material change.
- **Central access** — live only under `docs/design/`; listed in README / CONTRIBUTING / `config/sdd_status.json`.
- **Collaboration** — dual review mandatory before Approval.
- **Future growth** — each concrete provider adapter gets its own SDD and must pass the contract suite.

## Testing approach (required when the workflow produces code)

| Item | Guidance |
|---|---|
| TDD | Each TEST-EXJ-* written failing first against `FakeExternalJobs` |
| BDD-style | Given/When/Then narrative in docstrings + section comments in ordinary pytest — **not Cucumber** |
| Testing layer | `tests/unit/` (types, policies, redactor, driver), `tests/behavior/` (station narratives), `tests/contracts/` (adapter contract suite) |
| Time | Fake `Clock` + recording `Sleeper`; no real sleeps |
| Traceability | Test docstrings cite TEST-EXJ-NN and DES-0011-* |

### Planned TEST IDs (post-Approval)

| TEST ID | Layer | Given / When / Then |
|---|---|---|
| TEST-EXJ-01 | unit | **Given** `src/` **When** imports are scanned **Then** `external_job` port exists and no provider/HTTP client is imported |
| TEST-EXJ-02 | unit | **Given** each `JobState` **When** transitions are applied **Then** only §3.2 transitions are allowed and terminal states are absorbing |
| TEST-EXJ-03 | behavior | **Given** a fake job scripted to `succeeded` / `failed` **When** a station runs it **Then** outcome is success→PASS / failure→FAIL and rework policy applies |
| TEST-EXJ-04 | behavior | **Given** jobs ending `cancelled` / `timed_out` / non-retryable error / unknown state **When** run **Then** outcome is error→escalated and `rework_count` is unchanged |
| TEST-EXJ-05 | unit | **Given** a job stuck `queued` (then another stuck `running`, then a deadline breach) and a fake clock **When** the driver runs **Then** `cancel` is called once, state is `timed_out`, and the sleeper recorded waits without real time passing |
| TEST-EXJ-06 | unit | **Given** a started job **When** `start` is called again with the same key, and when a run resumes from a checkpointed traveler **Then** the same handle is returned and the fake reports one underlying job |
| TEST-EXJ-07 | unit | **Given** a 1,000-line log **When** `fetch_logs` is called with `none` / `tail(10)` / `tail(10_000)` / `full` **Then** empty / 10 lines / capped lines + `truncated` / `ArtifactRef` only |
| TEST-EXJ-08 | unit + behavior | **Given** a secret seeded into logs, error messages, and status detail (plain, URL-encoded, base64) plus a bearer token pattern **When** the job runs and fails **Then** none appear in `JobLogs`, `StationOutcome.reason`, routing notes, or metric labels |
| TEST-EXJ-09 | unit | **Given** a running job **When** `cancel` is called twice, and on a terminal job **Then** results are consistent and terminal status is unchanged |
| TEST-EXJ-10 | unit | **Given** `poll` raising a retryable error twice then succeeding (and another case exhausting the deadline) **When** the driver runs **Then** success / error respectively |
| TEST-EXJ-11 | unit | **Given** `InMemoryMetrics` **When** jobs finish in each state **Then** `hextory_external_jobs_total{status}` and duration are recorded with only allowed labels |
| TEST-EXJ-12 | contracts | **Given** the contract suite parametrized with `FakeExternalJobs` **When** run **Then** all port contract cases (§4.1) pass |
| TEST-EXJ-13 | behavior | **Given** DES-0011 behavior modules **When** inspected **Then** each test carries Given/When/Then narrative |

### First implementation slice (authorized only after Approval)

§13 is **not** green. After dual Approve, a follow-up PR may:

1. Add `src/ports/external_job.py`, `Sleeper`, `src/policies/redaction.py`, `src/policies/external_job.py`.
2. Add `adapters/local/fake_external_jobs.py` and the contract suite.
3. Add TEST-EXJ-01…13.
4. Do **not** add any concrete provider adapter, webhook ingestion, or traveler schema change.

---

## Review records

**None yet.** Dual review (Marcos Blazquez + Clark Bot) is required before Status may move to **Approved**.
