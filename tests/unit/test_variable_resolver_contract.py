"""TEST-VAR-10 — language-neutral JSON Schema + shared vectors (DES-0008 A-3).

``docs/contracts/variable-resolver-0.1.schema.json`` is the published contract
for non-Python consumers; ``variable-resolver-0.1.vectors.json`` holds shared
test vectors so every implementation (kernel, adapters, authoring stubs) keeps
one grammar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.ports.variable_resolver import (
    ERROR_CODES,
    IDENTIFIER_PATTERN,
    REDACTED,
    SCHEMA_ID,
    ResolveError,
    resolve_exchange,
)

REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "docs" / "contracts"
SCHEMA_PATH = CONTRACTS / "variable-resolver-0.1.schema.json"
VECTORS_PATH = CONTRACTS / "variable-resolver-0.1.vectors.json"

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["vectors"]
VALIDATOR = Draft202012Validator(SCHEMA)


def _sub(name: str) -> Draft202012Validator:
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]})


def test_var_10_schema_is_valid_draft_2020_12_and_names_schema_id():
    """
    TEST-VAR-10
    Given the published resolver schema
    When it is checked against the JSON Schema 2020-12 meta-schema
    Then it is valid and its title / const match the kernel SCHEMA_ID
    """
    Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["title"] == SCHEMA_ID
    assert SCHEMA["$defs"]["schema_id"]["const"] == SCHEMA_ID


def test_var_10_schema_grammar_and_codes_match_kernel():
    """
    TEST-VAR-10 / DES-0008-B (no split-brain grammar)
    Given the schema identifier pattern, error-code enum and redaction marker
    When compared with the Python kernel constants
    Then they are identical
    """
    assert SCHEMA["$defs"]["identifier"]["pattern"] == f"^{IDENTIFIER_PATTERN}$"
    assert set(SCHEMA["$defs"]["resolve_error"]["properties"]["code"]["enum"]) == set(ERROR_CODES)
    assert SCHEMA["$defs"]["redaction_marker"]["const"] == REDACTED


@pytest.mark.parametrize("vector", VECTORS, ids=[v["id"] for v in VECTORS])
def test_var_10_vectors_validate_and_kernel_matches_expected(vector):
    """
    TEST-VAR-10 (shared vectors)
    Given a published vector request
    When the kernel evaluates it via resolve_exchange
    Then request (unless marked invalid) and response validate and equal the expected response
    """
    if vector["request_schema_valid"]:
        VALIDATOR.validate(vector["request"])
    else:
        assert not _sub("resolve_request").is_valid(vector["request"])
    got = resolve_exchange(vector["request"])
    VALIDATOR.validate(got)
    VALIDATOR.validate(vector["expected"])
    assert got == vector["expected"]


def test_var_10_error_to_dict_always_validates():
    """
    TEST-VAR-10
    Given one ResolveError per error code
    When serialized with to_dict()
    Then each validates against $defs/resolve_error
    """
    validator = _sub("resolve_error")
    for code in sorted(ERROR_CODES):
        err = ResolveError(code, missing_names=["b", "a"], env_profile="p")
        validator.validate(err.to_dict())


@pytest.mark.parametrize(
    "doc",
    [
        {"fields": {}, "flow": {"node.output": "x"}},  # non-identifier var name
        {"flow": {}},  # fields required
        {"ok": True, "fields": {}},  # success without vars
        {"ok": False, "error": {"code": "boom"}},  # unknown code / missing members
        {"fields": {}, "unexpected": 1},  # closed request shape
    ],
)
def test_var_10_schema_rejects_malformed_documents(doc):
    """
    TEST-VAR-10
    Given a malformed request or response document
    When it is validated
    Then the schema rejects it
    """
    assert not VALIDATOR.is_valid(doc)
