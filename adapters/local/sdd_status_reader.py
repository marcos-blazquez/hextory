"""Local SddStatusReader (Q-GATE-1 interim).

Fail closed on read/parse error.
MAY use (a) SDD markdown Status field / frontmatter, and/or (b) config/sdd_status
manifest; when both present they must agree — otherwise ERROR (deny).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from src.ports.sdd_status import SddStatus


# DES field table: | **Status** | **Approved** |
_STATUS_LINE = re.compile(
    r"\|\s*\*\*Status\*\*\s*\|\s*\*?\*?([^*\|\n]+)\*?\*?\s*\|",
    re.IGNORECASE,
)
# YAML frontmatter only between leading --- fences
_FRONTMATTER_BLOCK = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FRONTMATTER_STATUS = re.compile(
    r"(?m)^status:\s*[\"']?([A-Za-z]+)[\"']?\s*$",
    re.IGNORECASE,
)


def _normalize(raw: str) -> SddStatus:
    value = raw.strip().strip("*").strip()
    lowered = value.lower()
    if lowered == "approved":
        return SddStatus.APPROVED
    if lowered == "draft":
        return SddStatus.DRAFT
    if not value:
        return SddStatus.UNKNOWN
    # Changes Requested, etc. → not Approved
    return SddStatus.DRAFT


def parse_markdown_status(text: str) -> Optional[SddStatus]:
    """Extract Status from DES table (preferred) or YAML frontmatter only.

    Ignores incidental `status:` lines in CLI transcripts / body prose.
    """
    # Prefer the design-doc field table (authoritative for Hextory SDDs).
    m = _STATUS_LINE.search(text)
    if m:
        return _normalize(m.group(1))

    fm_block = _FRONTMATTER_BLOCK.match(text)
    if fm_block:
        fm = _FRONTMATTER_STATUS.search(fm_block.group(1))
        if fm:
            return _normalize(fm.group(1))
    return None


def load_manifest(path: Path) -> dict[str, SddStatus]:
    """Load config/sdd_status as JSON: {\"DES-0002\": \"Approved\", ...}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("sdd_status manifest must be a JSON object")
    return {str(k): _normalize(str(v)) for k, v in data.items()}


class LocalSddStatusReader:
    def __init__(
        self,
        *,
        manifest_path: Optional[Path] = None,
        docs_design_dir: Optional[Path] = None,
        overrides: Optional[dict[str, SddStatus]] = None,
    ) -> None:
        self._manifest_path = manifest_path
        self._docs_design_dir = docs_design_dir
        self._overrides = overrides or {}

    def get_status(self, sdd_id: str) -> SddStatus:
        if sdd_id in self._overrides:
            return self._overrides[sdd_id]

        manifest_status: Optional[SddStatus] = None
        md_status: Optional[SddStatus] = None

        try:
            if self._manifest_path is not None and self._manifest_path.is_file():
                manifest = load_manifest(self._manifest_path)
                manifest_status = manifest.get(sdd_id)
        except Exception:
            return SddStatus.ERROR

        try:
            if self._docs_design_dir is not None:
                md_status = self._read_doc_status(sdd_id)
        except Exception:
            return SddStatus.ERROR

        if manifest_status is not None and md_status is not None:
            if manifest_status != md_status:
                return SddStatus.ERROR
            return manifest_status

        if manifest_status is not None:
            return manifest_status
        if md_status is not None:
            return md_status
        return SddStatus.UNKNOWN

    def is_approved(self, sdd_id: str) -> bool:
        return self.get_status(sdd_id) == SddStatus.APPROVED

    def _read_doc_status(self, sdd_id: str) -> Optional[SddStatus]:
        assert self._docs_design_dir is not None
        num = sdd_id.replace("DES-", "").replace("des-", "")
        matches = list(self._docs_design_dir.glob(f"{num}-*.md"))
        if not matches:
            exact = self._docs_design_dir / f"{sdd_id}.md"
            if exact.is_file():
                matches = [exact]
        if not matches:
            return None
        text = matches[0].read_text(encoding="utf-8")
        return parse_markdown_status(text)
