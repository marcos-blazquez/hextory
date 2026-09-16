"""FileIdempotencyStore under .hextory/idempotency/."""

from __future__ import annotations

from pathlib import Path

from adapters.local.file_idempotency import FileIdempotencyStore


def test_file_idempotency_roundtrip(tmp_path: Path):
    store = FileIdempotencyStore(tmp_path)
    assert store.get("k1") is None
    store.put("k1", "trv_abc")
    assert store.get("k1") == "trv_abc"
    # first write wins
    store.put("k1", "trv_other")
    assert store.get("k1") == "trv_abc"
    assert (tmp_path / "idempotency").is_dir()
