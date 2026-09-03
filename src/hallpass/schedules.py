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
    """Generic placeholder blocks — user edits names/times; not tied to any school."""
    return [
        {"name": "Block 1", "start": "08:00", "end": "09:20", "day_type": "Everyday"},
        {"name": "Block 2", "start": "09:25", "end": "10:45", "day_type": "Everyday"},
        {"name": "Block 3", "start": "10:50", "end": "12:10", "day_type": "Everyday"},
        {"name": "Block 4", "start": "12:15", "end": "13:35", "day_type": "Everyday"},
    ]


# Generic template structure — ships with one editable template; users add as many as they need
# (e.g. "Regular", "Late Start", "Early Release", "A Day", "Blue Day" — any sorting).
TEMPLATES: dict[str, list[dict[str, str]]] = {
    "Regular": [
        {"name": "Block 1", "start": "08:00", "end": "09:20"},
        {"name": "Block 2", "start": "09:25", "end": "10:45"},
        {"name": "Block 3", "start": "10:50", "end": "12:10"},
        {"name": "Block 4", "start": "12:15", "end": "13:35"},
    ],
}


def default_weekday_templates() -> dict[str, str]:
    return {wd: "Regular" for wd in WEEKDAYS}


def default_schedules() -> dict[str, Any]:
    return {
        "blocks": default_blocks(),
        "templates": {k: list(v) for k, v in TEMPLATES.items()},
        "date_overrides": {},
        "custom_days": {},
        "weekday_templates": default_weekday_templates(),
        "day_defaults": {wd: "Everyday" for wd in WEEKDAYS},
        "profiles": {},
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


def _norm_template_name(v: Any) -> str:
    name = str(v or "").strip()
    return name or "Regular"


def _normalize_templates(raw_templates: Any) -> dict[str, list[dict[str, str]]]:
    if not isinstance(raw_templates, dict) or not raw_templates:
        return {k: list(v) for k, v in TEMPLATES.items()}
    out: dict[str, list[dict[str, str]]] = {}
    for tname, blocks in raw_templates.items():
        tn = _norm_template_name(tname)
        if not isinstance(blocks, list):
            continue
        nblocks: list[dict[str, str]] = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            name = str(b.get("name") or b.get("block_id") or "").strip()
            if not name:
                continue
            nblocks.append({
                "name": name,
                "start": _norm_time(str(b.get("start", "08:00")), "08:00"),
                "end": _norm_time(str(b.get("end", "09:30")), "09:30"),
            })
        if nblocks:
            out[tn] = sorted(nblocks, key=lambda x: x["start"])
    return out or {k: list(v) for k, v in TEMPLATES.items()}


def _normalize_date_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        ks = str(k).strip()
        vs = str(v).strip()
        if len(ks) == 10 and ks[4] == "-" and ks[7] == "-":
            # accept YYYY-MM-DD; normalize value as template:letter or letter
            out[ks] = vs or "Everyday"
    return out


def load_schedules() -> dict[str, Any]:
    p = schedules_path()
    if not p.exists():
        return default_schedules()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_schedules()
        if "blocks" in raw and isinstance(raw["blocks"], list):
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
            dd = raw.get("day_defaults", {})
            if not isinstance(dd, dict):
                dd = {}
            new_dd: dict[str, str] = {}
            for wd in WEEKDAYS:
                new_dd[wd] = _norm_day_type(dd.get(wd, "Everyday"))
            templates = _normalize_templates(raw.get("templates", {"Regular": nblocks}))
            date_overrides = _normalize_date_map(raw.get("date_overrides", {}))
            custom_days = _normalize_date_map(raw.get("custom_days", {}))
            wt_raw = raw.get("weekday_templates", {})
            if not isinstance(wt_raw, dict):
                wt_raw = {}
            weekday_templates = {wd: _norm_template_name(wt_raw.get(wd, "Regular")) for wd in WEEKDAYS}
            profiles = raw.get("profiles") if isinstance(raw.get("profiles"), dict) else {}
            return {"blocks": nblocks, "templates": templates, "date_overrides": date_overrides, "custom_days": custom_days, "weekday_templates": weekday_templates, "day_defaults": new_dd, "profiles": profiles}
        if "profiles" in raw:
            migrated = _migrate_legacy_to_blocks(raw)
            migrated["templates"] = {"Regular": list(migrated["blocks"])}
            migrated["date_overrides"] = {}
            migrated["custom_days"] = {}
            migrated["weekday_templates"] = default_weekday_templates()
            return migrated
        if "templates" in raw:
            templates = _normalize_templates(raw.get("templates"))
            wt_raw = raw.get("weekday_templates", {})
            if not isinstance(wt_raw, dict):
                wt_raw = {}
            weekday_templates = {wd: _norm_template_name(wt_raw.get(wd, "Regular")) for wd in WEEKDAYS}
            return {"blocks": default_blocks(), "templates": templates, "date_overrides": _normalize_date_map(raw.get("date_overrides")), "custom_days": _normalize_date_map(raw.get("custom_days")), "weekday_templates": weekday_templates, "day_defaults": {wd: "Everyday" for wd in WEEKDAYS}, "profiles": {}}
        return default_schedules()
    except Exception:
        return default_schedules()


def save_schedules(data: dict[str, Any]) -> None:
    p = schedules_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if "blocks" not in data or not isinstance(data["blocks"], list):
        data = _migrate_legacy_to_blocks(data)
        data.setdefault("templates", {"Regular": list(data["blocks"])})
        data.setdefault("date_overrides", {})
        data.setdefault("custom_days", {})
    else:
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
        dd = data.get("day_defaults", {})
        if not isinstance(dd, dict):
            dd = {}
        new_dd: dict[str, str] = {}
        for wd in WEEKDAYS:
            new_dd[wd] = _norm_day_type(dd.get(wd, "Everyday"))
        data["day_defaults"] = new_dd
        data["templates"] = _normalize_templates(data.get("templates", {"Regular": nblocks}))
        data["date_overrides"] = _normalize_date_map(data.get("date_overrides", {}))
        data["custom_days"] = _normalize_date_map(data.get("custom_days", {}))
        wt_raw = data.get("weekday_templates", {})
        if not isinstance(wt_raw, dict):
            wt_raw = {}
        data["weekday_templates"] = {wd: _norm_template_name(wt_raw.get(wd, "Regular")) for wd in WEEKDAYS}
        data["profiles"] = data.get("profiles", {}) if isinstance(data.get("profiles"), dict) else {}
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- Helpers for new block model ---

def get_blocks() -> list[Block]:
    data = load_schedules()
    return [Block(b["name"], b["start"], b["end"], b["day_type"]) for b in data.get("blocks", [])]


def set_blocks(blocks: list[dict[str, str]]) -> None:
    data = load_schedules()
    data["blocks"] = blocks
    save_schedules(data)


def _parse_day_value(raw: str) -> tuple[str, str]:
    s = str(raw or "").strip()
    if ":" in s:
        template, letter = s.split(":", 1)
        return _norm_template_name(template), _norm_day_type(letter)
    # Could be just letter or just template; try letter first
    norm_letter = _norm_day_type(s)
    if norm_letter in ("A", "B", "Everyday"):
        return "Regular", norm_letter
    # Otherwise treat as template name with Everyday
    return _norm_template_name(s), "Everyday"


def _resolve_today_entry(data: dict[str, Any], today_key: str, weekday: str | None = None) -> tuple[str, str] | None:
    custom = data.get("custom_days", {})
    over = data.get("date_overrides", {})
    # weekday_templates fallback for template when only letter supplied
    wt = data.get("weekday_templates", {})
    default_template = "Regular"
    if weekday and isinstance(wt, dict) and wt.get(weekday):
        default_template = _norm_template_name(wt.get(weekday))
    if isinstance(custom, dict) and today_key in custom and str(custom[today_key]).strip():
        raw = str(custom[today_key]).strip()
        if ":" in raw:
            return _parse_day_value(raw)
        # letter-only → combine with weekday template
        norm_letter = _norm_day_type(raw)
        if norm_letter in ("A", "B", "Everyday"):
            return default_template, norm_letter
        return _parse_day_value(raw)
    if isinstance(over, dict) and today_key in over and str(over[today_key]).strip():
        raw = str(over[today_key]).strip()
        if ":" in raw:
            return _parse_day_value(raw)
        norm_letter = _norm_day_type(raw)
        if norm_letter in ("A", "B", "Everyday"):
            return default_template, norm_letter
        return _parse_day_value(raw)
    # No date-specific entry → fall back to weekday template with Everyday (set-and-forget)
    if weekday:
        return default_template, "Everyday"
    return None


def active_block(now: datetime | None = None, override: str | None = None) -> tuple[str, str]:
    data = load_schedules()
    if now is None:
        now = datetime.now()
    today_key = now.strftime("%Y-%m-%d")
    weekday = WEEKDAYS[now.weekday()]
    if override and override in ("A", "B", "Everyday"):
        today_letter = override
        template_name = _norm_template_name(data.get("weekday_templates", {}).get(weekday, "Regular"))
    elif override and ":" in override:
        template_name, today_letter = _parse_day_value(override)
    elif override:
        template_name, today_letter = _parse_day_value(override)
        if today_letter == "Everyday" and ":" not in override:
            resolved = _resolve_today_entry(data, today_key, weekday)
            if resolved:
                template_name, today_letter = resolved
    else:
        resolved = _resolve_today_entry(data, today_key, weekday)
        if resolved is None:
            return "", ""
        template_name, today_letter = resolved

    templates = data.get("templates", {})
    blocks: list[dict[str, str]] = []
    if isinstance(templates, dict) and template_name in templates:
        blocks = templates[template_name]
    else:
        blocks = data.get("blocks", [])
    t = now.strftime("%H:%M")
    for b in sorted(blocks, key=lambda x: x.get("start", "")):
        if b.get("start", "") <= t <= b.get("end", ""):
            prof = "Block_A_Schedule" if today_letter == "A" else "Block_B_Schedule" if today_letter == "B" else "Block_A_Schedule"
            return prof, b["name"]
    return "", ""


def resolve_today_letter(now: datetime | None = None, override: str | None = None) -> str:
    data = load_schedules()
    if now is None:
        now = datetime.now()
    today_key = now.strftime("%Y-%m-%d")
    weekday = WEEKDAYS[now.weekday()]
    if override and override in ("A", "B", "Everyday"):
        return override
    if override:
        _, letter = _parse_day_value(override)
        if letter in ("A", "B", "Everyday"):
            return letter
    resolved = _resolve_today_entry(data, today_key, weekday)
    if resolved:
        _, letter = resolved
        return letter
    return "Everyday"


def get_weekday_templates() -> dict[str, str]:
    return dict(load_schedules().get("weekday_templates", default_weekday_templates()))


def set_weekday_template(weekday: str, template_name: str) -> None:
    data = load_schedules()
    wt = data.get("weekday_templates", {})
    if not isinstance(wt, dict):
        wt = {}
    if weekday in WEEKDAYS:
        wt[weekday] = _norm_template_name(template_name)
    data["weekday_templates"] = {wd: _norm_template_name(wt.get(wd, "Regular")) for wd in WEEKDAYS}
    save_schedules(data)


def get_templates() -> dict[str, list[dict[str, str]]]:
    return load_schedules().get("templates", {"Regular": default_blocks()})


def set_templates(templates: dict[str, list[dict[str, str]]]) -> None:
    data = load_schedules()
    data["templates"] = _normalize_templates(templates)
    save_schedules(data)


def get_date_overrides() -> dict[str, str]:
    return dict(load_schedules().get("date_overrides", {}))


def set_date_overrides(m: dict[str, str]) -> None:
    data = load_schedules()
    data["date_overrides"] = _normalize_date_map(m)
    save_schedules(data)


def get_custom_days() -> dict[str, str]:
    return dict(load_schedules().get("custom_days", {}))


def set_custom_day(date_str: str, value: str) -> None:
    data = load_schedules()
    custom = _normalize_date_map(data.get("custom_days", {}))
    if not value.strip():
        custom.pop(date_str, None)
    else:
        custom[date_str] = value.strip()
    data["custom_days"] = custom
    save_schedules(data)


def import_date_overrides_csv(csv_path: Path, clear_existing: bool = True) -> dict[str, str]:
    import csv as _csv
    new_map: dict[str, str] = {} if clear_existing else dict(get_date_overrides())
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = _csv.DictReader(f)
        headers = [h.strip().lower() if h else "" for h in (reader.fieldnames or [])]
        has_date = any(h in ("date", "day", "yyyy-mm-dd") for h in headers)
        if not has_date:
            f.seek(0)
            rows = list(_csv.reader(f))
            for r in rows:
                if not r or len(r) < 1:
                    continue
                d = r[0].strip()
                if len(d) == 10 and d[4] == "-" and d[7] == "-":
                    val = r[1].strip() if len(r) > 1 else "Everyday"
                    new_map[d] = val
        else:
            for row in reader:
                d = (row.get("date") or row.get("Date") or row.get("DATE") or row.get("day") or "").strip()
                if not d:
                    d = (row.get("Day") or "").strip()
                if not d or len(d) != 10:
                    continue
                val = (row.get("type") or row.get("Type") or row.get("value") or row.get("template") or row.get("letter") or row.get("day_type") or "").strip() or "Everyday"
                if len(row) > 2 and not val:
                    # fallback second column
                    keys = list(row.keys())
                    if len(keys) > 1:
                        val = str(row[keys[1]]).strip() or "Everyday"
                new_map[d] = val
    set_date_overrides(new_map)
    return new_map


def import_date_overrides_ics(ics_path: Path, clear_existing: bool = True) -> dict[str, str]:
    text = ics_path.read_text(encoding="utf-8", errors="ignore")
    new_map: dict[str, str] = {} if clear_existing else dict(get_date_overrides())
    # lightweight ICS parse: each VEVENT with DTSTART and SUMMARY
    dt = ""
    summary = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("DTSTART"):
            # DTSTART;VALUE=DATE:20260915 or DTSTART:20260915
            if ":" in line:
                raw = line.split(":", 1)[1].strip()[:8]
                if len(raw) == 8 and raw.isdigit():
                    dt = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
                else:
                    dt = ""
        elif line.startswith("SUMMARY"):
            summary = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line == "END:VEVENT" and dt:
            new_map[dt] = summary or "Everyday"
            dt = ""
            summary = ""
    set_date_overrides(new_map)
    return new_map
