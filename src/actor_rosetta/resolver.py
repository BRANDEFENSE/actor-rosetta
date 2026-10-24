"""Module-level API on the bundled data. The data file is read once, from the package, never from the network."""
from __future__ import annotations

import json
from importlib import resources
from typing import List, Optional, Tuple

from .model import Dataset, Explanation, Group

_DATASET: Optional[Dataset] = None


def load(path: Optional[str] = None) -> Dataset:
    """Load the bundled data, or a given actors.json. The bundled data is cached."""
    global _DATASET
    if path is None and _DATASET is not None:
        return _DATASET
    if path is None:
        text = resources.files("actor_rosetta").joinpath("data/actors.json").read_text(encoding="utf-8")
    else:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    raw = json.loads(text)
    ds = Dataset((Group.from_dict(g) for g in raw["groups"]), raw.get("meta"))
    if path is None:
        _DATASET = ds
    return ds


def resolve(name: str) -> Optional[Group]:
    """The group that publishes this name, or None."""
    return load().resolve(name)


def search(name: str, limit: int = 5) -> List[Tuple[Group, float, str]]:
    """Fuzzy search: [(group, score, matched_name)]."""
    return load().search(name, limit=limit)


def explain(name: str) -> Explanation:
    """What the data says about this string."""
    return load().explain(name)


def all_groups() -> List[Group]:
    return list(load().groups)


def data_version() -> str:
    return load().version
