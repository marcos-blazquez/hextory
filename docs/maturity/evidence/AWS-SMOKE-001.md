# AWS-SMOKE-001 — Authorized DynamoDB checkpointer smoke

| Field | Value |
|---|---|
| **Evidence ID** | AWS-SMOKE-001 |
| **Related** | DES-0005 (authorized smoke amendment); TEST-AWS / `adapters/aws` |
| **Region** | `us-east-2` |
| **Table** | `hextory-aws-smoke` |
| **Stack (if used)** | `hextory-aws-smoke` |
| **Status** | **Pending operator run** — placeholder for Clark / Mac smoke results |

## Intent

Document a bounded, **authorized** real-account smoke for multi-target (aspect 9)
evidence: DynamoDB checkpointer round-trip against table `hextory-aws-smoke` in
`us-east-2` via `adapters/aws` handlers.

## Boundaries

- Names must use `hextory-` or `hextory-public-` prefix only (canonical table/stack: `hextory-aws-smoke`).
- Do not share resources with other workloads in the same account; use `hextory-*` names only.
- Metrics scrape: **deferred** (DES-0006 path remains LocalStack/on-prem `/metrics` until separately authorized).
- No secrets, credentials, account IDs, or pool/API identifiers in this repo.
- CI must not `sam deploy`; this smoke is **manual opt-in** only.
- Default CI proof remains **moto** (+ optional LocalStack Compose).

## Procedure (operator)

1. Ensure authorized credentials for the smoke account are available in the shell (never commit).
2. Set env: `AWS_DEFAULT_REGION=us-east-2`, `HEXTORY_DYNAMODB_TABLE=hextory-aws-smoke`, `HEXTORY_JWT_SECRET=…`.
3. Create table or apply SAM stub with stack/table `hextory-aws-smoke` (see `adapters/aws/README.md` § Authorized smoke).
4. Invoke `adapters.aws.handlers` in-process for POST `/runs` (Approved `DES-0002` starter) and confirm traveler checkpoint round-trip.
5. Tear down: delete stack and/or table `hextory-aws-smoke`.
6. Fill the result block below.

Operator notes: [`adapters/aws/README.md`](../../../adapters/aws/README.md).

## Result (fill after Mac / operator smoke)

| Field | Value |
|---|---|
| **Ran at (UTC)** | _TBD — Clark fills after Mac smoke_ |
| **Operator** | _TBD_ |
| **Outcome** | _TBD — pass / fail / skipped_ |
| **Notes** | _TBD — round-trip OK? teardown done?_ |

Until filled, treat this file as the **procedure + intent** record only — do not claim live smoke success in maturity scoring.
