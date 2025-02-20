#!/usr/bin/env python
"""
Generate a JSON schema for PEP-XXX mappings
"""

import json
from pathlib import Path
from typing import Annotated, Union

from pydantic import BaseModel, ConfigDict, Field

HERE = Path(__file__).parent
CENTRAL_REGISTRY_FILE = HERE / "central-registry.schema.json"
MAPPING_SCHEMA_FILE = HERE / "external-mapping.schema.json"


PURLField = Annotated[str, Field(min_length=1, pattern=r"^(pkg:|virtual:).*")]
NonEmptyString = Annotated[str, Field(min_length=1)]


class Definition(BaseModel):
    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    id: PURLField = ...
    "PURL-like identifier."
    description: str | None = None
    "Free-form field to add some details about the package."
    provides: PURLField | list[PURLField] | None = None
    """
    List of identifiers this entry connects to.
    Useful to annotate aliases or virtual package implementations.
    If no `provides` info is added, the entry is considered canonical.
    """
    urls: NonEmptyString | list[NonEmptyString] | dict[str, NonEmptyString] | None = (
        None
    )
    """
    Hyperlinks to web locations that provide more information about the definition.
    """

    @property
    def is_canonical(self):
        return not self.provides


class DefinitionListModel(BaseModel):
    """Canonical list of accepted pkg:generic/* and virtual:* packages"""

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    schema_: str = Field(default="", alias="$schema")
    "URL of the definition list schema in use for the document."

    schema_version: int = Field(1, ge=1, lt=2)

    definitions: list[Definition] = []
    "List of PURL definitions currently recognized."


class PackageManager(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    name: NonEmptyString = ...
    "Name of the package manager"
    install_command: list[NonEmptyString] = ...
    """
    Command that must be used to install the given package(s). Each argument must be provided as a
    separate string, as in `subprocess.run`. Use `{}` as a placeholder where the packages
    must be injected, if needed. If `{}` is not present, they will be added at the end.
    """


class SpecsDict(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    build: Union[NonEmptyString, list[NonEmptyString], None] = None
    """
    Dependencies that must be present at build time and can be executed in the build machine.
    """
    host: Union[NonEmptyString, list[NonEmptyString], None] = None
    """
    Dependencies that must be present at build time but only for linking purposes.
    Their architecture does not need to match the build machine.
    """
    run: Union[NonEmptyString, list[NonEmptyString], None] = None
    """
    Dependencies needed at runtime in the end-user machines.
    """


class Mapping(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    id: PURLField = ...
    """
    PURL-like identifier, as provided in the central registry,
    being mapped to ecosystem specific packages.
    """
    description: str | None = None
    "Free-form field for details about the mapping."
    specs: Union[NonEmptyString, list[NonEmptyString], SpecsDict] = ...
    "Package specifiers that provide the identifier at `id`."
    specs_from: PURLField | None = None
    """
    Identifier of another mapping entry with identical dependencies. Useful to avoid duplication.
    Cannot be used together with `specs`.
    """
    urls: NonEmptyString | list[NonEmptyString] | dict[str, NonEmptyString] | None = (
        None
    )
    """
    Hyperlinks to web locations that provide more information about the mapping.
    """


class MappingsModel(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    schema_: str = Field(default="", alias="$schema")
    "URL of the mappings schema in use for the document."

    schema_version: int = Field(1, ge=1, lt=2)
    description: str | None = None
    "Free-form field to add information this mapping."
    package_managers: list[PackageManager] = []
    "List of tools that can be used to install packages in this ecosystem."
    mappings: list[Mapping] = []
    "List of PURL-to-specs mappings."


def main():
    with CENTRAL_REGISTRY_FILE.open(mode="w+") as f:
        model = DefinitionListModel()
        obj = model.model_json_schema()
        obj["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        obj["$id"] = (
            f"https://github.com/python/peps/blob/main/peps/pep-0XXX/{CENTRAL_REGISTRY_FILE.name}"
        )
        f.write(json.dumps(obj, indent=2))
        f.write("\n")

    with MAPPING_SCHEMA_FILE.open(mode="w+") as f:
        model = MappingsModel()
        obj = model.model_json_schema()
        obj["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        obj["$id"] = (
            f"https://github.com/python/peps/blob/main/peps/pep-0XXX/{MAPPING_SCHEMA_FILE.name}"
        )
        f.write(json.dumps(obj, indent=2))
        f.write("\n")


if __name__ == "__main__":
    main()
