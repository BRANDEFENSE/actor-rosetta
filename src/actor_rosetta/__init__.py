"""actor-rosetta: resolve a threat-actor name to the group, its verified names and sources."""
from __future__ import annotations

from .fold import fold
from .model import Dataset, Explanation, Group, NameConflictError
from .resolver import (
    all_groups,
    data_version,
    explain,
    load,
    resolve,
    search,
)

__version__ = "0.1.0"

__all__ = [
    "Dataset",
    "Explanation",
    "Group",
    "NameConflictError",
    "__version__",
    "all_groups",
    "data_version",
    "explain",
    "fold",
    "load",
    "resolve",
    "search",
]
