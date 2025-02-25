import json
import sys

KEYS_WITH_MAYBE_DUPLICATES = {
    "definitions": "id",
    "mappings": "id",
    "package_managers": "name",
}

retcode = 0

for path in sys.argv[1:]:
    with open(path) as f:
        data = json.load(f)
        for key, sortkey in KEYS_WITH_MAYBE_DUPLICATES.items():
            if key not in data:
                continue
            seen = {}
            dedup = []
            value = data[key]
            for item in value:
                item_as_json = json.dumps(item, sort_keys=True)
                if item_as_json not in seen:
                    seen[item_as_json] = None
                    dedup.append(item)
            if len(dedup) != len(value):
                retcode += 1
            dedup.sort(key=lambda d: d.get(sortkey) or d.items())
            data[key] = dedup

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

sys.exit(retcode)
