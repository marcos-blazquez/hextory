# DigitalTraveler published contract — `hextory.digital_traveler@0.1`

| Field | Value |
|---|---|
| **Schema id** | `hextory.digital_traveler@0.1` |
| **Authority** | [DES-0002](../design/0002-factory-engine.md) decision **DES-0002-G** (§3.1) |
| **Status** | Published for public kernel consumers |
| **Core package** | `src/domain/traveler.py` |

This note is the short **published contract** for DigitalTraveler. Field semantics and requiredness live in DES-0002-G; this document names the schema id and the rules **downstream adapters and out-of-tree applications** that depend on `hextory.digital_traveler@0.1` must follow.

## Core fields (DES-0002-G)

Consumers that depend on `hextory.digital_traveler@0.1` MUST honor the §3.1 field set, including:

| Field | Contract rule |
|---|---|
| `traveler_id`, `workflow_id`, `sdd_id`, `status` | Required identity / lifecycle |
| `payload`, `artifact_refs`, `quality_reports`, `trace`, `audit` | Required containers (may be empty) |
| `rework_count`, `max_rework` | Required; default `max_rework` = **3** unless a workflow SDD overrides |
| `routing_history` | Required list; **append-only** — never rewrite or delete prior `RoutingEvent` entries |
| `idempotency_key`, `checkpoint_ref`, `last_defect` | Optional |
| `created_at`, `updated_at` | Required timestamps (UTC stored) |

`RoutingEvent`, `QualityReport`, and `DefectReport` shapes follow DES-0002 §3.1.

## Append-only `routing_history`

- Every node visit / routing decision appends a new event (`seq` monotonic within the traveler).
- Prior entries are immutable for the life of the traveler instance used by Gatekeeper and graph runtime.
- Adapters MAY serialize the full history; they MUST NOT collapse, rewrite timestamps, or reorder past events.

## Extension bags (downstream / out-of-tree consumers)

Downstream adapters and out-of-tree applications MAY attach **additive extension bags** — namespaced maps alongside the core traveler (for example `extensions.<vendor>` or a sibling envelope field outside the public schema id).

Rules:

1. Extension bags are **additive only**. They MUST NOT rename, remove, or change the type/semantics of DES-0002-G core fields.
2. Public kernel Gatekeeper, departments, and graph runtime MUST ignore unknown extension bags (forward-compatible).
3. Publishing a new **required** core field requires an Approved SDD amendment and a new schema id (e.g. `@0.2`).
4. Forks of the traveler **core** schema are forbidden (see below).

## Consumers must not fork Gatekeeper / traveler core

Consumers that depend on `hextory.digital_traveler@0.1`:

- **MUST** depend on the public kernel’s DigitalTraveler + Gatekeeper contracts (this schema id + DES-0002-I).
- **MUST NOT** fork or re-implement Gatekeeper policy, traveler core fields, or append-only `routing_history` semantics in a divergent copy.
- **MAY** wrap the public types with adapter DTOs and extension bags for UI / persistence needs.
- **MUST NOT** land Studio / React / `adapters/web` code in this public repo until an Approved build SDD authorizes it (DES-0003 remains Draft ideation).

## Versioning

| Change type | Action |
|---|---|
| Additive optional field or extension bag | Allowed under `@0.1` without id bump if public core ignores unknowns |
| Required new core field / semantic break | New schema id + Approved SDD amendment |
| Softening append-only `routing_history` | Not allowed under any 0.x without explicit Approved decision |

## See also

- [DES-0002 §3.1](../design/0002-factory-engine.md) — authoritative field table
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — hexagonal and design-gate rules
- `src/domain/traveler.py` — reference implementation
