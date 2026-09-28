"""Variable resolver port — Environment + in-flow ``{{var}}`` bind/resolve (DES-0008).

First slice (DES-0008 §9 / "First implementation slice"):

- Grammar (DES-0008-B): ``{{identifier}}`` with ``identifier`` =
  ``[A-Za-z_][A-Za-z0-9_]*``. Flat names only (Q-VAR-3); path binds such as
  ``{{node.output.text}}`` are *not* part of this slice.
- Escape (DES-0008-C): ``\\{{`` yields a literal ``{{`` (one backslash consumed);
  an unmatched ``}}`` is left as-is.
- Undefined (DES-0008-D): fail closed with a structured :class:`ResolveError`.
  Any other unescaped ``{{`` that does not open a valid bind also fails closed
  (``invalid_bind``) so a raw token never reaches a node.
- Precedence (DES-0008-G): in-flow > Environment > defaults; collisions are not
  errors. Defined names must themselves be identifiers.
- Secrets (DES-0008 §3.3): adapters wrap secret-backed values in
  :class:`SecretValue`. The raw value is substituted into resolved station
  inputs only; snapshots (``payload["vars"]``), error messages and snippets
  carry the :data:`REDACTED` marker instead.

Pure module: no adapter, OS-environment, network or secret-store imports.
The language-neutral contract lives in
``docs/contracts/variable-resolver-0.1.schema.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Protocol

SCHEMA_ID = "hextory.variable_resolver@0.1"

#: Reserved traveler payload key for the effective-map snapshot (DES-0008-E).
VARS_PAYLOAD_KEY = "vars"
#: RequestContext.metadata key mirroring the (redacted) effective map.
VARS_METADATA_KEY = "vars"
#: Payload key carrying a structured resolve error on a failed run.
RESOLVE_ERROR_PAYLOAD_KEY = "_resolve_error"

#: Marker substituted for secret values anywhere outside a resolved field.
REDACTED = "***"

IDENTIFIER_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"
_IDENTIFIER_RE = re.compile(rf"^{IDENTIFIER_PATTERN}$")
# Order matters: escape, then a valid bind, then any other bare opener.
_TOKEN_RE = re.compile(rf"\\\{{\{{|\{{\{{({IDENTIFIER_PATTERN})\}}\}}|\{{\{{")

ERROR_UNDEFINED_VARIABLE = "undefined_variable"
ERROR_INVALID_BIND = "invalid_bind"
ERROR_INVALID_VARIABLE_NAME = "invalid_variable_name"
ERROR_ENV_PROFILE_NOT_FOUND = "env_profile_not_found"

ERROR_CODES: frozenset[str] = frozenset(
    {
        ERROR_UNDEFINED_VARIABLE,
        ERROR_INVALID_BIND,
        ERROR_INVALID_VARIABLE_NAME,
        ERROR_ENV_PROFILE_NOT_FOUND,
    }
)

_SNIPPET_MAX = 120
_INVALID_BIND_MAX = 64


# --------------------------------------------------------------------------
# Value objects
# --------------------------------------------------------------------------


@dataclass(frozen=True, repr=False)
class SecretValue:
    """Secret-backed variable value. Never renders its raw value via str/repr."""

    _value: Any

    def reveal(self) -> Any:
        return self._value

    def __repr__(self) -> str:
        return f"SecretValue({REDACTED})"

    def __str__(self) -> str:
        return REDACTED


class ResolveError(Exception):
    """Structured, deterministic resolve failure (DES-0008 §3.1 ``ResolveError``).

    Lists are sorted (names) or in first-occurrence order (invalid binds) so the
    same input always yields the same error. ``snippet`` is redacted.
    """

    def __init__(
        self,
        code: str,
        *,
        missing_names: Iterable[str] = (),
        invalid_names: Iterable[str] = (),
        invalid_binds: Iterable[str] = (),
        fields: Iterable[str] = (),
        snippet: str = "",
        env_profile: Optional[str] = None,
    ) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"unknown resolve error code {code!r}")
        self.code = code
        self.missing_names = sorted(set(missing_names))
        self.invalid_names = sorted(set(invalid_names))
        self.invalid_binds = list(dict.fromkeys(invalid_binds))
        self.fields = sorted(set(fields))
        self.snippet = snippet
        self.env_profile = env_profile
        super().__init__(self._message())

    def _message(self) -> str:
        parts = [self.code + ":"]
        if self.missing_names:
            parts.append(f"missing=[{', '.join(self.missing_names)}]")
        if self.invalid_names:
            parts.append(f"invalid_names=[{', '.join(self.invalid_names)}]")
        if self.invalid_binds:
            parts.append(f"invalid_binds=[{', '.join(self.invalid_binds)}]")
        if self.fields:
            parts.append(f"fields=[{', '.join(self.fields)}]")
        if self.env_profile is not None:
            parts.append(f"env_profile={self.env_profile}")
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """JSON form matching ``$defs/resolve_error`` in the published schema."""
        out: dict[str, Any] = {
            "code": self.code,
            "message": self._message(),
            "missing_names": list(self.missing_names),
            "invalid_names": list(self.invalid_names),
            "invalid_binds": list(self.invalid_binds),
            "fields": list(self.fields),
            "snippet": self.snippet,
        }
        if self.env_profile is not None:
            out["env_profile"] = self.env_profile
        return out


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------


def is_identifier(name: Any) -> bool:
    return isinstance(name, str) and bool(_IDENTIFIER_RE.match(name))


def _secret_texts(vars: Mapping[str, Any]) -> list[str]:
    texts = {
        render_value(v.reveal())
        for v in vars.values()
        if isinstance(v, SecretValue)
    }
    texts.discard("")
    return sorted(texts, key=lambda t: (-len(t), t))


def redact(text: str, vars: Mapping[str, Any]) -> str:
    """Replace every secret value from ``vars`` occurring in ``text``."""
    for secret in _secret_texts(vars):
        text = text.replace(secret, REDACTED)
    return text


def _snippet(template: str, vars: Mapping[str, Any]) -> str:
    text = redact(template, vars)
    if len(text) > _SNIPPET_MAX:
        text = text[: _SNIPPET_MAX - 3] + "..."
    return text


def render_value(value: Any) -> str:
    """Text form of a bound value: ``str`` as-is, otherwise canonical compact JSON."""
    if isinstance(value, SecretValue):
        return render_value(value.reveal())
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class _Scan:
    names: list[str] = field(default_factory=list)
    invalid_binds: list[str] = field(default_factory=list)


def _invalid_bind_text(template: str, start: int) -> str:
    end = template.find("}}", start + 2)
    text = template[start:] if end == -1 else template[start : end + 2]
    if len(text) > _INVALID_BIND_MAX:
        text = text[: _INVALID_BIND_MAX - 3] + "..."
    return text


def _scan(template: str) -> _Scan:
    scan = _Scan()
    for m in _TOKEN_RE.finditer(template):
        tok = m.group(0)
        if tok.startswith("\\"):
            continue
        if m.group(1) is not None:
            if m.group(1) not in scan.names:
                scan.names.append(m.group(1))
        else:
            scan.invalid_binds.append(_invalid_bind_text(template, m.start()))
    return scan


def find_bind_names(template: str) -> list[str]:
    """Unique bound identifiers in first-occurrence order (escaped binds skipped)."""
    return _scan(template).names


def undefined_names(template: str, vars: Mapping[str, Any]) -> list[str]:
    """Defined-name check: bound identifiers absent from ``vars``, sorted."""
    return sorted(n for n in _scan(template).names if n not in vars)


def check_template(
    template: str,
    vars: Mapping[str, Any],
    *,
    field_name: Optional[str] = None,
) -> Optional[ResolveError]:
    """Return the ResolveError ``resolve_template`` would raise, or ``None``."""
    scan = _scan(template)
    missing = [n for n in scan.names if n not in vars]
    if not scan.invalid_binds and not missing:
        return None
    code = ERROR_INVALID_BIND if scan.invalid_binds else ERROR_UNDEFINED_VARIABLE
    snippet = _snippet(template, vars)
    if field_name is not None:
        snippet = f"{field_name}: {snippet}"
    return ResolveError(
        code,
        missing_names=missing,
        invalid_binds=[redact(b, vars) for b in scan.invalid_binds],
        fields=[field_name] if field_name is not None else [],
        snippet=snippet,
    )


def resolve_template(template: str, vars: Mapping[str, Any]) -> str:
    """Substitute ``{{identifier}}``; honour ``\\{{``; fail closed otherwise."""
    err = check_template(template, vars)
    if err is not None:
        raise err

    def _sub(m: re.Match[str]) -> str:
        tok = m.group(0)
        if tok.startswith("\\"):
            return "{{"
        return render_value(vars[m.group(1)])

    return _TOKEN_RE.sub(_sub, template)


def check_fields(
    fields: Mapping[str, Any], vars: Mapping[str, Any]
) -> Optional[ResolveError]:
    """Aggregate check over top-level string fields (Q-VAR-2), keys in sorted order."""
    errors = [
        e
        for key in sorted(fields)
        if isinstance(fields[key], str)
        for e in [check_template(fields[key], vars, field_name=key)]
        if e is not None
    ]
    if not errors:
        return None
    invalid = [b for e in errors for b in e.invalid_binds]
    return ResolveError(
        ERROR_INVALID_BIND if invalid else ERROR_UNDEFINED_VARIABLE,
        missing_names=[n for e in errors for n in e.missing_names],
        invalid_binds=invalid,
        fields=[f for e in errors for f in e.fields],
        snippet=errors[0].snippet,
    )


def resolve_fields(
    fields: Mapping[str, Any], vars: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve top-level ``str`` values; non-strings pass through unchanged.

    All-or-nothing: on any failure nothing is returned (no partial inputs).
    """
    err = check_fields(fields, vars)
    if err is not None:
        raise err
    return {
        k: (resolve_template(v, vars) if isinstance(v, str) else v)
        for k, v in fields.items()
    }


def effective_vars(
    *,
    env: Mapping[str, Any],
    flow: Mapping[str, Any],
    defaults: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Merge scopes flow > env > defaults (DES-0008-G); names must be identifiers."""
    scopes = [defaults or {}, env or {}, flow or {}]
    invalid = [k for scope in scopes for k in scope if not is_identifier(k)]
    if invalid:
        raise ResolveError(
            ERROR_INVALID_VARIABLE_NAME, invalid_names=[str(k) for k in invalid]
        )
    merged: dict[str, Any] = {}
    for scope in scopes:
        merged.update(scope)
    return merged


def snapshot_vars(vars: Mapping[str, Any]) -> dict[str, Any]:
    """JSON-safe snapshot for ``payload["vars"]``: secrets become :data:`REDACTED`."""
    return {
        k: (REDACTED if isinstance(v, SecretValue) else v)
        for k, v in sorted(vars.items())
    }


# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------


class VariableResolverPort(Protocol):
    """Merge variable scopes and resolve ``{{var}}`` templates (DES-0008-F)."""

    def effective_vars(
        self,
        *,
        env: Mapping[str, Any],
        flow: Mapping[str, Any],
        defaults: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        ...

    def resolve_template(self, template: str, vars: Mapping[str, Any]) -> str:
        ...

    def resolve_fields(
        self, fields: Mapping[str, Any], vars: Mapping[str, Any]
    ) -> dict[str, Any]:
        ...

    def check_fields(
        self, fields: Mapping[str, Any], vars: Mapping[str, Any]
    ) -> Optional[ResolveError]:
        ...


class EnvironmentSource(Protocol):
    """Adapter-owned Environment profile loader (DES-0008 §4.2 / Q-VAR-4).

    ``profile_id is None`` → empty map; unknown id → raise
    ``ResolveError(env_profile_not_found)`` (fail closed).
    """

    def load(self, profile_id: Optional[str]) -> Mapping[str, Any]:
        ...


class KernelVariableResolver:
    """Reference implementation of :class:`VariableResolverPort` (pure, no I/O)."""

    def effective_vars(
        self,
        *,
        env: Mapping[str, Any],
        flow: Mapping[str, Any],
        defaults: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        return effective_vars(env=env, flow=flow, defaults=defaults)

    def resolve_template(self, template: str, vars: Mapping[str, Any]) -> str:
        return resolve_template(template, vars)

    def resolve_fields(
        self, fields: Mapping[str, Any], vars: Mapping[str, Any]
    ) -> dict[str, Any]:
        return resolve_fields(fields, vars)

    def check_fields(
        self, fields: Mapping[str, Any], vars: Mapping[str, Any]
    ) -> Optional[ResolveError]:
        return check_fields(fields, vars)


def station_input_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Payload keys treated as node-field templates at run accept.

    Excludes the reserved ``vars`` bag and ``_``-prefixed gateway notes.
    """
    return {
        k: v
        for k, v in payload.items()
        if k != VARS_PAYLOAD_KEY and not str(k).startswith("_")
    }


# --------------------------------------------------------------------------
# Language-neutral exchange (docs/contracts/variable-resolver-0.1.schema.json)
# --------------------------------------------------------------------------


def resolve_exchange(
    request: Mapping[str, Any],
    resolver: Optional[VariableResolverPort] = None,
    environment_source: Optional[EnvironmentSource] = None,
) -> dict[str, Any]:
    """Evaluate a ``resolve_request`` document and return a response document.

    Response is ``{"schema", "ok": true, "fields", "vars"}`` on success or
    ``{"schema", "ok": false, "error"}`` on failure; ``vars`` is the redacted
    snapshot. Mirrors the gateway path so non-Python consumers can check parity
    against the published test vectors.
    """
    impl: VariableResolverPort = resolver or KernelVariableResolver()
    secret = frozenset(request.get("secret_names") or ())

    def _wrap(scope: Optional[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            k: (SecretValue(v) if k in secret else v) for k, v in (scope or {}).items()
        }

    try:
        env: dict[str, Any] = _wrap(request.get("env"))
        profile = request.get("env_profile")
        if profile is not None or environment_source is not None:
            if environment_source is None:
                raise ResolveError(ERROR_ENV_PROFILE_NOT_FOUND, env_profile=profile)
            env = {**dict(environment_source.load(profile)), **env}
        effective = impl.effective_vars(
            env=env,
            flow=_wrap(request.get("flow")),
            defaults=_wrap(request.get("defaults")),
        )
        fields = impl.resolve_fields(request.get("fields") or {}, effective)
    except ResolveError as err:
        return {"schema": SCHEMA_ID, "ok": False, "error": err.to_dict()}
    return {
        "schema": SCHEMA_ID,
        "ok": True,
        "fields": fields,
        "vars": snapshot_vars(effective),
    }
