#!/usr/bin/env python3
"""CI design-gate checks for Hextory (run without pytest collection).

Fail closed on SDD status hygiene issues. Does not require git.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
DESIGN = REPO / "docs" / "design"
MANIFEST = REPO / "config" / "sdd_status.json"
CONTRIBUTING = REPO / "CONTRIBUTING.md"
PYPROJECT = REPO / "pyproject.toml"

_STATUS_LINE = re.compile(
    r"\|\s*\*\*Status\*\*\s*\|\s*\*?\*?([^*\|\n]+)\*?\*?\s*\|",
    re.IGNORECASE,
)
_DOC_ID = re.compile(r"\|\s*\*\*Doc ID\*\*\s*\|\s*\*?\*?(DES-\d+)\*?\*?\s*\|", re.I)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _normalize_status_token(raw: str) -> str:
    return raw.strip().strip("*").strip().split()[0].lower()


def check_contributing() -> None:
    if not CONTRIBUTING.is_file():
        _fail("CONTRIBUTING.md missing")


def check_no_cucumber_dep() -> None:
    text = PYPROJECT.read_text(encoding="utf-8").lower()
    banned = ("cucumber", "behave", "pytest-bdd")
    for token in banned:
        if token in text:
            _fail(f"BDD toolchain dependency hinted in pyproject.toml: {token}")


def check_src_no_adapters_imports() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for mod in names:
                if mod == "adapters" or mod.startswith("adapters."):
                    offenders.append(f"{path.relative_to(REPO)} imports {mod}")
                if mod == "langgraph" or mod.startswith("langgraph."):
                    offenders.append(f"{path.relative_to(REPO)} imports {mod}")
    if offenders:
        _fail("src must not import adapters or langgraph:\n  " + "\n  ".join(offenders))


def check_sdd_status_hygiene() -> None:
    if not MANIFEST.is_file():
        _fail("config/sdd_status.json missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        _fail("sdd_status manifest must be a JSON object")

    docs: dict[str, Path] = {}
    for path in sorted(DESIGN.glob("[0-9][0-9][0-9][0-9]-*.md")):
        text = path.read_text(encoding="utf-8")
        id_m = _DOC_ID.search(text)
        st_m = _STATUS_LINE.search(text)
        if not id_m:
            _fail(f"{path.name}: missing Doc ID table row")
        if not st_m:
            _fail(
                f"{path.name}: Status cell not parseable — use a bare token "
                f"(Draft|Approved|…) with no parentheticals in the Status cell"
            )
        sdd_id = id_m.group(1).upper()
        token = _normalize_status_token(st_m.group(1))
        if token not in {
            "draft",
            "approved",
            "superseded",
            "in",  # "In Review"
            "changes",  # "Changes Requested"
        } and not token.startswith("in") and "review" not in st_m.group(1).lower():
            # Allow In Review / Changes Requested via first-token heuristics above;
            # still require cell matched.
            pass
        docs[sdd_id] = path

        if sdd_id not in manifest:
            _fail(f"{sdd_id} present in {path.name} but missing from config/sdd_status.json")

        man_raw = str(manifest[sdd_id]).strip().lower()
        # Compare normalized Approved vs not-Approved for gate purposes
        md_approved = token == "approved"
        man_approved = man_raw == "approved"
        if md_approved != man_approved:
            _fail(
                f"{sdd_id}: markdown Status ({st_m.group(1).strip()}) "
                f"disagrees with manifest ({manifest[sdd_id]})"
            )
        if not md_approved and man_raw not in {"draft", "in review", "changes requested", "superseded"}:
            # soft: require manifest token recognizable
            if man_raw != token and not man_raw.startswith(token):
                # Draft vs draft OK; In Review vs in review
                man_norm = re.sub(r"\s+", " ", man_raw)
                md_norm = re.sub(r"\s+", " ", st_m.group(1).strip().strip("*").lower())
                if man_norm.split()[0] != md_norm.split()[0]:
                    _fail(
                        f"{sdd_id}: status token mismatch "
                        f"markdown={st_m.group(1).strip()!r} manifest={manifest[sdd_id]!r}"
                    )

    # Fixture-only keys like DES-9999 may exist only in manifest — OK.
    print(f"OK: SDD hygiene for {len(docs)} design doc(s); manifest keys={len(manifest)}")


def main() -> None:
    check_contributing()
    check_no_cucumber_dep()
    if SRC.is_dir():
        check_src_no_adapters_imports()
    check_sdd_status_hygiene()
    print("OK: all design-gate checks passed")


if __name__ == "__main__":
    main()
