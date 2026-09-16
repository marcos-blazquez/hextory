"""Factory departments (nodes): assembly, quality, packaging."""

from src.departments.assembly import NODE_ID as ASSEMBLY_NODE
from src.departments.assembly import run_assembly
from src.departments.packaging import NODE_ID as PACKAGING_NODE
from src.departments.packaging import PackagingInvariantError, run_packaging
from src.departments.quality import NODE_ID as QUALITY_NODE
from src.departments.quality import run_quality

__all__ = [
    "ASSEMBLY_NODE",
    "PACKAGING_NODE",
    "PackagingInvariantError",
    "QUALITY_NODE",
    "run_assembly",
    "run_packaging",
    "run_quality",
]
