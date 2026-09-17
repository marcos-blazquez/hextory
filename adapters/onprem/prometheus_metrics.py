"""Prometheus MetricsPort exporter for on-prem (DES-0006-C).

``prometheus_client`` is imported only here — never under ``src/``.
"""

from __future__ import annotations

from typing import Mapping, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    generate_latest,
)

from src.ports.metrics import (
    METRIC_GATE_DENIALS,
    METRIC_QUALITY_FAIL,
    METRIC_REWORK,
    METRIC_RUNS_ACCEPTED,
    METRIC_RUNS_TERMINAL,
    sanitize_labels,
)


class PrometheusMetrics:
    """Adapter MetricsPort backed by a private CollectorRegistry."""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        self.registry = registry or CollectorRegistry()
        self._counters: dict[str, Counter] = {}
        self._labelnames: dict[str, tuple[str, ...]] = {}
        # Pre-register frozen series so /metrics exposes them even at zero.
        self._register(
            METRIC_GATE_DENIALS,
            "Gatekeeper denials (not auth 401)",
            ("workflow_id",),
        )
        self._register(
            METRIC_RUNS_ACCEPTED,
            "Runs accepted by gateway after Gatekeeper allow",
            ("workflow_id",),
        )
        self._register(
            METRIC_RUNS_TERMINAL,
            "Runs that reached a terminal status",
            ("workflow_id", "status"),
        )
        self._register(
            METRIC_QUALITY_FAIL,
            "Quality FAIL evaluations",
            ("workflow_id",),
        )
        self._register(
            METRIC_REWORK,
            "Rework routes scheduled after Quality FAIL",
            ("workflow_id",),
        )

    def _register(
        self, name: str, documentation: str, labelnames: tuple[str, ...]
    ) -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(
                name,
                documentation,
                labelnames=labelnames,
                registry=self.registry,
            )
            self._labelnames[name] = labelnames
        return self._counters[name]

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        clean = sanitize_labels(labels)
        if name not in self._counters:
            labelnames = tuple(sorted(clean.keys()))
            self._register(name, f"Hextory metric {name}", labelnames)
        counter = self._counters[name]
        labelnames = self._labelnames[name]
        if labelnames:
            label_values = {ln: clean.get(ln, "") for ln in labelnames}
            counter.labels(**label_values).inc(value)
        else:
            counter.inc(value)

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        # First slice: no histograms yet — fold into increment for dump parity.
        self.increment(name, value=value, labels=labels)

    def exposition(self) -> tuple[bytes, str]:
        """Return (body, content_type) for GET /metrics."""
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
