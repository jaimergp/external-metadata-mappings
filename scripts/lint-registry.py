import sys
import json
from pathlib import Path

exit_code = 0

for path in sys.argv[1:]:
    path = Path(path)
    registry = json.loads(path.read_text())
    for definition in registry["definitions"]:
        if definition["id"].startswith("dep:virtual/") and definition.get("provides"):
            print(f"'{definition["id"]}' is a virtual DepURL and cannot have 'provides'.")
            exit_code = 1

sys.exit(exit_code)
