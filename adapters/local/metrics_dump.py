"""Local CLI metrics dump (DES-0006 / Q-OBS-3).

Stdout or file dump of the same instrument names used by on-prem /metrics.
No HTTP scrape endpoint on the local adapter for first slice.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, TextIO, Union

from src.ports.metrics import InMemoryMetrics, MetricsPort


def dump_metrics(
    metrics: MetricsPort,
    *,
    dest: Optional[Union[str, Path]] = None,
    stream: Optional[TextIO] = None,
) -> str:
    """Dump counter lines to stdout (default) or ``dest`` file path.

    Returns the dump text. Non-InMemoryMetrics sinks yield an empty dump
    unless they expose ``dump_text``.
    """
    if hasattr(metrics, "dump_text"):
        text = metrics.dump_text()  # type: ignore[attr-defined]
    elif isinstance(metrics, InMemoryMetrics):
        text = metrics.dump_text()
    else:
        text = ""

    if dest is not None:
        path = Path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        out = stream or sys.stdout
        if text:
            out.write(text if text.endswith("\n") else text + "\n")
            out.flush()
    return text
