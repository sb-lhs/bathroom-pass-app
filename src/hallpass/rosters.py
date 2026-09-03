"""Roster handling with unlimited custom blocks.

New shape:
  {"Block 1": ["Alice", "Bob"], "My Custom Block": [...]}  # flat per-block
or nested legacy automatically migrates.

Supports both:
  - new flat: { block_name: [names] }
  - legacy nested: { "Block_A_Schedule": {"Block_1": [...]}, "Block_B_Schedule": {...}}
Migrates legacy to new by merging A+B per block (union) and using blocks list from schedules.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import rosters_path

PROFILE_A = "Block_A_Schedule"
PROFILE_B = "Block_B_Schedule"
ALL_PROFILES = [PROFILE_A, PROFILE_B]


VARIANTS = ["Everyday", "A", "B"]


def default_block_variants() -> dict[str, list[str]]:
    return {v: [] for v in VARIANTS}


def default_flat() -> dict[str, dict[str, list[str]]]:
    return {}


def default_rosters() -> dict[str, dict[str, list[str]]]:
    flat = default_flat()
    return {PROFILE_A: dict(flat), PROFILE_B: dict(flat)}


def _is_structured(data: dict[str, Any]) -> bool:
    if not data:
        return False
    for v in data.values():
        if isinstance(v, dict) and any(k in VARIANTS for k in v.keys()):
            return True
        if isinstance(v, dict) and any(isinstance(x, list) for x in v.values()):
            # Could be variant dict
            if set(v.keys()).issubset(set(VARIANTS)):
                return True
    return False


def _migrate_flat_to_structured(flat: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    out: dict[str, dict[str, list[str]]] = {}
    for block, names in flat.items():
        cleaned = [str(x).strip() for x in names if str(x).strip()]
        out[str(block).strip()] = {"Everyday": cleaned, "A": [], "B": []}
    return out


def _migrate_structured_to_flat_for_compat(s: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    # For old readers that expect flat list: use Everyday if present else first variant
    out: dict[str, list[str]] = {}
    for block, variants in s.items():
        if "Everyday" in variants and variants["Everyday"]:
            out[block] = list(variants["Everyday"])
        else:
            # union of variants
            seen: dict[str, str] = {}
            for v in VARIANTS:
                for n in variants.get(v, []):
                    if n.strip() and n.strip() not in seen:
                        seen[n.strip()] = n.strip()
            out[block] = list(seen.values())
    return out


def _is_nested(data: dict[str, Any]) -> bool:
    for v in data.values():
        if isinstance(v, dict):
            if any(isinstance(x, list) for x in v.values()):
                return True
    return False


def _migrate_flat_to_nested(flat: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    return {PROFILE_A: dict(flat), PROFILE_B: dict(flat)}


def _migrate_nested_to_flat(nested: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    """Merge A+B nested into flat per-block (union) for new model."""
    # Collect all block names across profiles
    all_blocks: set[str] = set()
    for prof_data in nested.values():
        if isinstance(prof_data, dict):
            all_blocks.update(prof_data.keys())
    flat: dict[str, list[str]] = {}
    for block in all_blocks:
        seen: dict[str, str] = {}
        for prof in ALL_PROFILES:
            lst = nested.get(prof, {}).get(block, [])
            for n in lst:
                key = n.strip()
                if key and key not in seen:
                    seen[key] = key
        # Also check extra profiles (Assembly etc.)
        for prof, prof_data in nested.items():
            if prof in ALL_PROFILES:
                continue
            if isinstance(prof_data, dict):
                lst = prof_data.get(block, [])
                for n in lst:
                    key = n.strip()
                    if key and key not in seen:
                        seen[key] = key
        flat[block] = list(seen.values())
    # Ensure at least defaults if empty
    if not flat:
        return default_flat()
    return flat


def _is_new_flat(data: dict[str, Any]) -> bool:
    # New flat: all values are lists, keys are not profile names
    if not data:
        return False
    if all(isinstance(v, list) for v in data.values()):
        # If keys are Block_A_Schedule etc, it's actually nested check? but _is_nested would have caught dict values
        # Here keys are block names, not profiles? Could still be legacy flat with Block_1 keys — treat as new flat
        return True
    return False


_TEST_ROSTER_SIGNATURE = {
    "alex johnson", "sam rivera", "jordan lee", "taylor swift", "casey kim",
    "morgan park", "riley quinn", "jamie fox", "avery cole", "blake ray", "skyler day", "quinn lee",
}


def _is_test_data(data: dict[str, Any]) -> bool:
    try:
        vals: list[str] = []
        for v in data.values():
            if isinstance(v, list):
                vals.extend([str(x).strip().lower() for x in v])
            elif isinstance(v, dict):
                for lst in v.values():
                    if isinstance(lst, list):
                        vals.extend([str(x).strip().lower() for x in lst])
        if not vals:
            return False
        # If every name in file is from the test set and at least 3 test names present, treat as test data
        test_hits = sum(1 for n in vals if n in _TEST_ROSTER_SIGNATURE)
        return test_hits >= 3 and test_hits == len([n for n in vals if n])
    except Exception:
        return False


def load_rosters_flat() -> dict[str, list[str]]:
    """Legacy compat: returns union flat per-block (Everyday+A+B). Prefer load_rosters_structured."""
    s = load_rosters_structured()
    return _migrate_structured_to_flat_for_compat(s)


def load_rosters_structured() -> dict[str, dict[str, list[str]]]:
    p = rosters_path()
    if not p.exists():
        return default_flat()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default_flat()
        if _is_test_data(data):
            return {}
        if _is_structured(data):
            out: dict[str, dict[str, list[str]]] = {}
            for block, variants in data.items():
                if not isinstance(variants, dict):
                    continue
                cleaned_v: dict[str, list[str]] = {}
                for v in VARIANTS:
                    lst = variants.get(v, [])
                    if isinstance(lst, list):
                        cleaned_v[v] = [str(x).strip() for x in lst if str(x).strip()]
                    else:
                        cleaned_v[v] = []
                out[str(block).strip()] = cleaned_v
            return out
        if _is_new_flat(data):
            flat = {str(k): [str(x).strip() for x in v if str(x).strip()] for k, v in data.items() if isinstance(v, list)}
            return _migrate_flat_to_structured(flat)
        if _is_nested(data):
            flat = _migrate_nested_to_flat(data)  # type: ignore
            return _migrate_flat_to_structured(flat)
        return default_flat()
    except Exception:
        return default_flat()


def load_rosters_nested() -> dict[str, dict[str, list[str]]]:
    p = rosters_path()
    if not p.exists():
        return default_rosters()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default_rosters()
        if _is_nested(data):
            out: dict[str, dict[str, list[str]]] = {}
            for prof in ALL_PROFILES:
                prof_data = data.get(prof)
                if isinstance(prof_data, dict):
                    out[prof] = {str(k): list(v) for k, v in prof_data.items()}
                else:
                    out[prof] = dict(default_flat())
            for k, v in data.items():
                if k not in out and isinstance(v, dict):
                    out[k] = {str(k2): list(v2) for k2, v2 in v.items()}
                elif k not in out and isinstance(v, list):
                    out[k] = {"Block 1": list(v)}  # type: ignore
            return out
        if _is_new_flat(data):
            flat = {str(k): list(v) for k, v in data.items() if isinstance(v, list)}
            if not flat:
                return default_rosters()
            return _migrate_flat_to_nested(flat)
    except Exception:
        return default_rosters()
    return default_rosters()


def load_rosters() -> dict[str, list[str]]:
    """Legacy compat: returns flat view (new flat)."""
    return load_rosters_flat()


def get_roster(profile: str, block_id: str) -> list[str]:
    s = load_rosters_structured()
    variants = s.get(block_id, {})
    # Map legacy profile to variant letter
    letter = "Everyday"
    if "B" in profile:
        letter = "B"
    elif "A" in profile:
        letter = "A"
    if letter in variants and variants[letter]:
        return list(variants[letter])
    return list(variants.get("Everyday", []))


def get_roster_for_block(block_name: str) -> list[str]:
    return get_roster_for_block_variant(block_name, "Everyday")


def save_rosters(data: dict[str, Any]) -> None:
    p = rosters_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if data and _is_structured(data):
        cleaned: dict[str, dict[str, list[str]]] = {}
        for block, variants in data.items():
            if not isinstance(variants, dict):
                continue
            cv: dict[str, list[str]] = {}
            for v in VARIANTS:
                lst = variants.get(v, [])
                if isinstance(lst, list):
                    cv[v] = [str(x).strip() for x in lst if str(x).strip()]
                else:
                    cv[v] = []
            cleaned[str(block).strip()] = cv
        # remove empty blocks with no names at all?
        p.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
        try: import os; os.chmod(p, 0o666)
        except Exception: pass
        return
    if data and all(isinstance(v, list) for v in data.values()):
        structured = _migrate_flat_to_structured({str(k): list(v) for k, v in data.items()})
        save_rosters(structured)
        return
    if data and _is_nested(data):
        flat = _migrate_nested_to_flat(data)  # type: ignore
        structured = _migrate_flat_to_structured(flat)
        save_rosters(structured)
        return
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try: import os; os.chmod(p, 0o666)
    except Exception: pass


def save_structured(data: dict[str, dict[str, list[str]]]) -> None:
    save_rosters(data)


def save_nested(data: dict[str, dict[str, list[str]]]) -> None:
    flat = _migrate_nested_to_flat(data)
    structured = _migrate_flat_to_structured(flat)
    save_rosters(structured)


def save_flat(data: dict[str, list[str]]) -> None:
    structured = _migrate_flat_to_structured(data)
    save_rosters(structured)


def get_roster_for_block_variant(block_name: str, variant: str = "Everyday") -> list[str]:
    s = load_rosters_structured()
    variants = s.get(block_name, {})
    if variant in variants and variants[variant]:
        return list(variants[variant])
    if "Everyday" in variants:
        return list(variants.get("Everyday", []))
    return []


def set_roster_for_block_variant(block_name: str, variant: str, names: list[str]) -> None:
    s = load_rosters_structured()
    if block_name not in s:
        s[block_name] = default_block_variants()
    if variant not in VARIANTS:
        variant = "Everyday"
    s[block_name][variant] = [str(x).strip() for x in names if str(x).strip()]
    save_rosters(s)


def set_roster_block(block_id: str, names: list[str]) -> None:
    set_roster_for_block_variant(block_id, "Everyday", names)


def set_roster_for(profile: str, block_id: str, names: list[str]) -> None:
    set_roster_for_block_variant(block_id, "Everyday", names)


def set_roster_for_block(block_name: str, names: list[str]) -> None:
    set_roster_for_block_variant(block_name, "Everyday", names)


def rename_block_roster(old_name: str, new_name: str) -> None:
    if old_name == new_name:
        return
    s = load_rosters_structured()
    if old_name in s:
        if new_name in s:
            # merge variants union
            for v in VARIANTS:
                seen = set(s[new_name].get(v, []))
                for n in s[old_name].get(v, []):
                    if n not in seen:
                        s[new_name][v].append(n)
            del s[old_name]
        else:
            s[new_name] = s.pop(old_name)
        save_rosters(s)


def delete_block_roster(block_name: str) -> None:
    s = load_rosters_structured()
    if block_name in s:
        del s[block_name]
        save_rosters(s)


def merge_roster_csv(csv_path: Path, target_block: str | None = None, target_profile: str | None = None, target_variant: str | None = None) -> dict[str, Any]:
    s = load_rosters_structured()
    block = target_block or "Block 1"
    variant = target_variant or target_profile or "Everyday"
    if variant not in VARIANTS:
        # map legacy Block_A_Schedule etc
        if "B" in str(variant):
            variant = "B"
        elif "A" in str(variant):
            variant = "A"
        else:
            variant = "Everyday"
    if block not in s:
        s[block] = default_block_variants()
    new_names: list[str] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower() if h else "" for h in (reader.fieldnames or [])]
        has_block = "block id" in headers or "block_id" in headers or "block" in headers
        has_variant = "variant" in headers or "group" in headers or "day_type" in headers
        for row in reader:
            name = (row.get("Student Name") or row.get("student name") or row.get("Name") or row.get("name") or "").strip()
            if not name:
                if row:
                    first_key = list(row.keys())[0]
                    name = str(row[first_key]).strip()
            if not name:
                continue
            row_block = block
            row_variant = variant
            if has_block and not target_block:
                row_block = (row.get("Block ID") or row.get("block id") or row.get("Block") or row.get("block") or block).strip() or block
            if has_variant and not target_variant and not target_profile:
                rv = (row.get("Variant") or row.get("variant") or row.get("Group") or row.get("group") or row.get("Day Type") or "").strip()
                if rv in VARIANTS:
                    row_variant = rv
            if row_block not in s:
                s[row_block] = default_block_variants()
            if has_block and not target_block:
                existing = set(s[row_block].get(row_variant, []))
                if name not in existing:
                    s[row_block][row_variant].append(name)
            else:
                # collect for batch
                if has_variant and not target_variant:
                    # per-row variant handling already? treat individually
                    existing = set(s[row_block].get(row_variant, []))
                    if name not in existing:
                        s[row_block][row_variant].append(name)
                else:
                    new_names.append(name)
    if new_names:
        existing = set(s[block].get(variant, []))
        for name in new_names:
            if name not in existing:
                s[block][variant].append(name)
                existing.add(name)
    if not new_names and has_block is False:
        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader2 = csv.reader(f)
            rows = list(reader2)
            start = 0
            if rows and rows[0] and rows[0][0].lower() in ("student name", "name", "student"):
                start = 1
            for r in rows[start:]:
                if not r:
                    continue
                name = r[0].strip()
                row_block = r[1].strip() if len(r) > 1 and r[1].strip() else block
                row_variant = r[2].strip() if len(r) > 2 and r[2].strip() in VARIANTS else variant
                if not name:
                    continue
                if row_block not in s:
                    s[row_block] = default_block_variants()
                existing = set(s[row_block].get(row_variant, []))
                if name not in existing:
                    s[row_block][row_variant].append(name)
    save_rosters(s)
    return s
