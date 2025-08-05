#!/usr/bin/env python
"""
Generate a JSON schema for PEP-XXX mappings
"""

import json
from pathlib import Path
from typing import Annotated, Literal

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
    install_command: list[NonEmptyString] = ...
    """
    Command that must be used to install the given package(s). Each argument must be provided as a
    separate string, as in `subprocess.run`. Use `{}` as a placeholder where the package specs
    must be injected, if needed. If `{}` is not present, they will be added at the end.
    """
    query_command: list[NonEmptyString] = ...
    """
    Command to check whether a package is installed. Each argument must be provided as a
    separate string, as in `subprocess.run`. The `{}` placeholder will be replaced by
    a single package spec, if needed. Otherwise, the package specifier will be added at the end.
    An empty list means no query command is available for this package manager.
    """
    requires_elevation: bool | Literal["install", "query"] = False
    """
    Whether the install and query commands require elevated permissions to run. Use `True`
    to require on all commands, `False` for none. `install` and `query` can be used individually
    to only require elevation on one of them.
    """
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
