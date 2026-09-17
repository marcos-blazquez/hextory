"""On-prem adapter operator notes (DES-0004).

## What this is

HTTP binding of the same Hextory factory core used by `adapters/local`:

- `POST /runs` — start a run (JWT required)
- `GET /runs/{id}` — traveler status (JWT required)
- `POST /runs/{id}/resume` — resume / reload from checkpointer (JWT required)
- `GET /health` — liveness (no JWT)

Gatekeeper + `SddStatusReader` semantics match the local CLI. Non-Approved or
missing `sdd_id` → structured **403** denial (no assembly). Missing/invalid JWT
→ **401** (never confused with gate denial).

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `HEXTORY_JWT_SECRET` | yes (workflow routes) | HS256 secret for bearer tokens |
| `HEXTORY_JWT_ISSUER` | no | Optional `iss` claim check |
| `HEXTORY_JWT_AUDIENCE` | no | Optional `aud` claim check |
| `HEXTORY_DATABASE_URL` | yes (Compose / durable) | Postgres DSN |
| `HEXTORY_ONPREM_HOST` | no | Bind host (default `0.0.0.0`) |
| `HEXTORY_ONPREM_PORT` | no | Bind port (default `8080`) |

Without `HEXTORY_DATABASE_URL`, wiring falls back to process-local memory
(useful for unit tests only — not for real on-prem durability).

## Compose smoke

From the repo root (Docker required):

```bash
export HEXTORY_JWT_SECRET=dev-secret-change-me
docker compose up --build -d
curl -s http://localhost:8080/health
# Mint a test token (Python with PyJWT installed via .[onprem]):
TOKEN=$(python -c "from adapters.onprem.auth import mint_token; print(mint_token())")
curl -s -X POST http://localhost:8080/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sdd_id":"DES-0002","workflow_id":"starter_factory","payload":{"force_quality":"PASS"}}'
```

Expected: JSON with `"status":"shipped"` and a `traveler_id`. Then:

```bash
curl -s http://localhost:8080/runs/$TRAVELER_ID -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8080/runs/$TRAVELER_ID/resume \
  -H "Authorization: Bearer $TOKEN"
```

TLS is expected to terminate at a reverse proxy (Q-ONP-3 interim); the app
speaks HTTP inside the Compose network.

## Install

```bash
pip install -e ".[onprem]"
# or with tests:
pip install -e ".[dev,onprem]"
python -m adapters.onprem
```

Postgres major version in Compose is **16** (Q-ONP-2 pin at first scaffold).
"""
