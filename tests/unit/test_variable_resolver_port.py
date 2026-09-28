"""TEST-VAR-01/02/03/04/08/11 — VariableResolverPort + pure bind helpers (DES-0008).

Traceability: REQ-0020 (proposed) / REQ-0010 → DES-0008-B/C/D/F/G + §3.3 secrets.
Style: TDD unit tests with Given/When/Then docstrings (ordinary pytest, no Cucumber).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.ports import (
    KernelVariableResolver,
    ResolveError,
    SecretValue,
    VariableResolverPort,
)
from src.ports.variable_resolver import (
    ERROR_INVALID_BIND,
    ERROR_INVALID_VARIABLE_NAME,
    ERROR_UNDEFINED_VARIABLE,
    REDACTED,
    find_bind_names,
    snapshot_vars,
    undefined_names,
)

REPO = Path(__file__).resolve().parents[2]
PORT_FILE = REPO / "src" / "ports" / "variable_resolver.py"


@pytest.fixture
def resolver() -> KernelVariableResolver:
    return KernelVariableResolver()


# --- TEST-VAR-01 ---------------------------------------------------------


def test_var_01_port_importable_from_src_ports_and_kernel_impl_conforms():
    """
    TEST-VAR-01 / AC-VAR-01 / DES-0008-F
    Given the public ports package
    When VariableResolverPort and the kernel resolver are imported
    Then the kernel resolver exposes effective_vars / resolve_template / resolve_fields
    """
    # Given / When
    impl: VariableResolverPort = KernelVariableResolver()
    # Then
    for name in ("effective_vars", "resolve_template", "resolve_fields", "check_fields"):
        assert callable(getattr(impl, name))


def test_var_01_port_module_has_no_adapter_os_env_or_io_imports():
    """
    TEST-VAR-01 / AC-VAR-01 (+ TEST-0010 family)
    Given src/ports/variable_resolver.py
    When its imports are scanned
    Then it imports no adapters, OS-environment, network, or secret-store modules
    """
    # Given
    tree = ast.parse(PORT_FILE.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    # When
    banned_roots = {"adapters", "os", "boto3", "urllib", "socket", "subprocess", "http"}
    offenders = [m for m in mods if m.split(".", 1)[0] in banned_roots]
    # Then
    assert offenders == []


# --- TEST-VAR-02 ---------------------------------------------------------


def test_var_02_given_defined_names_when_resolving_then_binds_substitute(resolver):
    """
    TEST-VAR-02 / AC-VAR-02 / DES-0008-B
    Given an effective map with flow_greeting and region
    When "Say {{flow_greeting}} to {{region}}" is resolved
    Then both binds are substituted
    """
    # Given
    vars_ = {"flow_greeting": "hi", "region": "eu-west"}
    # When
    out = resolver.resolve_template("Say {{flow_greeting}} to {{region}}", vars_)
    # Then
    assert out == "Say hi to eu-west"


def test_var_02_given_escaped_open_when_resolving_then_literal_braces(resolver):
    """
    TEST-VAR-02 / AC-VAR-02 / DES-0008-C
    Given a template with \\{{name}} and a stray }}
    When resolved with an empty map
    Then \\{{ becomes a literal {{ (one backslash consumed) and }} is left as-is
    """
    # Given
    template = "literal \\{{name}} and stray }}"
    # When
    out = resolver.resolve_template(template, {})
    # Then
    assert out == "literal {{name}} and stray }}"


def test_var_02_given_empty_string_value_when_resolving_then_defined(resolver):
    """
    TEST-VAR-02 / DES-0008 §5.3 (empty string is defined)
    Given a variable whose value is the empty string
    When a template binds it
    Then it resolves to empty text instead of failing
    """
    assert resolver.resolve_template("[{{blank}}]", {"blank": ""}) == "[]"


def test_var_02_given_non_string_values_when_resolving_then_canonical_json_text(resolver):
    """
    TEST-VAR-02 / DES-0008 §3.1 (JSON-compatible values)
    Given numeric, boolean, null and object values
    When bound into a template
    Then each renders as canonical compact JSON text
    """
    vars_ = {"n": 3, "ok": True, "none": None, "obj": {"b": 1, "a": [1, 2]}}
    out = resolver.resolve_template("{{n}}|{{ok}}|{{none}}|{{obj}}", vars_)
    assert out == '3|true|null|{"a":[1,2],"b":1}'


def test_var_02_given_no_binds_when_resolving_then_text_unchanged(resolver):
    """
    TEST-VAR-02
    Given plain text with single braces
    When resolved
    Then the text is unchanged
    """
    assert resolver.resolve_template("a {b} c }", {}) == "a {b} c }"


def test_var_02_find_bind_names_in_first_occurrence_order():
    """
    TEST-VAR-02
    Given a template repeating and escaping binds
    When bind names are listed
    Then unique names come back in first-occurrence order and escaped binds are skipped
    """
    assert find_bind_names("{{b}} {{a}} {{b}} \\{{c}}") == ["b", "a"]


# --- TEST-VAR-03 ---------------------------------------------------------


def test_var_03_given_undefined_names_when_resolving_then_fail_closed_sorted(resolver):
    """
    TEST-VAR-03 / AC-VAR-03 / DES-0008-D
    Given a template binding zeta and alpha which are not defined
    When it is resolved
    Then ResolveError(undefined_variable) lists missing names sorted, deterministically
    """
    # Given
    template = "{{zeta}} {{known}} {{alpha}} {{zeta}}"
    # When
    with pytest.raises(ResolveError) as exc:
        resolver.resolve_template(template, {"known": "k"})
    # Then
    err = exc.value
    assert err.code == ERROR_UNDEFINED_VARIABLE
    assert err.missing_names == ["alpha", "zeta"]
    assert str(err) == "undefined_variable: missing=[alpha, zeta]"
    # Deterministic: same input → identical structured error.
    with pytest.raises(ResolveError) as again:
        resolver.resolve_template(template, {"known": "k"})
    assert again.value.to_dict() == err.to_dict()


def test_var_03_undefined_names_helper_is_the_defined_name_check():
    """
    TEST-VAR-03 / TEST-VAR-11 (defined-name checking without substitution)
    Given a template and a map
    When undefined_names is called
    Then it returns only the unresolved names, sorted
    """
    assert undefined_names("{{b}} {{a}} {{c}}", {"c": "1"}) == ["a", "b"]
    assert undefined_names("{{c}}", {"c": ""}) == []


def test_var_03_given_resolve_fields_with_missing_when_resolving_then_no_partial_output(resolver):
    """
    TEST-VAR-03 / AC-VAR-03
    Given several station input fields, two of which bind undefined names
    When resolve_fields runs
    Then one aggregated ResolveError names every missing var and every failing field
    """
    # Given
    fields = {"prompt": "hi {{who}}", "url": "{{base}}/x", "ok": "{{known}}", "count": 3}
    # When
    with pytest.raises(ResolveError) as exc:
        resolver.resolve_fields(fields, {"known": "k"})
    # Then
    assert exc.value.missing_names == ["base", "who"]
    assert exc.value.fields == ["prompt", "url"]


# --- TEST-VAR-04 ---------------------------------------------------------


def test_var_04_given_same_key_in_env_and_flow_when_merged_then_flow_wins(resolver):
    """
    TEST-VAR-04 / AC-VAR-04 / DES-0008-G
    Given region defined in defaults, Environment and in-flow
    When effective_vars merges the scopes
    Then in-flow wins over Environment, Environment over defaults, without error
    """
    # Given
    defaults = {"region": "default", "only_default": "d"}
    env = {"region": "env", "only_env": "e"}
    flow = {"region": "flow"}
    # When
    eff = resolver.effective_vars(env=env, flow=flow, defaults=defaults)
    # Then
    assert eff == {"region": "flow", "only_default": "d", "only_env": "e"}
    assert resolver.resolve_template("{{region}}", eff) == "flow"


def test_var_04_given_invalid_defined_name_when_merged_then_fail_closed(resolver):
    """
    TEST-VAR-04 / TEST-VAR-11 / DES-0008-B (defined names must be identifiers)
    Given an in-flow map that defines "node.output" and "1bad"
    When effective_vars merges scopes
    Then ResolveError(invalid_variable_name) lists the offending names sorted
    """
    with pytest.raises(ResolveError) as exc:
        resolver.effective_vars(env={}, flow={"node.output": "x", "1bad": "y", "ok": "z"})
    assert exc.value.code == ERROR_INVALID_VARIABLE_NAME
    assert exc.value.invalid_names == ["1bad", "node.output"]


# --- TEST-VAR-08 (secrets) -----------------------------------------------


def test_var_08_secret_value_never_renders_in_repr_or_str():
    """
    TEST-VAR-08 / DES-0008 §3.3 (never log raw secret values)
    Given a SecretValue
    When it is printed or repr'd
    Then only the redaction marker appears; reveal() returns the raw value
    """
    s = SecretValue("tok-123")
    assert "tok-123" not in repr(s) and "tok-123" not in str(s)
    assert str(s) == REDACTED
    assert s.reveal() == "tok-123"


def test_var_08_given_secret_var_when_resolving_then_value_substitutes_into_station_input(resolver):
    """
    TEST-VAR-08 / DES-0008 §3.3 (adapters inject secret-backed env vars at resolve time)
    Given an Environment map holding a secret-backed api_token
    When a station input binds {{api_token}}
    Then the concrete secret is substituted (the station needs it)
    """
    eff = resolver.effective_vars(env={"api_token": SecretValue("tok-123")}, flow={})
    assert resolver.resolve_template("Bearer {{api_token}}", eff) == "Bearer tok-123"


def test_var_08_given_secret_var_when_snapshotting_then_redacted(resolver):
    """
    TEST-VAR-08 / DES-0008-E + §3.3
    Given an effective map containing a secret
    When the payload["vars"] snapshot is produced
    Then the secret value is replaced by the redaction marker; plain values are kept
    """
    eff = resolver.effective_vars(env={"api_token": SecretValue("tok-123"), "region": "eu"}, flow={})
    assert snapshot_vars(eff) == {"api_token": REDACTED, "region": "eu"}


def test_var_08_given_secret_in_template_text_when_error_then_snippet_redacted(resolver):
    """
    TEST-VAR-08 / DES-0008 §3.3 (redact resolve error snippets)
    Given a template that accidentally embeds a secret's raw value and an undefined bind
    When resolution fails
    Then the error snippet, message and dict never contain the raw secret
    """
    eff = resolver.effective_vars(env={"api_token": SecretValue("tok-123")}, flow={})
    with pytest.raises(ResolveError) as exc:
        resolver.resolve_template("key=tok-123 {{missing}}", eff)
    err = exc.value
    assert "tok-123" not in err.snippet
    assert REDACTED in err.snippet
    assert "tok-123" not in str(err) and "tok-123" not in repr(err.to_dict())


# --- TEST-VAR-11 (grammar strictness / defined-name checking) --------------


@pytest.mark.parametrize(
    "template",
    ["{{node.output.text}}", "{{ spaced }}", "{{1abc}}", "open {{ never closed", "{{}}"],
)
def test_var_11_given_non_identifier_bind_when_resolving_then_invalid_bind(resolver, template):
    """
    TEST-VAR-11 / DES-0008-B / Q-VAR-3 (flat identifiers only in first slice)
    Given an unescaped {{ that does not open a flat {{identifier}} bind
    When the template is resolved
    Then ResolveError(invalid_bind) fails closed instead of passing a raw token on
    """
    with pytest.raises(ResolveError) as exc:
        resolver.resolve_template(template, {"node": "x", "spaced": "y"})
    assert exc.value.code == ERROR_INVALID_BIND
    assert exc.value.invalid_binds


def test_var_11_check_fields_reports_without_substituting(resolver):
    """
    TEST-VAR-11 (defined-name checking for authoring / pre-flight)
    Given station input fields with one undefined bind
    When check_fields runs
    Then it returns a ResolveError value (not raised); a clean set returns None
    """
    err = resolver.check_fields({"a": "{{x}}", "b": "{{y}}"}, {"y": "1"})
    assert isinstance(err, ResolveError)
    assert err.missing_names == ["x"] and err.fields == ["a"]
    assert resolver.check_fields({"b": "{{y}}", "n": 1}, {"y": "1"}) is None


def test_var_11_resolve_fields_passes_non_strings_through(resolver):
    """
    TEST-VAR-11 / Q-VAR-2 (string fields only in first slice)
    Given fields with nested objects containing bind-like text
    When resolve_fields runs
    Then only top-level strings resolve; nested values pass through untouched
    """
    fields = {"s": "{{v}}", "nested": {"t": "{{nope}}"}, "lst": ["{{nope}}"], "n": 1}
    out = resolver.resolve_fields(fields, {"v": "ok"})
    assert out == {"s": "ok", "nested": {"t": "{{nope}}"}, "lst": ["{{nope}}"], "n": 1}
