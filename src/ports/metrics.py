"""Metrics / Telemetry port (DES-0006-B).

Core records domain metric *facts* through this protocol. Prometheus, OTel,
Grafana, and scrape HTTP live only in adapters — never import them here.
"""

from __future__ import annotations

import logging
from typing import Mapping, MutableMapping, Optional, Protocol, Sequence

logger = logging.getLogger(__name__)

# Frozen first-slice names (TEST-OBS / Q-OBS-4).
METRIC_GATE_DENIALS = "hextory_gate_denials_total"
METRIC_RUNS_ACCEPTED = "hextory_runs_accepted_total"
METRIC_RUNS_TERMINAL = "hextory_runs_terminal_total"
METRIC_QUALITY_FAIL = "hextory_quality_fail_total"
METRIC_REWORK = "hextory_rework_total"

FROZEN_METRIC_NAMES: frozenset[str] = frozenset(
    {
        METRIC_GATE_DENIALS,
        METRIC_RUNS_ACCEPTED,
        METRIC_RUNS_TERMINAL,
        METRIC_QUALITY_FAIL,
        METRIC_REWORK,
    }
)

# Q-OBS-2: low-cardinality labels only; forbid traveler / PII keys.
ALLOWED_LABEL_KEYS: frozenset[str] = frozenset({"workflow_id", "status"})
FORBIDDEN_LABEL_KEYS: frozenset[str] = frozenset(
    {
        "traveler_id",
        "email",
        "payload",
        "secret",
        "token",
        "password",
        "idempotency_key",
    }
)


def sanitize_labels(
    labels: Optional[Mapping[str, str]] = None,
) -> dict[str, str]:
    """Drop forbidden / high-cardinality keys; keep only allowed keys."""
    if not labels:
        return {}
    out: dict[str, str] = {}
    for key, value in labels.items():
        if key in FORBIDDEN_LABEL_KEYS:
            continue
        if key not in ALLOWED_LABEL_KEYS:
            continue
        out[key] = str(value)
    return out


class MetricsPort(Protocol):
    """Record metric facts without exporter I/O libraries."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        ...

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        ...


class NoOpMetrics:
    """Default metrics sink — swallows all facts."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        return None

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        return None


class InMemoryMetrics:
    """Test / local-CLI sink: accumulates counters for assertions and dumps."""

    def __init__(self) -> None:
        # (name, frozenset labels) -> value
        self._counters: MutableMapping[tuple[str, frozenset[tuple[str, str]]], float] = {}
        self.events: list[tuple[str, float, dict[str, str]]] = []

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        clean = sanitize_labels(labels)
        key = (name, frozenset(clean.items()))
        self._counters[key] = self._counters.get(key, 0.0) + float(value)
        self.events.append((name, float(value), clean))

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        # First slice: treat observe as a labeled sample counter for dump/tests.
        self.increment(name, value=value, labels=labels)

    def get(self, name: str, labels: Optional[Mapping[str, str]] = None) -> float:
        clean = sanitize_labels(labels)
        return float(self._counters.get((name, frozenset(clean.items())), 0.0))

    def total(self, name: str) -> float:
        return float(
            sum(v for (n, _), v in self._counters.items() if n == name)
        )

    def dump_lines(self) -> list[str]:
        """Prometheus-ish text lines for stdout/file dump (Q-OBS-3)."""
        lines: list[str] = []
        for (name, label_items), value in sorted(
            self._counters.items(), key=lambda x: (x[0][0], sorted(x[0][1]))
        ):
            if label_items:
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in sorted(label_items)
                )
                lines.append(f"{name}{{{label_str}}} {value:g}")
            else:
                lines.append(f"{name} {value:g}")
        return lines

    def dump_text(self) -> str:
        return "\n".join(self.dump_lines()) + ("\n" if self._counters else "")


class SafeMetrics:
    """Best-effort wrapper: metric failures never raise into the run path."""

    def __init__(self, inner: MetricsPort) -> None:
        self._inner = inner

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        try:
            self._inner.increment(name, value=value, labels=labels)
        except Exception:  # noqa: BLE001 — observability must not fail runs
            logger.exception("metrics increment failed name=%s", name)

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        try:
            self._inner.observe(name, value, labels=labels)
        except Exception:  # noqa: BLE001
            logger.exception("metrics observe failed name=%s", name)


def labels_contain_forbidden(labels: Mapping[str, str]) -> Sequence[str]:
    """Return forbidden keys present (for TEST-OBS-08)."""
    return [k for k in labels if k in FORBIDDEN_LABEL_KEYS]
