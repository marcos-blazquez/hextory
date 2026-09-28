"""TEST-VAR-09 — local in-memory Environment source adapter (DES-0008 §4.2 / Q-VAR-4)."""

from __future__ import annotations

import pytest

from adapters.local.variable_source import InMemoryEnvironmentSource
from src.ports.variable_resolver import (
    ERROR_ENV_PROFILE_NOT_FOUND,
    ERROR_INVALID_VARIABLE_NAME,
    REDACTED,
    EnvironmentSource,
    ResolveError,
    SecretValue,
    snapshot_vars,
)


def test_var_09_given_no_profile_id_when_loading_then_empty_env():
    """
    TEST-VAR-09 / Q-VAR-4 (omit id → empty env)
    Given an in-memory source with a staging profile
    When load(None) is called
    Then an empty Environment map is returned
    """
    src: EnvironmentSource = InMemoryEnvironmentSource({"staging": {"region": "eu"}})
    assert dict(src.load(None)) == {}


def test_var_09_given_known_profile_when_loading_then_copy_of_map():
    """
    TEST-VAR-09
    Given a staging profile
    When load("staging") is called and the result mutated
    Then values are returned and the adapter's stored profile is not affected
    """
    src = InMemoryEnvironmentSource({"staging": {"region": "eu"}})
    loaded = dict(src.load("staging"))
    loaded["region"] = "mutated"
    assert dict(src.load("staging")) == {"region": "eu"}


def test_var_09_given_unknown_profile_when_loading_then_fail_closed():
    """
    TEST-VAR-09 / Q-VAR-4 (present-but-missing → fail closed)
    Given a source without a "prod" profile
    When load("prod") is called
    Then ResolveError(env_profile_not_found) names the profile
    """
    src = InMemoryEnvironmentSource({"staging": {}})
    with pytest.raises(ResolveError) as exc:
        src.load("prod")
    assert exc.value.code == ERROR_ENV_PROFILE_NOT_FOUND
    assert exc.value.env_profile == "prod"


def test_var_09_given_secret_names_when_loading_then_values_wrapped_and_redacted():
    """
    TEST-VAR-09 / TEST-VAR-08 (adapter injects secret-backed env vars)
    Given a profile whose api_token is declared secret
    When the profile loads
    Then api_token is a SecretValue and snapshots show only the redaction marker
    """
    src = InMemoryEnvironmentSource(
        {"staging": {"api_token": "tok-123", "region": "eu"}},
        secret_names={"api_token"},
    )
    env = src.load("staging")
    assert isinstance(env["api_token"], SecretValue)
    assert env["api_token"].reveal() == "tok-123"
    assert snapshot_vars(env) == {"api_token": REDACTED, "region": "eu"}
    assert "tok-123" not in repr(src)


def test_var_09_given_invalid_name_in_profile_when_constructing_then_rejected():
    """
    TEST-VAR-09 / TEST-VAR-11 (defined names are identifiers)
    Given a profile defining "bad-name"
    When the source is constructed
    Then ResolveError(invalid_variable_name) is raised up front
    """
    with pytest.raises(ResolveError) as exc:
        InMemoryEnvironmentSource({"staging": {"bad-name": "x"}})
    assert exc.value.code == ERROR_INVALID_VARIABLE_NAME
