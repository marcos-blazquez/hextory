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

**First-slice proof:** moto unit tests (required) + optional LocalStack Compose
smoke. **No deploy to a real AWS account** (DES-0005-B / NG1).

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `HEXTORY_JWT_SECRET` | yes (workflow routes) | HS256 secret for bearer tokens |
| `HEXTORY_JWT_ISSUER` | no | Optional `iss` claim check |
| `HEXTORY_JWT_AUDIENCE` | no | Optional `aud` claim check |
| `HEXTORY_DYNAMODB_TABLE` | no | DynamoDB table (default `hextory`) |
| `HEXTORY_AWS_ENDPOINT` | LocalStack | e.g. `http://localhost:4566` |
| `AWS_DEFAULT_REGION` | no | default `us-east-1` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | LocalStack | dummy `test` / `test` |

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

## Uneployed IaC stub

`adapters/aws/template.yaml` is a **SAM design stub only**. Do **not** run
`sam deploy`, `cdk deploy`, or CloudFormation apply against a real account in
this first slice. CI must not deploy.

## Metrics (optional)

Handlers accept an optional `MetricsPort` via `build_handler_context(metrics=…)`
(DES-0006). First AWS slice does not require a Prometheus scrape endpoint.
