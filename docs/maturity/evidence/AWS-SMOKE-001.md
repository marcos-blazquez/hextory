# AWS-SMOKE-001 — Authorized DynamoDB checkpointer smoke

| Field | Value |
|---|---|
| **Evidence ID** | AWS-SMOKE-001 |
| **Related** | DES-0005 (authorized smoke amendment); TEST-AWS / `adapters/aws` |
| **Region** | `us-east-2` |
| **Table** | `hextory-aws-smoke` (pay-per-request; `pk` HASH) |
| **Stack (if used)** | n/a — table + in-process handler round-trip only (full SAM/HTTP API deploy not required for this slice) |
| **Status** | **SUCCEEDED** — Mac smoke 2026-09-17 ~20:10 America/Santiago |

## Intent

Document a bounded, **authorized** real-account smoke for multi-target (aspect 9)
evidence: DynamoDB checkpointer round-trip against table `hextory-aws-smoke` in
`us-east-2` via `adapters/aws` handlers.

## Boundaries

- Names must use `hextory-` or `hextory-public-` prefix only (canonical table: `hextory-aws-smoke`).
- Do not share resources with other workloads in the same account; use `hextory-*` names only.
- Metrics scrape: **deferred**.
- No secrets, credentials, account IDs, or other workload identifiers in this repo.
- CI must not `sam deploy`; this smoke is **manual opt-in** only.
- Default CI proof remains **moto** (+ optional LocalStack Compose).
- Full SAM / HTTP API deploy was **not** required for this first evidence slice.

## Procedure (operator)

1. Ensure authorized credentials for the smoke account are available in the shell (never commit).
2. Set env: `AWS_DEFAULT_REGION=us-east-2`, `HEXTORY_DYNAMODB_TABLE=hextory-aws-smoke`, `HEXTORY_JWT_SECRET=…` (ephemeral; not committed). Leave `HEXTORY_AWS_ENDPOINT` **unset** (real DynamoDB, not LocalStack).
3. Ensure table `hextory-aws-smoke` exists (pay-per-request, `pk` HASH) — see `adapters/aws/README.md` § Authorized smoke.
4. Invoke `adapters.aws.handlers` in-process against real DynamoDB; confirm traveler checkpoint round-trip.
5. Optional teardown (table may remain idle on pay-per-request):

```bash
aws dynamodb delete-table --table-name hextory-aws-smoke --region us-east-2
```

Operator notes: [`adapters/aws/README.md`](../../../adapters/aws/README.md).

## Result

| Field | Value |
|---|---|
| **Ran at** | 2026-09-17 ~20:10 America/Santiago |
| **Operator** | Mac smoke (authorized) |
| **Outcome** | **SUCCEEDED** |
| **Mode** | In-process `adapters.aws` handlers → real DynamoDB (`HEXTORY_AWS_ENDPOINT` unset; not LocalStack) |
| **Ops observed** | `GET /health` → 200; `POST /runs` (`DES-0002` / `starter_factory` / `force_quality` PASS) → 200 traveler **shipped**; `GET /runs/{id}` → 200; DynamoDB scan → 1 item with `pk` `traveler#trv_…` |
| **checkpoint_ref form** | `dynamodb://hextory-aws-smoke/travelers/trv_…` |
| **Metrics scrape** | Deferred |
| **SAM / HTTP API** | Not deployed for this slice (table + handler round-trip only) |
| **Secrets** | JWT secret ephemeral via env only; not committed |
| **Teardown** | Table may remain idle (pay-per-request). To delete: `aws dynamodb delete-table --table-name hextory-aws-smoke --region us-east-2` |

This note is public-safe: no account IDs and no names of other workloads in the same account.
