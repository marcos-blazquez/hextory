"""Adapter tests: EchoLlm + llm_from_env (fail-closed openai)."""

from __future__ import annotations

import pytest

from adapters.local.echo_llm import EchoLlm, llm_from_env
from src.ports.llm import NullLlm


def test_echo_llm_prefixes_prompt():
    out = EchoLlm().complete("hello world")
    assert out.startswith("echo:")
    assert "hello world" in out


def test_llm_from_env_default_null():
    llm = llm_from_env({})
    assert isinstance(llm, NullLlm)
    assert llm.complete("x") == ""


def test_llm_from_env_echo():
    llm = llm_from_env({"HEXTORY_LLM_MODE": "echo"})
    assert isinstance(llm, EchoLlm)


def test_llm_from_env_openai_fail_closed_without_key():
    with pytest.raises(ValueError, match="fail-closed|API key"):
        llm_from_env({"HEXTORY_LLM_MODE": "openai"})


def test_llm_from_env_unknown_mode():
    with pytest.raises(ValueError, match="unknown"):
        llm_from_env({"HEXTORY_LLM_MODE": "banana"})
