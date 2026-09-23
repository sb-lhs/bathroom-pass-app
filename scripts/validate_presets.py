#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hallpass.schedules import _sanitize_slug, validate_school_preset


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "schools"
    files = sorted(p for p in root.glob("*.json") if p.name != "index.json") if root.is_dir() else []
    if not files:
        print("No presets found in schools/ — nothing to validate.")
        return 0
    failed = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"FAIL {f.name}: not valid JSON ({e})")
            failed += 1
            continue
        errors = validate_school_preset(data)
        if isinstance(data, dict) and f.stem != _sanitize_slug(data.get("slug")):
            errors = errors + [f"filename must be <slug>.json (expected {_sanitize_slug(data.get('slug'))}.json)"]
        if errors:
            print(f"FAIL {f.name}:")
            for e in errors:
                print(f"  - {e}")
            failed += 1
        else:
            print(f"OK {f.name}")
    print(f"{len(files) - failed}/{len(files)} presets valid.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
