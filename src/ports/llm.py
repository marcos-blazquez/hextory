"""LLM port — optional model assist for departments (DES-0002 / Q-LLM-1).

``NullLlm`` remains the default for tests. ``ScriptedLlm`` gives deterministic
prompt→response maps without cloud keys. Concrete adapters (echo / env) live
under ``adapters/local``; ``src/`` never imports them.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol


class LlmPort(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> str:
        ...


class NullLlm:
    """No-op LLM; returns empty string. Safe default for tests."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        return ""


class ScriptedLlm:
    """Deterministic fake: exact prompt match, optional prefix/default.

    Useful in unit/behavior tests without network or API keys.
    """

    def __init__(
        self,
        scripts: Optional[Mapping[str, str]] = None,
        *,
        default: str = "",
        prefix_scripts: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._scripts = dict(scripts or {})
        self._prefix = dict(prefix_scripts or {})
        self._default = default
        self.calls: list[str] = []

    def complete(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append(prompt)
        if prompt in self._scripts:
            return self._scripts[prompt]
        for prefix, response in self._prefix.items():
            if prompt.startswith(prefix):
                return response
        return self._default


# Alias kept for callers who prefer FakeLlm naming.
FakeLlm = ScriptedLlm
