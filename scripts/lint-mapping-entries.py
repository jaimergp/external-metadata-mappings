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

for path in sys.argv[1:]:
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
                            f"{path}: {package_manager['name']} command {command_name}",
                            "is missing the placeholder '{}' in the 'command' key",
                        )
                        exit_code = 1

sys.exit(exit_code)
