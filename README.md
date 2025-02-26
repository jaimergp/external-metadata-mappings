# Registry and mappings for external metadata

This repository prototypes schemas for PEP-725-adjacent PURL registry and downstream mappings could look like.

A Streamlit app to navigate the examples is published at https://external-metadata-mappings.streamlit.app.

## Overview of contents

There are two schemas, both built from `schemas/schema.py` and stored as JSON schemas in `schemas/`:

- `central-registry.schema.json`: Defines the list of canonical identifiers, and its most common "providers". A concrete example of how this schema applies to a real life scenario is given in `data/registry.json`.
- `external-mapping.schema.json`: Defines how the mappings that provide package names for canonical identifiers would look like. These are designed to be hosted by the target ecosystems (e.g. Linux distributions, Homebrew, Winget, conda-forge, etc). Concrete examples can be found under the `data/*.mapping.json` files.

The Streamlit app can be found in the `app.py` file.

The `scripts/` folder hosts custom linting logic used in the `pre-commit` configuration file.

## Design decisions

- A single registry implementation is assumed to exist.
- Many mappings can exist, each maintained by different communities if necessary. They are meant to refer to the single registry as the source of canonical identifiers that can be mapped to ecosystem-native package specifiers.
- A canonical identifier is defined in a registry by an `definitions` entry that does not provide any other `pkg:` identifier. If it only provides one or more `virtual:` identifiers, it is still considered canonical.
- Mappings are only required to provide mapped values for canonical identifiers. They can still provide for non-canonical ones, but it's not necessary. If the ecosystem has not packaged the project behind a canonical identifier, then `specs` must be an empty list.
