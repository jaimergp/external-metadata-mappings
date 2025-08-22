#!/usr/bin/env python
"""
Generate a JSON schema for PEP-XXX mappings
"""

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, AnyUrl

HERE = Path(__file__).parent
CENTRAL_REGISTRY_FILE = HERE / "central-registry.schema.json"
ECOSYSTEMS_FILE = HERE / "known-ecosystems.schema.json"
MAPPING_SCHEMA_FILE = HERE / "external-mapping.schema.json"


DepURLField = Annotated[str, Field(min_length=5, pattern=r"^dep:.+$")]
NonEmptyString = Annotated[str, Field(min_length=1)]


# region Definitions


class Definition(BaseModel):
    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    id: DepURLField = ...
    "PURL-like identifier."
    description: str | None = None
    "Free-form field to add some details about the package. Allows Markdown."
    provides: DepURLField | list[DepURLField] | None = None
    """
    List of identifiers this entry connects to.
    Useful to annotate aliases or virtual package implementations.
    If no `provides` info is added, the entry is considered canonical.
    MUST NOT be used with `dep:virtual/` URLs.
    """
    urls: AnyUrl | list[AnyUrl] | dict[NonEmptyString, AnyUrl] | None = None
    """
    Hyperlinks to web locations that provide more information about the definition.
    """

    @property
    def is_canonical(self):
        return not self.provides


class DefinitionListModel(BaseModel):
    """Canonical list of accepted `dep:(virtual|generic)/` packages"""

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": (
                "https://github.com/python/peps/blob/main/peps/pep-0XXX/"
                f"{CENTRAL_REGISTRY_FILE.name}"
            ),
        },
    )

    schema_: str = Field(default="", alias="$schema")
    "URL of the definition list schema in use for the document."

    schema_version: int = Field(1, ge=1, lt=2)

    definitions: list[Definition]
    "List of PURL definitions currently recognized."


class VersionOperators(BaseModel):
    """
    Mapping of a PEP440 operator to a package manager specific operator.
    Use an empty string if there's no equivalent.
    """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    and_: str = Field(",", alias="and")
    arbitrary: str = "==="
    compatible: str = "~="
    equal: str = "=="
    greater_than_equal: str = ">="
    greater_than: str = ">"
    less_than_equal: str = "<="
    less_than: str = "<"
    not_equal: str = "!="
    separator: str = ""


class PackageManagerCommand(BaseModel):
    "Command template plus its elevation requirements."

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    command: list[NonEmptyString] = []
    "Command template, as expected by `subprocess.run`. Use `{}` as a placeholder for package(s)."
    requires_elevation: bool = False
    "Whether the command requires elevated permissions to run."


class PackageManagerCommands(BaseModel):
    "Command templates needed to execute certain operations with this package manager"

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    install: PackageManagerCommand = ...
    """
    Command that must be used to install the given package(s). The tool must accept several
    packages in the same command. Each argument must be provided as a separate string, as
    in `subprocess.run`. Use `{}` as a placeholder where the package spec(s) must be injected.
    The placeholder can only appear once in the whole list and will be replaced once per package.
    For example, given the names `foo` and `bar`, `["pkg", "install", "{}"]` would become
    `pkg install foo bar`, and `["pkg", "install", "--spec={}"]` would become
    `pkg install --spec=foo --spec=bar`.
    """
    query: PackageManagerCommand | None = None
    """
    Command to check whether a package is installed. The tool must only accept one package at a
    time. Each argument must be provided as a separate string, as in `subprocess.run`. The `{}`
    placeholder will be replaced by the single package. An empty list means no query command is
    available for this package manager.
    """


class PackageManager(BaseModel):
    """
    Details of a particular package manager for this ecosystem.
    """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    name: NonEmptyString = ...
    "Name of the package manager"
    commands: PackageManagerCommands = ...
    "Command templates needed to execute certain operations with this package manager"
    version_operators: VersionOperators = VersionOperators()
    """
    Mapping of PEP440 version comparison operators to the syntax used in this package manager.
    If set to an empty dictionary, it means that the package manager (or ecosystem)
    doesn't support the notion of requesting particular package versions.
    """


# endregion

# region Ecosystems


class EcosystemDetails(BaseModel):
    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    mapping: AnyUrl = ...
    "URL to the mapping for this ecosystem / package manager"


class Ecosystems(BaseModel):
    """
    A registry of known ecosystems and their canonical locations for their mappings.
    """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": (
                "https://github.com/python/peps/blob/main/peps/pep-0XXX/"
                f"{ECOSYSTEMS_FILE.name}"
            ),
        },
    )
    schema_: str = Field(default="", alias="$schema")
    "URL of the definition list schema in use for the document."

    schema_version: int = Field(1, ge=1, lt=2)
    ecosystems: dict[NonEmptyString, EcosystemDetails] = {}
    """
    Ecosystems names and their corresponding details
    """


# endregion

# region Mapping


class SpecsDict(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    build: NonEmptyString | list[NonEmptyString] | None = None
    """
    Dependencies that must be present at build time and can be executed in the build machine.
    """
    host: NonEmptyString | list[NonEmptyString] | None = None
    """
    Dependencies that must be present at build time but only for linking purposes.
    Their architecture does not need to match the build machine.
    """
    run: NonEmptyString | list[NonEmptyString] | None = None
    """
    Dependencies needed at runtime in the end-user machines.
    """


class _BaseMapping(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    id: DepURLField = ...
    """
    PURL-like identifier, as provided in the central registry,
    being mapped to ecosystem specific packages.
    """
    description: str | None = None
    "Free-form field for details about the mapping. Allows Markdown."
    urls: AnyUrl | list[AnyUrl] | dict[NonEmptyString, AnyUrl] | None = None
    """
    Hyperlinks to web locations that provide more information about the mapping.
    """
    extra_metadata: dict[NonEmptyString, Any] | None = None
    """
    Free-form key-value store for arbitrary metadata.
    """


class MappingWithSpecs(_BaseMapping):
    """ """

    specs: NonEmptyString | list[NonEmptyString] | SpecsDict = ...
    "Package specifiers that provide the identifier at `id`."


class MappingWithSpecsFrom(_BaseMapping):
    """ """

    specs_from: DepURLField = ...
    """
    Identifier of another mapping entry with identical dependencies. Useful to avoid duplication.
    Cannot be used together with `specs`.
    """


class MappingsModel(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": (
                "https://github.com/python/peps/blob/main/peps/pep-0XXX/"
                f"{CENTRAL_REGISTRY_FILE.name}"
            ),
        },
    )

    schema_: str = Field(default="", alias="$schema")
    "URL of the mappings schema in use for the document."
    schema_version: int = Field(1, ge=1, lt=2)
    name: NonEmptyString = ...
    "Name of the schema"
    description: str | None = None
    "Free-form field to add information this mapping. Allows Markdown."
    package_managers: list[PackageManager]
    "List of tools that can be used to install packages in this ecosystem."
    mappings: list[MappingWithSpecs | MappingWithSpecsFrom]
    "List of PURL-to-specs mappings."


# endregion


def main():
    with CENTRAL_REGISTRY_FILE.open(mode="w+") as f:
        model = DefinitionListModel(
            definitions=[],
        )
        obj = model.model_json_schema()
        f.write(json.dumps(obj, indent=2))
        f.write("\n")

    with ECOSYSTEMS_FILE.open(mode="w+") as f:
        model = Ecosystems()
        obj = model.model_json_schema()
        f.write(json.dumps(obj, indent=2))
        f.write("\n")

    with MAPPING_SCHEMA_FILE.open(mode="w+") as f:
        model = MappingsModel(
            name="doesnotmatter",
            package_managers=[],
            mappings=[],
        )
        obj = model.model_json_schema()
        f.write(json.dumps(obj, indent=2))
        f.write("\n")


if __name__ == "__main__":
    main()
