from pathlib import Path

import pytest

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


@pytest.mark.parametrize("mapping", MAPPINGS)
def test_mappings(mapping):
    Mapping.from_path(mapping).validate()
