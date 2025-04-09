# Registry and mappings for external metadata

This repository prototypes schemas for PEP-725-adjacent PURL registry and downstream mappings could look like.

A Streamlit app to navigate the examples is published at https://external-metadata-mappings.streamlit.app.

## Overview of contents

There are three schemas, both built from `schemas/schemas.py` and stored as JSON schemas in `schemas/`:

- `central-registry.schema.json`: Defines the list of canonical identifiers, and its most common "providers". A concrete example of how this schema applies to a real life scenario is given in `data/registry.json`.
- `known-ecosystems.schema.json`: Defines the list of ecosystems that are known to provide a mapping (located at the given URL), as well as their package manager names. An example is given in `data/known-ecosystems.json`.
- `external-mapping.schema.json`: Defines how the mappings that provide package names for canonical identifiers would look like. These are designed to be hosted by the target ecosystems (e.g. Linux distributions, Homebrew, Winget, conda-forge, etc). Concrete examples can be found under the `data/*.mapping.json` files.

A Python API to process the `data/` examples can be found under `src/`.

The Streamlit app can be found in the `app.py` file.

The `scripts/` folder hosts custom linting logic used in the `pre-commit` configuration file.

## Design decisions

- A single registry implementation is assumed to exist.
- Many mappings can exist, each maintained by different communities if necessary. They are meant to refer to the single registry as the source of canonical identifiers that can be mapped to ecosystem-native package specifiers.
- A canonical identifier is defined in a registry by an `definitions` entry that does not provide any other `dep:` identifier. But it only provides one or more `dep:virtual/` identifiers, it is still considered canonical.
- Mappings are only required to provide mapped values for canonical identifiers. They can still provide for non-canonical ones, but it's not necessary. If the ecosystem has not packaged the project behind a canonical identifier, then `specs` must be an empty list.

## Open questions

- Should an ecosystem map `dep:virtual/` packages, their immediate concrete `dep:` providers, or both?

## Contributing

- Run test suite with `pixi run test` and choose the adequate environment for a Python version
- Run `pixi run pre-commit run --all-files` before submitting a PR.
- Regenerate the schemas with `pixi run schemas` if necessary.
- The Streamlit app can be run locally with `pixi run app`.
