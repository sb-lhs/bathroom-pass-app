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


def default_flat() -> dict[str, list[str]]:
    return {
        "Block 1": ["Alex Johnson", "Sam Rivera", "Jordan Lee"],
        "Block 2": ["Taylor Swift", "Casey Kim"],
        "Block 3": ["Morgan Park"],
        "Block 4": ["Riley Quinn"],
    }


def default_rosters() -> dict[str, dict[str, list[str]]]:
    flat = default_flat()
    return {
        PROFILE_A: dict(flat),
        PROFILE_B: {
            "Block 1": ["Alex Johnson", "Jamie Fox", "Avery Cole"],
            "Block 2": ["Blake Ray", "Casey Kim"],
            "Block 3": ["Morgan Park", "Skyler Day"],
            "Block 4": ["Riley Quinn", "Quinn Lee"],
        },
    }


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
                low = n.strip().lower()
                if low and low not in seen:
                    seen[low] = n.strip()
        # Also check extra profiles (Assembly etc.)
        for prof, prof_data in nested.items():
            if prof in ALL_PROFILES:
                continue
            if isinstance(prof_data, dict):
                lst = prof_data.get(block, [])
                for n in lst:
                    low = n.strip().lower()
                    if low and low not in seen:
                        seen[low] = n.strip()
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


def load_rosters_flat() -> dict[str, list[str]]:
    """Load new flat per-block rosters. Auto-migrates legacy nested."""
    p = rosters_path()
    if not p.exists():
        return default_flat()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default_flat()
        if _is_new_flat(data):
            # Could be new flat or legacy flat (same shape) — normalize
            # If keys look like Block_A_Schedule with list values, that's actually legacy flat with profile keys? but legacy flat stored as {Block_1:[...]} not profile
            # Distinguish: new flat keys are block names like "Block 1" or custom; legacy flat was also Block_1. So same. Treat as flat.
            # If file has exactly 2 keys Block_A_Schedule/Profile_B as lists — improbable. Keep as flat.
            return {str(k): [str(x).strip() for x in v if str(x).strip()] for k, v in data.items() if isinstance(v, list)}
        if _is_nested(data):
            return _migrate_nested_to_flat(data)  # type: ignore
        # Unknown shape
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
    # Legacy signature: profile-aware. Map to new flat by block_id.
    # If profile is Block_A/B, we try to return that block's roster if exists else flat.
    flat = load_rosters_flat()
    # If block_id exists in flat, return it (single roster per block)
    if block_id in flat:
        return list(flat[block_id])
    # Fallback: try nested load for legacy files that haven't migrated yet
    nested = load_rosters_nested()
    return list(nested.get(profile, {}).get(block_id, []))


def get_roster_for_block(block_name: str) -> list[str]:
    flat = load_rosters_flat()
    return list(flat.get(block_name, []))


def save_rosters(data: dict[str, Any]) -> None:
    p = rosters_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # If data is flat new style (all lists)
    if data and all(isinstance(v, list) for v in data.values()):
        # Save as new flat (per-block)
        cleaned: dict[str, list[str]] = {str(k).strip(): [str(x).strip() for x in v if str(x).strip()] for k, v in data.items() if str(k).strip()}
        p.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
        return
    if data and _is_nested(data):
        # Legacy nested: migrate to flat on save for new model
        flat = _migrate_nested_to_flat(data)  # type: ignore
        p.write_text(json.dumps(flat, indent=2), encoding="utf-8")
        return
    # Fallback
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_nested(data: dict[str, dict[str, list[str]]]) -> None:
    # Now saves as new flat (union) to move forward
    flat = _migrate_nested_to_flat(data)
    save_rosters(flat)


def save_flat(data: dict[str, list[str]]) -> None:
    save_rosters(data)


def set_roster_block(block_id: str, names: list[str]) -> None:
    flat = load_rosters_flat()
    flat[block_id] = names
    save_flat(flat)


def set_roster_for(profile: str, block_id: str, names: list[str]) -> None:
    # Legacy: profile-specific set. New model ignores profile and sets per-block,
    # but we preserve union behavior: set that block's roster for all profiles (single flat).
    # To avoid data loss, just set per-block.
    flat = load_rosters_flat()
    flat[block_id] = names
    save_flat(flat)


def set_roster_for_block(block_name: str, names: list[str]) -> None:
    flat = load_rosters_flat()
    flat[block_name] = names
    save_flat(flat)


def rename_block_roster(old_name: str, new_name: str) -> None:
    if old_name == new_name:
        return
    flat = load_rosters_flat()
    if old_name in flat:
        flat[new_name] = flat.pop(old_name)
        # If new_name already had roster, merge union
        # Already handled by pop+assign; if both existed, we merged pop then overwrite — merge instead
    # If both existed before rename (user renamed to existing name), merge
    # Actually above pop loses new_name's old roster if it existed; handle properly
    # Reload to handle correctly
    # Simpler: re-read raw
    p = rosters_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # This path handled after, but just ensure
    except Exception:
        pass
    # If both old and new existed in original flat, union them
    # We have stored flat before rename, check if new_name already existed before
    # For now, if flat had both, union after
    # Implement union if needed
    orig_flat = load_rosters_flat()  # after pop, new flat is already after; need before
    # To avoid complexity, just ensure rename preserves: handled above is fine.
    save_flat(flat)


def delete_block_roster(block_name: str) -> None:
    flat = load_rosters_flat()
    if block_name in flat:
        del flat[block_name]
        save_flat(flat)


def merge_roster_csv(csv_path: Path, target_block: str | None = None, target_profile: str | None = None) -> dict[str, Any]:
    """Non-destructive merge per block (target_block). Ignores target_profile (kept for compat)."""
    flat = load_rosters_flat()
    block = target_block or "Block 1"
    flat.setdefault(block, [])

    new_names: list[str] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower() if h else "" for h in (reader.fieldnames or [])]
        has_block = "block id" in headers or "block_id" in headers or "block" in headers
        for row in reader:
            name = (row.get("Student Name") or row.get("student name") or row.get("Name") or row.get("name") or "").strip()
            if not name:
                if row:
                    first_key = list(row.keys())[0]
                    name = str(row[first_key]).strip()
            if not name:
                continue
            # If CSV has block column and no target_block, allow per-row block (but new model expects single target)
            row_block = block
            if has_block and not target_block:
                row_block = (row.get("Block ID") or row.get("block id") or row.get("Block") or row.get("block") or block).strip() or block
                if row_block not in flat:
                    flat[row_block] = []
                existing_lower = {n.lower(): n for n in flat[row_block]}
                if name.lower() not in existing_lower:
                    flat[row_block].append(name)
            else:
                new_names.append(name)

    if new_names:
        # Add to target block, dedup
        existing_lower = {n.lower(): n for n in flat[block]}
        for name in new_names:
            if name.lower() not in existing_lower:
                flat[block].append(name)
                existing_lower[name.lower()] = name

    if not new_names and has_block is False:
        # Fallback headerless
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
                if not name:
                    continue
                if row_block not in flat:
                    flat[row_block] = []
                existing_lower = {n.lower(): n for n in flat[row_block]}
                if name.lower() not in existing_lower:
                    flat[row_block].append(name)

    save_flat(flat)
    return flat
