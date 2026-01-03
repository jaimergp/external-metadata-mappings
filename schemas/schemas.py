#!/usr/bin/env python
"""
Generate a JSON schema for PEP-XXX mappings
"""

import json
from pathlib import Path
from typing import Annotated, Any, Literal

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

    id: DepURLField
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


class VersionRanges(BaseModel):
    """
    Instructions to map PEP 440 specifiers to a package manager specific constraints.
    Use an empty string if there's no equivalent. Use `{name}` and `{version}` as
    placeholders. The `and` field is not templated; it should just be the `and` operator.
    If not available, the constraints will be exploded into several specifiers (e.g.
    `name>=2,<3` would become `name>=2 name<3`).
    """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    syntax: list[NonEmptyString]
    """
    The syntax used to specify a constrained package selection (e.g. `package>=3,<4`). The
    following placeholders are supported: `{name}` (the name of the package), `ranges` (the merged
    version constraints). This value is a list of strings because some package managers may need
    several arguments to express a single package version constraint. It MUST include at least
    `{ranges}`. Some examples: `["{name}{ranges}"]`, `["{ranges}"]`, `["--spec", "{name}",
    "--version", "{ranges}"]`.
    """
    and_: str | None = Field(..., alias="and")
    """
    How to merge several constraints. If the value is a string, this will be used to join all
    the version constraints in a single string. If set to `None`, the constraints will not be
    joined, but appended as different arguments to the command.
    """
    equal: str
    """
    A range for fuzzy equality. If defined as a string, it MUST include at least the `{version}`
    placeholder. If `None`, this operator is not supported and no version constraints will be
    applied.
    """
    greater_than_equal: str | None
    """
    A range for inclusive lower bound. If defined as a string, it MUST include at least the
    `{version}` placeholder. If `None`, this operator is not supported and no version constraints
    will be applied.
    """
    greater_than: str | None
    """
    A range for exclusive lower bound. If defined as a string, it MUST include at least the
    `{version}` placeholder. If `None`, this operator is not supported and no version constraints
    will be applied.
    """
    less_than_equal: str | None
    """
    A range for inclusive upper bound. If defined as a string, it MUST include at least the
    `{version}` placeholder. If `None`, this operator is not supported and no version constraints
    will be applied.
    """
    less_than: str | None
    """
    A range for exclusive upper bound. If defined as a string, it MUST include at least the
    `{version}` placeholder. If `None`, this operator is not supported and no version constraints
    will be applied.
    """


class SpecifierSyntax(BaseModel):
    """
    Instructions to process the packager specifiers once mapped.
    """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    name_only: list[NonEmptyString]
    """
    Template used to request a package by name only, with no version constraints.
    Use the `{name}` placeholder to write the mapped name of the package. A list of
    strings is required because some package managers require several arguments to
    request a single package; e.g. `["--package", "{name}"]`.
    """
    exact_version: list[NonEmptyString] | None
    """
    Template used to request a package with a specific version (a literal, not a range).
    Since some package managers require separate arguments, this is a list of strings. The
    following placeholders are defined: `{name}` (name of the package), `{version}` (the
    exact version being requested). Some examples: `["{name}=={version}"]`,
    `["{name}", "--version={version}"]`. A value of `None` means that the package manager
    does not support version selection, only names.
    """
    version_ranges: VersionRanges | None
    """
    How to map version constraints from PEP440 style to the target package manager.
    """


class PackageManagerCommand(BaseModel):
    "Command template plus its elevation requirements."

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    command: list[NonEmptyString]
    "Command template, as expected by `subprocess.run`. Use `{}` as a placeholder for package(s)."
    requires_elevation: bool = False
    "Whether the command requires elevated permissions to run."
    multiple_specifiers: Literal["always", "name-only", "never"] = "always"
    """
    Whether the command accepts multiple specifiers at once or not. Defaults to `always`.
    Use `name-only` if the command only accepts multiple specifiers when they don't have
    version information. With `never`, only one specifier is accepted at a time, which
    will result in several single-spec commands being generated.
    """


class PackageManagerCommands(BaseModel):
    "Command templates needed to execute certain operations with this package manager"

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    install: PackageManagerCommand
    """
    Command that must be used to install the given package(s). Each argument must be provided as a
    separate string, as in `subprocess.run`. Use `"{}"` as a placeholder where the package spec(s)
    must be injected. The placeholder can only appear once in the whole list.
    """
    query: PackageManagerCommand | None
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

    name: NonEmptyString
    "Name of the package manager"
    commands: PackageManagerCommands
    "Command templates needed to execute certain operations with this package manager"
    specifier_syntax: SpecifierSyntax
    "Instructions to transform package names and version constrains for this package manager"


# endregion

# region Ecosystems


class EcosystemDetails(BaseModel):
    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )
    mapping: AnyUrl
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
    ecosystems: dict[NonEmptyString, EcosystemDetails]
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
    build: NonEmptyString | list[NonEmptyString]
    """
    Dependencies that must be present at build time and can be executed in the build machine.
    """
    host: NonEmptyString | list[NonEmptyString]
    """
    Dependencies that must be present at build time but only for linking purposes.
    Their architecture does not need to match the build machine.
    """
    run: NonEmptyString | list[NonEmptyString]
    """
    Dependencies needed at runtime in the end-user machines.
    """


class _BaseMapping(BaseModel):
    """ """

    model_config: ConfigDict = ConfigDict(
        extra="forbid",
        use_attribute_docstrings=True,
    )

    id: DepURLField
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

    specs: NonEmptyString | list[NonEmptyString] | SpecsDict
    "Package specifiers that provide the identifier at `id`."


class MappingWithSpecsFrom(_BaseMapping):
    """ """

    specs_from: DepURLField
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
    name: NonEmptyString
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
        obj = DefinitionListModel.model_json_schema()
        f.write(json.dumps(obj, indent=2))
        f.write("\n")

    with ECOSYSTEMS_FILE.open(mode="w+") as f:
        obj = Ecosystems.model_json_schema()
        f.write(json.dumps(obj, indent=2))
        f.write("\n")

    with MAPPING_SCHEMA_FILE.open(mode="w+") as f:
        obj = MappingsModel.model_json_schema()
        f.write(json.dumps(obj, indent=2))
        f.write("\n")


if __name__ == "__main__":
    main()
