"""Shared fixtures for Hextory tests."""

from __future__ import annotations

import pytest

from src.graphs.registry import GraphRegistry
from src.graphs.starter import register_starter
from src.policies.gate import PolicyGatekeeper
from src.ports.sdd_status import SddStatus


class FakeSddStatusReader:
    def __init__(self, mapping: dict[str, SddStatus] | None = None) -> None:
        self.mapping = mapping or {"DES-0002": SddStatus.APPROVED}

    def get_status(self, sdd_id: str) -> SddStatus:
        return self.mapping.get(sdd_id, SddStatus.UNKNOWN)

    def is_approved(self, sdd_id: str) -> bool:
        return self.get_status(sdd_id) == SddStatus.APPROVED


@pytest.fixture
def approved_reader() -> FakeSddStatusReader:
    return FakeSddStatusReader({"DES-0002": SddStatus.APPROVED, "DES-0001": SddStatus.APPROVED})


@pytest.fixture
def gatekeeper(approved_reader: FakeSddStatusReader) -> PolicyGatekeeper:
    return PolicyGatekeeper(approved_reader)


@pytest.fixture
def starter_registry() -> GraphRegistry:
    registry = GraphRegistry()
    register_starter(registry, sdd_id="DES-0002")
    return registry
