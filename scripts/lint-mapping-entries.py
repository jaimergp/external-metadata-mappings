import sys
import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "registry.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text())
ALL_IDs = {item["id"] for item in REGISTRY["definitions"]}
CANONICAL_IDs = {
    # Canonical IDs are those that do not implement any pkg: PURL (pkg:virtual/ are ok)
    item["id"]
    for item in REGISTRY["definitions"]
    if not item.get("provides")
    or all(item.startswith("dep:virtual/") for item in item.get("provides"))
}

exit_code = 0

for path in sorted(sys.argv[1:]):
    with open(path) as f:
        data = json.load(f)
        mapping_ids = {item["id"] for item in data["mappings"]}
        specs_from_ids = {
            item["specs_from"] for item in data["mappings"] if item.get("specs_from")
        }
        if missing := CANONICAL_IDs.difference(mapping_ids):
            print(f"Some canonical IDs are missing in mapping '{path}':")
            for item in sorted(missing):
                print("-", item)
            exit_code = 1
        if extra := mapping_ids.difference(CANONICAL_IDs):
            print(f"Some IDs in mapping '{path}' are not recognized as canonical:")
            for item in sorted(extra):
                print("-", item)
            exit_code = 1
        if missing_from := specs_from_ids.difference(mapping_ids):
            print(
                f"Some IDs used as 'specs_from' values in '{path}' are not defined in this mapping:"
            )
            for item in sorted(missing_from):
                print("-", item)
            exit_code = 1
        for package_manager in data.get("package_managers", ()):
            for command_name, command_details in package_manager.get(
                "commands", {}
            ).items():
                if command_args := command_details.get("command"):
                    if not any("{}" in arg for arg in command_args):
                        print(
                            f"{path}: package_managers.{package_manager['name']}.commands.{command_name}.command",
                            "is missing the placeholder '{}'",
                        )
                        exit_code = 1
            if specifier_syntax := package_manager.get("specifier_syntax", {}):
                if "{name}" not in specifier_syntax["name_only"]:
                    print(
                        f"{path}: package_managers.{package_manager['name']}.specifier_syntax.name_only",
                        "does not include the '{name}' placeholder.",
                    )
                    exit_code = 1
                exact_version = specifier_syntax["exact_version"]
                if exact_version and not any("{name}" in arg for arg in exact_version):
                    print(
                        f"{path}: package_managers.{package_manager['name']}.specifier_syntax.exact_version",
                        "does not have any fields with the '{name}' placeholder.",
                    )
                    exit_code = 1
                if exact_version and not any(
                    "{version}" in arg for arg in exact_version or ()
                ):
                    print(
                        f"{path}: package_managers.{package_manager['name']}.specifier_syntax.exact_version",
                        "does not have any fields with the '{version}' placeholder.",
                    )
                    exit_code = 1
                if version_ranges := specifier_syntax.get("version_ranges"):
                    if not any("{ranges}" in arg for arg in version_ranges["syntax"]):
                        print(
                            f"{path}: package_managers.{package_manager['name']}.specifier_syntax.version_ranges.syntax",
                            "does not have any fields with the '{ranges}' placeholder.",
                        )
                        exit_code = 1
                    for opkey in (
                        "equal",
                        "greater_than",
                        "greater_than_equal",
                        "less_than",
                        "less_than_equal",
                        "not_equal",
                    ):
                        op = version_ranges[opkey]
                        if op is None:
                            continue
                        if "{version}" not in op:
                            print(
                                f"{path}: package_managers.{package_manager['name']}.specifier_syntax.version_ranges.{opkey}",
                                "does not have a '{version}' placeholder.",
                            )
                            exit_code = 1


sys.exit(exit_code)
