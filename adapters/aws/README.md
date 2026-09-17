# AWS adapter (DES-0005)

API Gateway HTTP API + Lambda handlers binding the same Hextory factory core used by
`adapters/local` and `adapters/onprem`:

| Semantic op | HTTP | Auth |
|---|---|---|
| Start run | `POST /runs` | JWT bearer |
| Status | `GET /runs/{id}` | JWT bearer |
| Resume | `POST /runs/{id}/resume` | JWT bearer |
| Health | `GET /health` | none |

Gatekeeper + `SddStatusReader` semantics match the local CLI. Non-Approved or
missing `sdd_id` → structured **403** denial (no assembly). Missing/invalid JWT
→ **401** (never confused with gate denial).

**First-slice CI proof:** moto unit tests (required) + optional LocalStack Compose
smoke. CI must **not** deploy to a real AWS account.

**Authorized smoke (manual opt-in):** operators may run a bounded real-account
smoke in `us-east-2` using only `hextory-` / `hextory-public-` stack and table
names (e.g. stack `hextory-aws-smoke`, table `hextory-aws-smoke`). Do not share
resources with other workloads in the same account; use `hextory-*` names only.
See [Authorized smoke](#authorized-smoke) and evidence note
[`docs/maturity/evidence/AWS-SMOKE-001.md`](../../docs/maturity/evidence/AWS-SMOKE-001.md).

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `HEXTORY_JWT_SECRET` | yes (workflow routes) | HS256 secret for bearer tokens |
| `HEXTORY_JWT_ISSUER` | no | Optional `iss` claim check |
| `HEXTORY_JWT_AUDIENCE` | no | Optional `aud` claim check |
| `HEXTORY_DYNAMODB_TABLE` | no | DynamoDB table (default `hextory-aws-smoke`) |
| `HEXTORY_AWS_ENDPOINT` | LocalStack | e.g. `http://localhost:4566` |
| `AWS_DEFAULT_REGION` | no | default `us-east-1` (authorized smoke: `us-east-2`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | LocalStack or smoke | LocalStack: dummy `test` / `test`; smoke: operator credentials (never commit) |

## Install

```bash
pip install -e ".[dev,aws]"
```

## moto (CI / unit)

Parity tests under `tests/adapters/test_aws_api.py` (TEST-AWS-01…08) use moto —
no real AWS credentials and no LocalStack required for the default suite.

## Optional LocalStack Compose smoke

From the repo root (Docker required):

```bash
export HEXTORY_JWT_SECRET=dev-secret-change-me
docker compose -f adapters/aws/docker-compose.localstack.yml up -d
# Wait until LocalStack is healthy, then exercise handlers in-process against
# HEXTORY_AWS_ENDPOINT=http://localhost:4566 (see TEST-AWS-05 docs).
# Example in-process invoke (not a live API GW URL string identity):
python - <<'PY'
import json, os
os.environ["HEXTORY_JWT_SECRET"] = "dev-secret-change-me"
os.environ["HEXTORY_AWS_ENDPOINT"] = "http://localhost:4566"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
from adapters.aws.auth import mint_token
from adapters.aws.handlers import build_handler_context, handle_event
ctx = build_handler_context()
token = mint_token()
event = {
    "version": "2.0",
    "rawPath": "/runs",
    "headers": {"authorization": f"Bearer {token}"},
    "requestContext": {"http": {"method": "POST"}},
    "body": json.dumps({
        "sdd_id": "DES-0002",
        "workflow_id": "starter_factory",
        "payload": {"force_quality": "PASS"},
    }),
}
print(handle_event(event, handler_context=ctx))
PY
```

Tear down:

```bash
docker compose -f adapters/aws/docker-compose.localstack.yml down
```

## Authorized smoke

Manual, operator-opt-in only. Not part of CI. Hard boundaries:

- Region: `us-east-2`
- Names: stack and table must use `hextory-` or `hextory-public-` prefix (canonical: `hextory-aws-smoke`)
- Do not share resources with other workloads in the same account; use `hextory-*` names only
- Scope: DynamoDB checkpointer round-trip via `adapters/aws` handlers; metrics scrape deferred
- No secrets in the repo

Example env (credentials from the operator shell — never commit):

```bash
export AWS_DEFAULT_REGION=us-east-2
export HEXTORY_DYNAMODB_TABLE=hextory-aws-smoke
export HEXTORY_JWT_SECRET=…   # operator-local only
# Ensure AWS credentials are available for the authorized account.
# Optional: apply SAM/CFN with stack name hextory-aws-smoke and TableName=hextory-aws-smoke,
# or create the DynamoDB table alone and invoke handlers in-process.
```

Round-trip check (in-process against real DynamoDB — same handler path as moto):

```bash
python - <<'PY'
import json, os
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-2")
os.environ.setdefault("HEXTORY_DYNAMODB_TABLE", "hextory-aws-smoke")
assert os.environ.get("HEXTORY_JWT_SECRET"), "set HEXTORY_JWT_SECRET"
from adapters.aws.auth import mint_token
from adapters.aws.handlers import build_handler_context, handle_event
ctx = build_handler_context()
token = mint_token()
event = {
    "version": "2.0",
    "rawPath": "/runs",
    "headers": {"authorization": f"Bearer {token}"},
    "requestContext": {"http": {"method": "POST"}},
    "body": json.dumps({
        "sdd_id": "DES-0002",
        "workflow_id": "starter_factory",
        "payload": {"force_quality": "PASS"},
    }),
}
print(handle_event(event, handler_context=ctx))
PY
```

Teardown:

```bash
# If a CloudFormation/SAM stack was created:
#   aws cloudformation delete-stack --stack-name hextory-aws-smoke --region us-east-2
# If only the table was created:
#   aws dynamodb delete-table --table-name hextory-aws-smoke --region us-east-2
```

Record outcome in [`docs/maturity/evidence/AWS-SMOKE-001.md`](../../docs/maturity/evidence/AWS-SMOKE-001.md) (timestamp/status placeholder for the operator).

## Uneployed IaC stub (CI)

`adapters/aws/template.yaml` is a SAM design stub. **Do not** run `sam deploy`,
`cdk deploy`, or CloudFormation apply from CI. Default table parameter is
`hextory-aws-smoke` for the authorized manual path only.

## Metrics (optional)

Handlers accept an optional `MetricsPort` via `build_handler_context(metrics=…)`
(DES-0006). First AWS slice does not require a Prometheus scrape endpoint;
authorized smoke defers metrics scrape.
