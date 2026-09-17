"""On-prem HTTP adapter (DES-0004) — FastAPI + JWT + Postgres checkpointer.

Core ``src/`` is never imported from here into reverse; this package binds
ports only. AWS and Studio remain out of scope.
"""

from adapters.onprem.app import create_app

__all__ = ["create_app"]
