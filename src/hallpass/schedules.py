"""Schedule with unlimited custom-named blocks.

New shape:
{
  "blocks": [
    {"name": "Period 1", "start": "08:00", "end": "09:30", "day_type": "Everyday" | "A" | "B"},
    ...
  ],
  "day_defaults": {"Monday": "A", "Tuesday": "A", ...}  # A/B day per weekday; legacy "Block_A_Schedule" maps to "A"
}

Legacy shape (profiles + periods with block_id) auto-migrates on load.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import schedules_path

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


DAY_TYPES = ["Everyday", "A", "B"]


@dataclass
class Block:
    name: str
    start: str  # HH:MM
    end: str  # HH:MM
    day_type: str = "Everyday"  # Everyday | A | B

    def contains(self, t: str) -> bool:
        return self.start <= t <= self.end


def _norm_day_type(v: Any) -> str:
    if not v or not isinstance(v, str):
        return "Everyday"
    v = v.strip()
    if v in DAY_TYPES:
        return v
    # Legacy: Block_A_Schedule -> A, Block_B_Schedule -> B, Assembly -> Everyday, "A Day" -> A etc.
    low = v.lower()
    if "block_a" in low or low == "a" or "a day" in low:
        return "A"
    if "block_b" in low or low == "b" or "b day" in low:
        return "B"
    return "Everyday"


def _norm_time(t: str, fallback: str) -> str:
    t = (t or "").strip()
    if len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit():
        return t
    # Try HH:MM with single digit hour
    try:
        parts = t.split(":")
        if len(parts) == 2:
            h = int(parts[0]); m = int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
    except Exception:
        pass
    return fallback


def default_blocks() -> list[dict[str, str]]:
    return [
        {"name": "Block 1", "start": "08:00", "end": "09:30", "day_type": "Everyday"},
        {"name": "Block 2", "start": "09:35", "end": "11:05", "day_type": "Everyday"},
        {"name": "Block 3", "start": "11:10", "end": "12:40", "day_type": "Everyday"},
        {"name": "Block 4", "start": "13:10", "end": "14:40", "day_type": "Everyday"},
    ]


def default_schedules() -> dict[str, Any]:
    # New default uses blocks list; also keep legacy profiles for migrators that still expect them
    return {
        "blocks": default_blocks(),
        "day_defaults": {
            "Monday": "A",
            "Tuesday": "A",
            "Wednesday": "A",
            "Thursday": "B",
            "Friday": "B",
            "Saturday": "A",
            "Sunday": "A",
        },
        # legacy mirror for old code paths (not used by new logic)
        "profiles": {
            "Block_A_Schedule": {"periods": [{"block_id": "Block 1", "start": "08:00", "end": "09:30"}, {"block_id": "Block 2", "start": "09:35", "end": "11:05"}, {"block_id": "Block 3", "start": "11:10", "end": "12:40"}, {"block_id": "Block 4", "start": "13:10", "end": "14:40"}]},
            "Block_B_Schedule": {"periods": [{"block_id": "Block 1", "start": "08:00", "end": "09:30"}, {"block_id": "Block 2", "start": "09:35", "end": "11:05"}, {"block_id": "Block 3", "start": "11:10", "end": "12:40"}, {"block_id": "Block 4", "start": "13:10", "end": "14:40"}]},
        },
    }


def _migrate_legacy_to_blocks(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy profiles+periods to blocks list. Preserves times from A schedule (shared)."""
    profiles = data.get("profiles", {})
    # Try Block_A_Schedule first, else any profile
    src = profiles.get("Block_A_Schedule") or profiles.get("Block_A") or next(iter(profiles.values()), None) if profiles else None
    blocks: list[dict[str, str]] = []
    if src and isinstance(src, dict):
        for per in src.get("periods", []):
            if not isinstance(per, dict):
                continue
            name = str(per.get("block_id") or per.get("name") or "").strip()
            if not name:
                continue
            blocks.append({
                "name": name,
                "start": _norm_time(str(per.get("start", "08:00")), "08:00"),
                "end": _norm_time(str(per.get("end", "09:30")), "09:30"),
                "day_type": "Everyday",
            })
    if not blocks:
        blocks = default_blocks()
    # Normalize day_defaults
    dd = data.get("day_defaults", {})
    new_dd: dict[str, str] = {}
    for wd in WEEKDAYS:
        raw = dd.get(wd, "A")
        new_dd[wd] = _norm_day_type(raw)
    return {"blocks": blocks, "day_defaults": new_dd, "profiles": data.get("profiles", {})}


def load_schedules() -> dict[str, Any]:
    p = schedules_path()
    if not p.exists():
        return default_schedules()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_schedules()
        # New shape has "blocks" list
        if "blocks" in raw and isinstance(raw["blocks"], list):
            # Normalize blocks
            nblocks: list[dict[str, str]] = []
            for b in raw["blocks"]:
                if not isinstance(b, dict):
                    continue
                name = str(b.get("name") or b.get("block_id") or "").strip()
                if not name:
                    continue
                nblocks.append({
                    "name": name,
                    "start": _norm_time(str(b.get("start", "08:00")), "08:00"),
                    "end": _norm_time(str(b.get("end", "09:30")), "09:30"),
                    "day_type": _norm_day_type(b.get("day_type", "Everyday")),
                })
            if not nblocks:
                nblocks = default_blocks()
            # Normalize day_defaults
            dd = raw.get("day_defaults", {})
            if not isinstance(dd, dict):
                dd = {}
            new_dd: dict[str, str] = {}
            for wd in WEEKDAYS:
                new_dd[wd] = _norm_day_type(dd.get(wd, "A"))
            # Preserve profiles for legacy but ensure existence
            profiles = raw.get("profiles")
            if not isinstance(profiles, dict):
                # synthesize from blocks for compat
                profiles = {
                    "Block_A_Schedule": {"periods": [{"block_id": b["name"], "start": b["start"], "end": b["end"]} for b in nblocks]},
                    "Block_B_Schedule": {"periods": [{"block_id": b["name"], "start": b["start"], "end": b["end"]} for b in nblocks]},
                }
            return {"blocks": nblocks, "day_defaults": new_dd, "profiles": profiles}
        # Legacy without blocks
        if "profiles" in raw:
            return _migrate_legacy_to_blocks(raw)
        return default_schedules()
    except Exception:
        return default_schedules()


def save_schedules(data: dict[str, Any]) -> None:
    p = schedules_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Ensure blocks normalized before write
    if "blocks" not in data or not isinstance(data["blocks"], list):
        # Migrate on save
        data = _migrate_legacy_to_blocks(data)
    else:
        # Normalize day_type and times
        nblocks: list[dict[str, str]] = []
        for b in data["blocks"]:
            if not isinstance(b, dict):
                continue
            name = str(b.get("name") or b.get("block_id") or "").strip()
            if not name:
                continue
            nblocks.append({
                "name": name,
                "start": _norm_time(str(b.get("start", "08:00")), "08:00"),
                "end": _norm_time(str(b.get("end", "09:30")), "09:30"),
                "day_type": _norm_day_type(b.get("day_type", "Everyday")),
            })
        if not nblocks:
            nblocks = default_blocks()
        data["blocks"] = sorted(nblocks, key=lambda x: x["start"])
        # Normalize day_defaults
        dd = data.get("day_defaults", {})
        if not isinstance(dd, dict):
            dd = {}
        new_dd: dict[str, str] = {}
        for wd in WEEKDAYS:
            new_dd[wd] = _norm_day_type(dd.get(wd, "A"))
        data["day_defaults"] = new_dd
        # Keep profiles mirror updated for old readers (optional)
        data["profiles"] = {
            "Block_A_Schedule": {"periods": [{"block_id": b["name"], "start": b["start"], "end": b["end"]} for b in nblocks if b["day_type"] in ("Everyday", "A")] or [{"block_id": b["name"], "start": b["start"], "end": b["end"]} for b in nblocks]},
            "Block_B_Schedule": {"periods": [{"block_id": b["name"], "start": b["start"], "end": b["end"]} for b in nblocks if b["day_type"] in ("Everyday", "B")] or [{"block_id": b["name"], "start": b["start"], "end": b["end"]} for b in nblocks]},
        }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- Helpers for new block model ---

def get_blocks() -> list[Block]:
    data = load_schedules()
    return [Block(b["name"], b["start"], b["end"], b["day_type"]) for b in data.get("blocks", [])]


def set_blocks(blocks: list[dict[str, str]]) -> None:
    data = load_schedules()
    data["blocks"] = blocks
    save_schedules(data)


def active_block(now: datetime | None = None, override: str | None = None) -> tuple[str, str]:
    """Return (profile_name, block_id) for current time. Falls back to first block if outside periods.
    New: respects Everyday/A/B day_type and uses override as A/B letter if provided.
    Legacy compat: if override is Block_A_Schedule etc, maps to A/B.
    """
    data = load_schedules()
    if now is None:
        now = datetime.now()
    weekday = WEEKDAYS[now.weekday()]
    # Determine today letter A/B
    if override and override in ("A", "B", "Everyday"):
        today_letter = override
    elif override:
        today_letter = _norm_day_type(override)
        if today_letter == "Everyday":
            today_letter = _norm_day_type(data.get("day_defaults", {}).get(weekday, "A"))
    else:
        today_letter = _norm_day_type(data.get("day_defaults", {}).get(weekday, "A"))

    blocks = data.get("blocks", [])
    t = now.strftime("%H:%M")
    # Only return a block whose time and day_type match current time
    for b in sorted(blocks, key=lambda x: x.get("start", "")):
        dt = b.get("day_type", "Everyday")
        if dt != "Everyday" and dt != today_letter:
            continue
        if b.get("start", "") <= t <= b.get("end", ""):
            prof = "Block_A_Schedule" if today_letter == "A" else "Block_B_Schedule" if today_letter == "B" else "Block_A_Schedule"
            return prof, b["name"]
    # No matching block — return empty so roster is empty
    return "", ""


def resolve_today_letter(now: datetime | None = None, override: str | None = None) -> str:
    data = load_schedules()
    if now is None:
        now = datetime.now()
    weekday = WEEKDAYS[now.weekday()]
    if override and override in ("A", "B"):
        return override
    if override:
        norm = _norm_day_type(override)
        if norm in ("A", "B"):
            return norm
    return _norm_day_type(data.get("day_defaults", {}).get(weekday, "A"))
