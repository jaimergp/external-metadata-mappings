from pathlib import Path

import pytest
from packageurl import PackageURL

from external_metadata_mappings import Ecosystems, Mapping, Registry


HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = ROOT / "data"


def datafile(filename: str) -> Path:
    return DATA / filename


REGISTRY_PATH = datafile("registry.json")
ECOSYSTEMS_PATH = datafile("known-ecosystems.json")
MAPPINGS = sorted(DATA.glob("*.mapping.json"))


def test_registry():
    Registry.from_path(REGISTRY_PATH).validate()


def test_ecosystems():
    Ecosystems.from_path(ECOSYSTEMS_PATH).validate()


@pytest.mark.parametrize("mapping", [pytest.param(m, id=m.name) for m in MAPPINGS])
def test_mappings(mapping):
    Mapping.from_path(mapping).validate()


@pytest.mark.parametrize(
    "dep_url",
    list(
        dict.fromkeys(
            [entry["id"] for entry in Registry.from_path(REGISTRY_PATH).iter_all()]
        )
    ),
)
def test_registry_dep_urls_are_parsable(dep_url):
    if dep_url.startswith("dep:"):
        pytest.skip("dep URLs use a different schema and aren't parsable (yet?)")
    PackageURL.from_string(dep_url)


def test_resolve_virtual_gcc():
    mapping = Mapping.from_path(DATA / "fedora.mapping.json")
    registry = Registry.from_path(DATA / "registry.json")
    arrow = next(
        iter(
            mapping.iter_by_id(
                "dep:virtual/compiler/c", resolve_alias_with_registry=registry
            )
        )
    )
    assert arrow["specs"]["build"] == ["gcc"]


def test_resolve_alias_arrow():
    mapping = Mapping.from_path(DATA / "fedora.mapping.json")
    registry = Registry.from_path(DATA / "registry.json")
    arrow = next(
        iter(
            mapping.iter_by_id(
                "dep:github/apache/arrow", resolve_alias_with_registry=registry
            )
        )
    )
    assert arrow["specs"]["run"] == ["libarrow", "libarrow-dataset-libs"]
