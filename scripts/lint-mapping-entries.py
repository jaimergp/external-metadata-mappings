import sys
import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "registry.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text())
ALL_IDs = {item["id"] for item in REGISTRY["definitions"]}
CANONICAL_IDs = {
    item["id"] for item in REGISTRY["definitions"] if not item.get("provides")
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
        if extra := mapping_ids.difference(ALL_IDs):
            print(f"Some IDs in mapping '{path}' are not recognized:")
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

sys.exit(exit_code)
