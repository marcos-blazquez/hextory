"""Run the on-prem FastAPI app: ``python -m adapters.onprem``."""

from __future__ import annotations

import os


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            'uvicorn is required; install with: pip install -e ".[onprem]"'
        ) from exc

    host = os.environ.get("HEXTORY_ONPREM_HOST", "0.0.0.0")
    port = int(os.environ.get("HEXTORY_ONPREM_PORT", "8080"))
    uvicorn.run("adapters.onprem.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
