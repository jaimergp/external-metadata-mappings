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
    "purl",
    list(
        dict.fromkeys(
            [entry["id"] for entry in Registry.from_path(REGISTRY_PATH).iter_all()]
        )
    ),
)
def test_registry_purls_are_parsable(purl):
    if purl.startswith("dep:"):
        pytest.skip("Virtual PURLs use a different schema and aren't parsable (yet?)")
    PackageURL.from_string(purl)
