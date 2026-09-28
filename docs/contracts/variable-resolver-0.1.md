# Variable resolver published contract — `hextory.variable_resolver@0.1`

| Field | Value |
|---|---|
| **Schema id** | `hextory.variable_resolver@0.1` |
| **Authority** | [DES-0008](../design/0008-env-and-flow-variables.md) (Approved) — first slice |
| **JSON Schema** | [`variable-resolver-0.1.schema.json`](variable-resolver-0.1.schema.json) (JSON Schema 2020-12) |
| **Shared vectors** | [`variable-resolver-0.1.vectors.json`](variable-resolver-0.1.vectors.json) |
| **Core package** | `src/ports/variable_resolver.py` (`VariableResolverPort`, `KernelVariableResolver`, `resolve_exchange`) |

Language-neutral input/output contract for `{{var}}` bind/resolve so non-Python consumers (authoring clients, stubs, other runtimes) can validate documents and check parity.

## Documents

A document is exactly one of:

| Def | Meaning |
|---|---|
| `resolve_request` | `fields` (station inputs) + optional `env_profile`, `env`, `flow`, `defaults`, `secret_names` |
| `resolve_success` | `ok: true`, resolved `fields`, redacted effective-map snapshot `vars` |
| `resolve_failure` | `ok: false`, structured `error` (`resolve_error`) |

## Rules (DES-0008)

- Bind: `{{identifier}}`, identifier `^[A-Za-z_][A-Za-z0-9_]*$`. Flat names only; path binds are not part of `@0.1`.
- Escape: `\{{` → literal `{{`; unmatched `}}` is left as-is.
- Any other unescaped `{{` → `invalid_bind`. Undefined names → `undefined_variable`. Both fail closed; no partial output.
- Precedence: `flow` > `env` > `defaults`. Collisions are not errors. Empty string is a defined value.
- Only top-level string fields resolve; other values pass through unchanged. Non-string variable values render as canonical compact JSON.
- Secrets: values named in `secret_names` (or marked secret by an adapter) appear raw only inside resolved `fields`; `vars` snapshots and errors use `***`.
- Environment profile: omitted → empty; named but unknown → `env_profile_not_found`.
- Errors are deterministic: `missing_names`, `invalid_names`, `fields` sorted and de-duplicated; `invalid_binds` in first-occurrence order.

## Versioning

Additive optional members are allowed under `@0.1`. Grammar changes (e.g. path binds) need an Approved DES-0008 amendment and a new schema id.
