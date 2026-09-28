"""Local in-memory Environment source for ``VariableResolverPort`` (DES-0008).

Holds named Environment profiles (name → value maps) in memory. Names listed in
``secret_names`` are wrapped in :class:`SecretValue` on load, modelling an
adapter that injects secret-backed env vars at resolve time (DES-0008 §3.3).

Profile semantics (Q-VAR-4, first slice):
  - ``load(None)`` → empty map
  - ``load("<unknown>")`` → ``ResolveError(env_profile_not_found)`` (fail closed)
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from src.ports.variable_resolver import (
    ERROR_ENV_PROFILE_NOT_FOUND,
    ERROR_INVALID_VARIABLE_NAME,
    ResolveError,
    SecretValue,
    is_identifier,
)


class InMemoryEnvironmentSource:
    """``EnvironmentSource`` backed by in-process dicts (tests / local CLI)."""

    def __init__(
        self,
        profiles: Optional[Mapping[str, Mapping[str, Any]]] = None,
        *,
        secret_names: Iterable[str] = (),
    ) -> None:
        self._profiles: dict[str, dict[str, Any]] = {
            str(pid): dict(values) for pid, values in (profiles or {}).items()
        }
        self._secret_names = frozenset(secret_names)
        invalid = [
            str(name)
            for values in self._profiles.values()
            for name in values
            if not is_identifier(name)
        ]
        if invalid:
            raise ResolveError(ERROR_INVALID_VARIABLE_NAME, invalid_names=invalid)

    def profile_ids(self) -> list[str]:
        return sorted(self._profiles)

    def load(self, profile_id: Optional[str]) -> dict[str, Any]:
        if profile_id is None:
            return {}
        if profile_id not in self._profiles:
            raise ResolveError(ERROR_ENV_PROFILE_NOT_FOUND, env_profile=profile_id)
        return {
            name: (
                SecretValue(value)
                if name in self._secret_names and not isinstance(value, SecretValue)
                else value
            )
            for name, value in self._profiles[profile_id].items()
        }

    def __repr__(self) -> str:
        return (
            f"InMemoryEnvironmentSource(profiles={self.profile_ids()!r}, "
            f"secret_names={sorted(self._secret_names)!r})"
        )
