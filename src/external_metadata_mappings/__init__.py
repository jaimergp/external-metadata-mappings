"""
Python API to interact with central registry and associated mappings
"""

import json
from collections import UserDict
from pathlib import Path
from typing import Any, Iterable

import requests
from jsonschema import Draft202012Validator, validators

HERE = Path(__file__).parent
SCHEMAS_DIR = HERE.parent.parent / "schemas"


class _Validated:
    default_schema: Path
    _validator_cls = validators.create(
        meta_schema=Draft202012Validator.META_SCHEMA,
        validators=dict(Draft202012Validator.VALIDATORS),
    )

    def _validator_inst(self, path_or_url: str | None = None):
        if path_or_url is None:
            schema = json.loads(self.default_schema.read_text())
        elif path_or_url.startswith(("http://", "https://")):
            r = requests.get(path_or_url)
            r.raise_for_status()
            schema = r.json()
        else:
            path = Path(path_or_url)
            if not path.is_absolute() and (data_path := getattr(self, "_path", None)):
                # TODO: Stop supporting relative paths and remove '._path' from _FromPathOrUrl
                data_path = Path(data_path).parent
                schema = json.loads((data_path / path).read_text())
            else:
                schema = json.loads(Path(path_or_url).read_text())
        return self._validator_cls(schema)

    def validate(self):
        schema_definition = self.data.get("$schema") or None
        errors = list(self._validator_inst(schema_definition).iter_errors(self.data))
        if errors:
            msg = "\n".join(errors)
            raise ValueError(f"Validation error: {msg}")


class _FromPathOrUrl:
    @classmethod
    def from_path(cls, path):
        with open(path) as f:
            inst = cls(json.load(f))
        inst._path = path
        return inst

    @classmethod
    def from_url(cls, url):
        r = requests.get(url)
        r.raise_for_status()
        return cls(r.json())


class Registry(UserDict, _Validated, _FromPathOrUrl):
    default_schema: Path = SCHEMAS_DIR / "central-registry.schema.json"

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
                item.startswith("dep:virtual/") for item in item.get("provides")
            ):
                yield item

    def iter_generic(self):
        for item in self.iter_all():
            if item["id"].startswith("dep:generic/"):
                yield item

    def iter_virtual(self):
        for item in self.iter_all():
            if item["id"].startswith("dep:virtual/"):
                yield item


class Ecosystems(UserDict, _Validated, _FromPathOrUrl):
    default_schema: Path = SCHEMAS_DIR / "known-ecosystems.schema.json"

    def iter_all(self) -> Iterable[dict]:
        for eco in self.data.get("ecosystems", ()):
            yield eco


class Mapping(UserDict, _Validated, _FromPathOrUrl):
    default_schema: Path = SCHEMAS_DIR / "external-mapping.schema.json"

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
            return self._resolve_specs(specs_from)
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
        raise KeyError(f"Could not find '{name}' in {self.data['package_managers']:r}")

    def iter_install_commands(self, package_manager, purl) -> Iterable[list[str]]:
        mgr = self.get_package_manager(package_manager)
        for specs in self.iter_specs_by_id(purl):
            yield self.build_install_command(mgr, specs)

    def build_install_command(
        self,
        package_manager: dict[str, Any],
        specs: list[str],
    ) -> list[str]:
        # TODO: Deal with `{}` placeholders
        cmd = []
        if package_manager.get("requires_elevation", False):
            # TODO: Add a system to infer type of elevation required (sudo vs Windows AUC)
            cmd.append("sudo")
        cmd.extend(package_manager["install_command"])
        cmd.extend(specs)
        return cmd
