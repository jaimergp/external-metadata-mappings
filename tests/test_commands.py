from pathlib import Path

import pytest

from external_metadata_mappings import Mapping

HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = ROOT / "data"


@pytest.fixture
def mapping_instance():
    # Create a minimal Mapping instance for testing the method
    # The actual data doesn't matter much for _add_version_to_spec
    return Mapping({"mappings": [], "package_managers": []})


# Missing 'version_operators' key -> Use default PEP440 operators
pm_missing_key_uses_default = {"name": "no_version_missing"}

# Empty 'version_operators' dict -> NO version support
pm_empty_dict_disables_version_support = {
    "name": "default_ops_empty_dict",
    "version_operators": {},
}

# Custom separator, default operators
pm_custom_separator_defaults = {
    "name": "custom_sep_defaults",
    "version_operators": {"separator": "@"},  # Defaults used for operators, 'and'
}

# Custom operators, default for others
pm_custom_operators_defaults = {
    "name": "custom_ops_defaults",
    "version_operators": {
        "equal": "=",  # Custom mapping for '=='
        # Other operators will use defaults from Mapping.default_operator_mapping
        "separator": "-",  # Custom separator
        "and": " ",  # Custom 'and'
    },
}

# Unsupported operator ('=='), default for others
pm_no_equals_defaults = {
    "name": "no_equals_defaults",
    "version_operators": {
        "equal": None,  # Explicitly unsupported/ignored operator
        # Other operators will use defaults
        "separator": ":",  # Custom separator
        "and": ",",  # Default 'and' (which is ',')
    },
}


@pytest.mark.parametrize(
    "name, version, pm_config, expected",
    [
        # --- No Version Support (Missing key) ---
        (
            "pkg-no-ver-a",
            "==1.0",
            pm_empty_dict_disables_version_support,
            "pkg-no-ver-a",
        ),
        (
            "pkg-no-ver-b",
            ">=1.0,<2.0",
            pm_empty_dict_disables_version_support,
            "pkg-no-ver-b",
        ),
        ("pkg-no-ver-c", None, pm_empty_dict_disables_version_support, "pkg-no-ver-c"),
        ("pkg-no-ver-d", "", pm_empty_dict_disables_version_support, "pkg-no-ver-d"),
        # --- Default Operators (Empty dict) ---
        ("pkg-def-a", None, pm_missing_key_uses_default, "pkg-def-a"),
        ("pkg-def-b", "", pm_missing_key_uses_default, "pkg-def-b"),
        (
            "pkg-def-c",
            "==1.0",
            pm_missing_key_uses_default,
            "pkg-def-c==1.0",
        ),  # Default separator is ""
        ("pkg-def-d", ">=2.5", pm_missing_key_uses_default, "pkg-def-d>=2.5"),
        ("pkg-def-e", "<3.0", pm_missing_key_uses_default, "pkg-def-e<3.0"),
        ("pkg-def-f", "!=4.1", pm_missing_key_uses_default, "pkg-def-f!=4.1"),
        ("pkg-def-g", "~=1.2.3", pm_missing_key_uses_default, "pkg-def-g~=1.2.3"),
        (
            "pkg-def-h",
            ">=1.0,<2.0",
            pm_missing_key_uses_default,
            "pkg-def-h>=1.0,<2.0",
        ),  # Default 'and' is ','
        (
            "pkg-def-i",
            ">1.0,!=1.5,<2.0",
            pm_missing_key_uses_default,
            "pkg-def-i>1.0,!=1.5,<2.0",
        ),
        # --- Custom Separator (Defaults for ops) ---
        ("pkg-sep-a", "==1.0", pm_custom_separator_defaults, "pkg-sep-a@==1.0"),
        (
            "pkg-sep-b",
            ">=1.0,<2.0",
            pm_custom_separator_defaults,
            "pkg-sep-b@>=1.0,<2.0",
        ),
        # --- Custom Operators (Defaults for others) ---
        ("pkg-custom-a", "==1.0", pm_custom_operators_defaults, "pkg-custom-a-=1.0"),
        (
            "pkg-custom-b",
            "<2.0",
            pm_custom_operators_defaults,
            "pkg-custom-b-<2.0",
        ),  # Corrected expected output
        (
            "pkg-custom-c",
            ">=3.0,==3.5",
            pm_custom_operators_defaults,
            "pkg-custom-c->=3.0 =3.5",
        ),  # Note the ' ' as 'and'
        (
            "pkg-custom-d",
            "~=4.0",
            pm_custom_operators_defaults,
            "pkg-custom-d-~=4.0",
        ),  # Uses default ~=
        # --- Unsupported Operator (Defaults for others) ---
        (
            "pkg-noeq-a",
            "==1.0",
            pm_no_equals_defaults,
            "pkg-noeq-a",
        ),  # == maps to None so version is dropped
        (
            "pkg-noeq-b",
            ">=2.0,==2.5",
            pm_no_equals_defaults,
            "pkg-noeq-b:>=2.0",
        ),  # >=2.0 is kept (default op), ==2.5 is dropped
        (
            "pkg-noeq-c",
            "==3.0,==3.1",
            pm_no_equals_defaults,
            "pkg-noeq-c",
        ),  # Both dropped
        (
            "pkg-noeq-d",
            "<4.0",
            pm_no_equals_defaults,
            "pkg-noeq-d:<4.0",
        ),  # Uses default <
    ],
)
def test_add_version_to_spec(mapping_instance, name, version, pm_config, expected):
    """
    Tests the _add_version_to_spec method with various inputs.
    """
    result = mapping_instance._add_version_to_spec(name, version, pm_config)
    assert result == expected


@pytest.mark.parametrize(
    "dep_url,expected",
    (
        ("dep:generic/llvm@20", "llvm==20"),
        ("dep:generic/llvm@>20", "llvm>20"),
        ("dep:generic/llvm@20,>=21", "llvm==20,>=21"),
    ),
)
def test_build_command(dep_url, expected):
    mapping = Mapping.from_path(DATA / "conda-forge.mapping.json")
    for command in mapping.iter_install_commands("conda", dep_url):
        assert expected in command
