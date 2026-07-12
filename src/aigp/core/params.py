"""Versioned parameter sets.

Every tunable in the system lives in one nested JSON document. ParamSet is an
immutable view over it with:

- dot-key access:            params.get("planner.approach.speed_far_mps")
- flatten()/unflatten():     dot-key <-> nested dict, for optimizers
- patch(overrides):          returns a NEW ParamSet with dot-key overrides
- hash / hash8:              sha256 of canonical JSON, identifies the set

The learning loop snapshots the exact JSON per flight, so every result row in
the DB points at a reproducible parameter set.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


class ParamSet:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = copy.deepcopy(data)

    # -- construction ---------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "ParamSet":
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.canonical_json())

    # -- access ---------------------------------------------------------------

    def get(self, dotkey: str, default: Any = KeyError) -> Any:
        node: Any = self._data
        for part in dotkey.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is KeyError:
                    raise KeyError(dotkey)
                return default
            node = node[part]
        return node

    def __getitem__(self, dotkey: str) -> Any:
        return self.get(dotkey)

    def section(self, dotkey: str) -> dict[str, Any]:
        """Return a deep copy of a nested section as a plain dict."""
        val = self.get(dotkey)
        if not isinstance(val, dict):
            raise TypeError(f"{dotkey} is not a section")
        return copy.deepcopy(val)

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    # -- flatten / patch --------------------------------------------------------

    def flatten(self) -> dict[str, Any]:
        flat: dict[str, Any] = {}

        def walk(node: dict[str, Any], prefix: str) -> None:
            for k, v in node.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    walk(v, key)
                else:
                    flat[key] = v

        walk(self._data, "")
        return flat

    @classmethod
    def unflatten(cls, flat: dict[str, Any]) -> "ParamSet":
        data: dict[str, Any] = {}
        for dotkey, v in flat.items():
            node = data
            parts = dotkey.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = v
        return cls(data)

    def patch(self, overrides: dict[str, Any]) -> "ParamSet":
        """Return a new ParamSet with dot-key overrides applied."""
        data = copy.deepcopy(self._data)
        for dotkey, v in overrides.items():
            node = data
            parts = dotkey.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = v
        return ParamSet(data)

    # -- identity ---------------------------------------------------------------

    def canonical_json(self) -> str:
        return json.dumps(self._data, sort_keys=True, indent=2, ensure_ascii=False)

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def hash8(self) -> str:
        return self.hash[:8]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ParamSet) and other._data == self._data

    def __repr__(self) -> str:
        return f"ParamSet({self.hash8})"
