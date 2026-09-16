"""Local LLM adapters: echo + env-selected mode (no mandatory cloud keys).

``HEXTORY_LLM_MODE``:
  - ``null`` (default) → NullLlm
  - ``echo`` → EchoLlm (returns a readable echo of the prompt)
  - ``openai`` → optional thin OpenAI-compatible client; **fail-closed** if
    ``HEXTORY_OPENAI_API_KEY`` / ``OPENAI_API_KEY`` unset (raises clear error;
    never used by default tests).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from src.ports.llm import LlmPort, NullLlm


class EchoLlm:
    """Deterministic local adapter: echoes a short note derived from the prompt."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        snippet = prompt.strip().replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        return f"echo: {snippet}"


class OpenAiCompatibleLlm:
    """Thin OpenAI-compatible chat completion client. Fail-closed without a key."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        if not api_key:
            raise ValueError(
                "OpenAI-compatible LLM requires an API key "
                "(HEXTORY_OPENAI_API_KEY or OPENAI_API_KEY)"
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    def complete(self, prompt: str, **kwargs: Any) -> str:
        model = str(kwargs.get("model") or self._model)
        body = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - network
            raise RuntimeError(f"OpenAI-compatible request failed: {exc}") from exc
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


def llm_from_env(environ: Optional[dict[str, str]] = None) -> LlmPort:
    """Build an LlmPort from env. Default ``null`` — never requires cloud keys."""
    env = environ if environ is not None else dict(os.environ)
    mode = (env.get("HEXTORY_LLM_MODE") or "null").strip().lower()
    if mode in ("", "null", "none", "off"):
        return NullLlm()
    if mode == "echo":
        return EchoLlm()
    if mode in ("openai", "openai_compatible"):
        key = env.get("HEXTORY_OPENAI_API_KEY") or env.get("OPENAI_API_KEY") or ""
        if not key:
            raise ValueError(
                "HEXTORY_LLM_MODE=openai but no API key set "
                "(HEXTORY_OPENAI_API_KEY / OPENAI_API_KEY); fail-closed"
            )
        base = env.get("HEXTORY_OPENAI_BASE_URL") or "https://api.openai.com/v1"
        model = env.get("HEXTORY_OPENAI_MODEL") or "gpt-4o-mini"
        return OpenAiCompatibleLlm(api_key=key, base_url=base, model=model)
    raise ValueError(
        f"unknown HEXTORY_LLM_MODE={mode!r}; expected null|echo|openai"
    )
