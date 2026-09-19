# AWS-SMOKE-002 — Full SAM + HTTP API live smoke

| Field | Value |
|---|---|
| **Evidence ID** | AWS-SMOKE-002 |
| **Related** | DES-0005 (authorized smoke); TEST-AWS / `adapters/aws`; prior slice [AWS-SMOKE-001](AWS-SMOKE-001.md) |
| **Region** | `us-east-2` |
| **Table** | `hextory-aws-smoke` |
| **Stack** | `hextory-aws-smoke` (UPDATE after DescribeTable fix on main tip `bac43aa` / includes `65a46c8`) |
| **HTTP API** | `https://igt3ejl0ji.execute-api.us-east-2.amazonaws.com` |
| **Status** | **SUCCEEDED** — live smoke 2026-09-19 ~15:00 America/Santiago |

## Intent

Document a bounded, **authorized** real-account smoke for multi-target (aspect 9)
evidence: full **SAM stack + HTTP API** deploy against table `hextory-aws-smoke` in
`us-east-2`, exercising live API Gateway → Lambda → DynamoDB for the same
Gatekeeper / traveler ops previously proven in-process under AWS-SMOKE-001.

## Boundaries

- Names must use `hextory-` or `hextory-public-` prefix only (canonical stack/table: `hextory-aws-smoke`).
- Do not share resources with other workloads in the same account; use `hextory-*` names only.
- Metrics scrape: **deferred** (same as AWS-SMOKE-001).
- No secrets, credentials, account IDs, or other workload identifiers in this repo.
- CI must not `sam deploy`; this smoke is **manual opt-in** only.
- Default CI proof remains **moto** (+ optional LocalStack Compose).
- Temporary `dynamodb:ListTables` smoke policy was **removed**; live path works with `DescribeTable` + SAM `DynamoDBCrudPolicy` only (see `65a46c8`).

## Procedure (operator)

1. Ensure authorized credentials for the smoke account are available in the shell (never commit).
2. Deploy SAM stack `hextory-aws-smoke` in `us-east-2` from a tip that includes the DescribeTable fix (`65a46c8` or later; this run used main tip `bac43aa`).
3. Set JWT via env / stack parameter only (ephemeral; not committed).
4. Against the deployed HTTP API base URL, confirm health + run create/fetch + DynamoDB scan.
5. Optional teardown (stack/table may remain idle on pay-per-request): delete the SAM stack / table when finished.

Operator notes: [`adapters/aws/README.md`](../../../adapters/aws/README.md).

## Result

| Field | Value |
|---|---|
| **Ran at** | 2026-09-19 ~15:00 America/Santiago |
| **Outcome** | **SUCCEEDED** |
| **Mode** | Live SAM stack + HTTP API → Lambda → real DynamoDB |
| **Stack tip** | Main tip `bac43aa` (includes DescribeTable fix `65a46c8`) |
| **HTTP API** | `https://igt3ejl0ji.execute-api.us-east-2.amazonaws.com` |
| **Ops observed** | `GET /health` → 200; `POST /runs` (`DES-0002` / `starter_factory` / `force_quality` PASS) → 200 traveler `trv_5e2ad550-9d96-47f9-a8b8-e53f2113b8ad` **shipped**; `GET /runs/{id}` → 200; DynamoDB scan → Count=2 |
| **IAM** | Temporary `dynamodb:ListTables` smoke policy removed; live path works with `DescribeTable` + SAM `DynamoDBCrudPolicy` only |
| **Metrics scrape** | Deferred |
| **Secrets** | JWT via env / stack param only; not committed |

This note is public-safe: no account IDs and no names of other workloads in the same account.
