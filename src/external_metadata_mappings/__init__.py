"""
Python API to interact with central registry and associated mappings
"""

import json
from collections import UserDict
from typing import Iterable

# import jsonschema
import requests


class Registry(UserDict):
    def __init__(self, metadata=None):
        self.data = metadata or {}

    @classmethod
    def from_path(cls, path):
        with open(path) as f:
            return cls(json.load(f))

    @classmethod
    def from_url(cls, url):
        r = requests.get(url)
        r.raise_for_status()
        return cls(r.json())

    def _validate(self):
        pass


    def iter_unique_purls(self):
        seen = set()
        for item in self.iter_all():
            if (id_ := item["id"]) not in seen:
                seen.add(id_)
                yield id_

    def iter_by_id(self, key):
        for item in self.iter_all():
            if item["id"] == key:
                yield item

    def iter_all(self):
        for item in self.data["definitions"]:
            yield item

    def iter_canonical(self):
        for item in self.iter_all():
            if not item.get("provides") or all(
                item.startswith("virtual:") for item in item.get("provides")
            ):
                yield item

    def iter_generic(self):
        for item in self.iter_all():
            if item["id"].startswith("pkg:generic/"):
                yield item

    def iter_virtual(self):
        for item in self.iter_all():
            if item["id"].startswith("virtual:"):
                yield item


class Ecosystems(UserDict):
    def __init__(self, metadata=None):
        self.data = metadata or {}

    @classmethod
    def from_path(cls, path):
        with open(path) as f:
            return cls(json.load(f))

    @classmethod
    def from_url(cls, url):
        r = requests.get(url)
        r.raise_for_status()
        return cls(r.json())

    def _validate(self):
        pass


class Mapping(UserDict):
    def __init__(self, metadata=None):
        self.data = metadata or {}

    @classmethod
    def from_path(cls, path):
        with open(path) as f:
            return cls(json.load(f))

    @classmethod
    def from_url(cls, url):
        r = requests.get(url)
        r.raise_for_status()
        return cls(r.json())

    def _validate(self):
        pass

    @property
    def name(self):
        return self.get("name")

    @property
    def description(self):
        return self.get("description")

    def iter_all(self, resolve_specs=True):
        for entry in self.data["mappings"]:
            if resolve_specs:
                entry = entry.copy()
                specs = self._resolve_specs(entry)
                entry["specs"] = self._normalize_specs(specs)
                entry.pop("specs_from", None)
            yield entry

    def iter_by_id(self, key, only_mapped=False, resolve_specs=True):
        for entry in self.iter_all(resolve_specs=False):
            if entry["id"] == key:
                if resolve_specs:
                    entry = entry.copy()
                    specs = self._resolve_specs(entry)
                    entry["specs"] = self._normalize_specs(specs)
                    entry.pop("specs_from", None)
                if only_mapped:
                    try_specs_from = False
                    if specs := entry.get("specs", {}):
                        for key in "run", "host", "build":
                            if specs.get(key):
                                yield entry
                                break
                        else:
                            try_specs_from = not resolve_specs
                    if try_specs_from and entry.get("specs_from"):
                        yield entry
                else:
                    yield entry

    def _resolve_specs(self, mapping_entry):
        if specs := mapping_entry.get("specs"):
            return specs
        elif specs_from := mapping_entry.get("specs_from"):
            return self._resolve_specs(self.data["mappings"], specs_from)
        return []

    @staticmethod
    def _normalize_specs(
        specs: str | list[str] | dict[str, str | list[str]],
    ) -> dict[str, list[str]]:
        if isinstance(specs, str):
            specs = {"build": [specs], "host": [specs], "run": [specs]}
        elif hasattr(specs, "items"):  # assert all fields are present as lists
            for key in "build", "host", "run":
                specs.setdefault(key, [])
                if isinstance(specs[key], str):
                    specs[key] = [specs[key]]
        else:  # list
            specs = {"build": specs, "host": specs, "run": specs}
        return specs

    def get_package_manager(self, name: str) -> dict:
        for manager in self.data["package_managers"]:
            if manager["name"] == name:
                return manager
        raise KeyError(f"Could not find '{name}' in {self.data["package_managers"]:r}")

    def iter_install_commands(self, package_manager, purl) -> Iterable[list[str]]:
        command = self.get_package_manager(package_manager)["install_command"]
        for specs in self.iter_specs_by_id(purl):
            yield command + specs  # TODO: Deal with `{}` placeholders

    def build_install_command(
        self, base_command: list[str], specs: list[str]
    ) -> list[str]:
        return base_command + specs
