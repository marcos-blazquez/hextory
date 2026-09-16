"""File-backed IdempotencyStore under ``.hextory/idempotency/``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(key: str) -> str:
    cleaned = _SAFE.sub("_", key.strip())
    return cleaned or "unnamed"


class FileIdempotencyStore:
    """Persist key → traveler_id as JSON files under ``store_dir/idempotency/``."""

    def __init__(self, store_dir: Path | str) -> None:
        self.root = Path(store_dir) / "idempotency"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / f"{_safe_segment(key)}.json"

    def get(self, key: str) -> Optional[str]:
        path = self._path(key)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        tid = data.get("traveler_id")
        return str(tid) if tid else None

    def put(self, key: str, traveler_id: str) -> None:
        path = self._path(key)
        if path.is_file():
            return  # first write wins
        payload = {"idempotency_key": key, "traveler_id": traveler_id}
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

