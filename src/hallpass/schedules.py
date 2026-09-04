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
        "templates": {k: [{"name": "", "start": v["start"], "end": v["end"]} for v in blocks] for k, blocks in TEMPLATES.items()},
        "date_overrides": {},
        "custom_days": {},
        "weekday_templates": default_weekday_templates(),
        "weekday_letters": {wd: "Everyday" for wd in WEEKDAYS},
        "date_templates": {},
        "date_letters": {},
        "custom_day_templates": {},
        "custom_day_letters": {},
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
        return {k: [{"name": "", "start": b["start"], "end": b["end"]} for b in vs] for k, vs in TEMPLATES.items()}
    out: dict[str, list[dict[str, str]]] = {}
    for tname, blocks in raw_templates.items():
        tn = _norm_template_name(tname)
        if not isinstance(blocks, list):
            continue
        nblocks: list[dict[str, str]] = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            raw_name = str(b.get("name") if "name" in b else b.get("block_id", "") or "").strip()
            if _is_auto_name(raw_name):
                raw_name = ""
            nblocks.append({
                "name": raw_name,
                "start": _norm_time(str(b.get("start", "08:00")), "08:00"),
                "end": _norm_time(str(b.get("end", "09:30")), "09:30"),
            })
        if nblocks:
            out[tn] = sorted(nblocks, key=lambda x: x["start"])
    if not out:
        return {k: [{"name": "", "start": b["start"], "end": b["end"]} for b in vs] for k, vs in TEMPLATES.items()}
    return out


def _normalize_date_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        ks = str(k).strip()
        vs = str(v).strip()
        if len(ks) == 10 and ks[4] == "-" and ks[7] == "-":
            out[ks] = vs or "Everyday"
    return out


def _is_auto_name(raw: str) -> bool:
    s = (raw or "").strip()
    if s == "":
        return True
    if s.startswith("Block ") and s[6:].isdigit():
        return True
    return False


def get_display_blocks(template_name: str) -> list[dict[str, str]]:
    data = load_schedules()
    templates = data.get("templates", {})
    raw_blocks = templates.get(template_name) if isinstance(templates, dict) else None
    if not isinstance(raw_blocks, list):
        raw_blocks = []
    sorted_blocks = sorted(raw_blocks, key=lambda x: x.get("start", ""))
    auto_counter = 1
    out: list[dict[str, str]] = []
    for b in sorted_blocks:
        raw_name = str(b.get("name", "") or "").strip()
        is_auto = _is_auto_name(raw_name)
        if is_auto:
            display = f"Block {auto_counter}"
            auto_counter += 1
        else:
            display = raw_name
        out.append({
            "start": str(b.get("start", "")),
            "end": str(b.get("end", "")),
            "name": raw_name,
            "display_name": display,
            "is_custom": not is_auto,
        })
    return out


def get_all_display_names() -> list[str]:
    data = load_schedules()
    templates = data.get("templates", {}) if isinstance(data.get("templates"), dict) else {}
    seen: set[str] = set()
    for tname in templates.keys():
        for b in get_display_blocks(str(tname)):
            seen.add(b["display_name"])
    from .config import rosters_path
    import json as _json
    try:
        from .rosters import load_rosters_structured
        rosters = load_rosters_structured()
        for k in rosters.keys():
            seen.add(str(k))
    except Exception:
        pass
    def sort_key(n: str):
        if n.startswith("Block ") and n[6:].isdigit():
            return (0, int(n[6:]), n)
        return (1, 999, n.lower())
    return sorted(seen, key=sort_key)


def _normalize_weekday_letters(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        raw = {}
    out = {}
    for wd in WEEKDAYS:
        out[wd] = _norm_day_type(raw.get(wd, "Everyday"))
    return out


def _split_overrides_to_templates_letters(overrides: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    t_map: dict[str, str] = {}
    l_map: dict[str, str] = {}
    for k, v in overrides.items():
        raw = str(v).strip()
        if not raw:
            continue
        if ":" in raw:
            tmpl, letter = _parse_day_value(raw)
            t_map[k] = tmpl
            l_map[k] = letter
        else:
            norm_letter = _norm_day_type(raw)
            if norm_letter in ("A", "B", "Everyday") and raw in ("A","B","Everyday", "a","b"):
                l_map[k] = norm_letter
            else:
                # Could be template name alone or letter; try letter first
                if norm_letter in ("A","B"):
                    l_map[k] = norm_letter
                elif norm_letter == "Everyday" and raw.lower() in ("everyday",):
                    l_map[k] = "Everyday"
                else:
                    # treat as template
                    t_map[k] = _norm_template_name(raw)
    return t_map, l_map


def load_schedules() -> dict[str, Any]:
    p = schedules_path()
    if not p.exists():
        return default_schedules()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_schedules()

        def _load_weekday_letters(src: dict[str, Any]) -> dict[str, str]:
            wl_raw = src.get("weekday_letters")
            if isinstance(wl_raw, dict) and wl_raw:
                return _normalize_weekday_letters(wl_raw)
            dd = src.get("day_defaults", {})
            if isinstance(dd, dict) and dd:
                return _normalize_weekday_letters(dd)
            return _normalize_weekday_letters({})

        def _load_split_maps(src: dict[str, Any], prefix: str, legacy_key: str) -> tuple[dict[str, str], dict[str, str]]:
            t_key = f"{prefix}_templates"
            l_key = f"{prefix}_letters"
            # New split keys present
            if isinstance(src.get(t_key), dict) or isinstance(src.get(l_key), dict):
                t_raw = src.get(t_key, {}) if isinstance(src.get(t_key), dict) else {}
                l_raw = src.get(l_key, {}) if isinstance(src.get(l_key), dict) else {}
                t_map = {str(k): _norm_template_name(v) for k, v in t_raw.items() if len(str(k))==10 and str(k)[4]=="-"}
                l_map = {str(k): _norm_day_type(v) for k, v in l_raw.items() if len(str(k))==10 and str(k)[4]=="-"}
                # Also merge legacy if both present (back-compat)
                legacy = _normalize_date_map(src.get(legacy_key, {}))
                if legacy:
                    lt, ll = _split_overrides_to_templates_letters(legacy)
                    for kk, vv in lt.items():
                        t_map.setdefault(kk, vv)
                    for kk, vv in ll.items():
                        l_map.setdefault(kk, vv)
                return t_map, l_map
            # Only legacy
            legacy = _normalize_date_map(src.get(legacy_key, {}))
            if legacy:
                return _split_overrides_to_templates_letters(legacy)
            return {}, {}

        if "blocks" in raw and isinstance(raw["blocks"], list):
            nblocks: list[dict[str, str]] = []
            for b in raw["blocks"]:
                if not isinstance(b, dict):
                    continue
                name = str(b.get("name") or b.get("block_id") or "").strip()
                if _is_auto_name(name):
                    name = ""
                if not name and not b.get("start"):
                    continue
                # keep even empty name for auto slots; only skip if no start/end
                start = _norm_time(str(b.get("start", "08:00")), "08:00")
                end = _norm_time(str(b.get("end", "09:30")), "09:30")
                if not name and not start:
                    continue
                nblocks.append({
                    "name": name,
                    "start": start,
                    "end": end,
                    "day_type": _norm_day_type(b.get("day_type", "Everyday")),
                })
            if not nblocks:
                nblocks = default_blocks()
            # For default fallback when templates missing, build auto templates from nblocks
            templates = _normalize_templates(raw.get("templates", {"Regular": nblocks}))
            date_overrides = _normalize_date_map(raw.get("date_overrides", {}))
            custom_days = _normalize_date_map(raw.get("custom_days", {}))
            dt, dl = _load_split_maps(raw, "date", "date_overrides")
            ct, cl = _load_split_maps(raw, "custom_day", "custom_days")
            wt_raw = raw.get("weekday_templates", {})
            if not isinstance(wt_raw, dict):
                wt_raw = {}
            weekday_templates = {wd: _norm_template_name(wt_raw.get(wd, "Regular")) for wd in WEEKDAYS}
            weekday_letters = _load_weekday_letters(raw)
            dd = raw.get("day_defaults", {})
            if not isinstance(dd, dict):
                dd = {}
            new_dd: dict[str, str] = {}
            for wd in WEEKDAYS:
                new_dd[wd] = weekday_letters.get(wd, _norm_day_type(dd.get(wd, "Everyday")))
            profiles = raw.get("profiles") if isinstance(raw.get("profiles"), dict) else {}
            return {
                "blocks": nblocks,
                "templates": templates,
                "date_overrides": date_overrides,
                "custom_days": custom_days,
                "date_templates": dt,
                "date_letters": dl,
                "custom_day_templates": ct,
                "custom_day_letters": cl,
                "weekday_templates": weekday_templates,
                "weekday_letters": weekday_letters,
                "day_defaults": new_dd,
                "profiles": profiles,
            }
        if "profiles" in raw:
            migrated = _migrate_legacy_to_blocks(raw)
            migrated["templates"] = {"Regular": list(migrated["blocks"])}
            migrated["date_overrides"] = {}
            migrated["custom_days"] = {}
            migrated["date_templates"] = {}
            migrated["date_letters"] = {}
            migrated["custom_day_templates"] = {}
            migrated["custom_day_letters"] = {}
            migrated["weekday_templates"] = default_weekday_templates()
            migrated["weekday_letters"] = {wd: "Everyday" for wd in WEEKDAYS}
            return migrated
        if "templates" in raw:
            templates = _normalize_templates(raw.get("templates"))
            wt_raw = raw.get("weekday_templates", {})
            if not isinstance(wt_raw, dict):
                wt_raw = {}
            weekday_templates = {wd: _norm_template_name(wt_raw.get(wd, "Regular")) for wd in WEEKDAYS}
            weekday_letters = _load_weekday_letters(raw)
            dt, dl = _load_split_maps(raw, "date", "date_overrides")
            ct, cl = _load_split_maps(raw, "custom_day", "custom_days")
            return {
                "blocks": default_blocks(),
                "templates": templates,
                "date_overrides": _normalize_date_map(raw.get("date_overrides")),
                "custom_days": _normalize_date_map(raw.get("custom_days")),
                "date_templates": dt,
                "date_letters": dl,
                "custom_day_templates": ct,
                "custom_day_letters": cl,
                "weekday_templates": weekday_templates,
                "weekday_letters": weekday_letters,
                "day_defaults": dict(weekday_letters),
                "profiles": {},
            }
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
        data.setdefault("date_templates", {})
        data.setdefault("date_letters", {})
        data.setdefault("custom_day_templates", {})
        data.setdefault("custom_day_letters", {})
        data.setdefault("weekday_letters", {wd: "Everyday" for wd in WEEKDAYS})
    else:
        nblocks: list[dict[str, str]] = []
        for b in data["blocks"]:
            if not isinstance(b, dict):
                continue
            raw_name = str(b.get("name") or b.get("block_id") or "").strip()
            if _is_auto_name(raw_name):
                raw_name = ""
            start = _norm_time(str(b.get("start", "08:00")), "08:00")
            end = _norm_time(str(b.get("end", "09:30")), "09:30")
            nblocks.append({
                "name": raw_name,
                "start": start,
                "end": end,
                "day_type": _norm_day_type(b.get("day_type", "Everyday")),
            })
        if not nblocks:
            nblocks = default_blocks()
        data["blocks"] = sorted(nblocks, key=lambda x: x["start"])
        dd = data.get("day_defaults", {})
        if not isinstance(dd, dict):
            dd = {}
        wl = data.get("weekday_letters", {})
        if not isinstance(wl, dict):
            wl = {}
        # weekday_letters takes precedence over day_defaults
        merged_wl = _normalize_weekday_letters(wl if wl else dd)
        data["weekday_letters"] = merged_wl
        data["day_defaults"] = dict(merged_wl)
        data["templates"] = _normalize_templates(data.get("templates", {"Regular": nblocks}))
        # Preserve legacy maps for downgrade but also write split maps
        legacy_over = _normalize_date_map(data.get("date_overrides", {}))
        legacy_custom = _normalize_date_map(data.get("custom_days", {}))
        dt = data.get("date_templates", {})
        dl = data.get("date_letters", {})
        ct = data.get("custom_day_templates", {})
        cl = data.get("custom_day_letters", {})
        if isinstance(dt, dict):
            dt = {str(k): _norm_template_name(v) for k, v in dt.items() if len(str(k))==10}
        else:
            dt = {}
        if isinstance(dl, dict):
            dl = {str(k): _norm_day_type(v) for k, v in dl.items() if len(str(k))==10}
        else:
            dl = {}
        if isinstance(ct, dict):
            ct = {str(k): _norm_template_name(v) for k, v in ct.items() if len(str(k))==10}
        else:
            ct = {}
        if isinstance(cl, dict):
            cl = {str(k): _norm_day_type(v) for k, v in cl.items() if len(str(k))==10}
        else:
            cl = {}
        # If legacy provided but split empty, derive split (migrate on save)
        if legacy_over and not dt and not dl:
            nd_t, nd_l = _split_overrides_to_templates_letters(legacy_over)
            dt, dl = nd_t, nd_l
        if legacy_custom and not ct and not cl:
            nc_t, nc_l = _split_overrides_to_templates_letters(legacy_custom)
            ct, cl = nc_t, nc_l
        data["date_templates"] = dt
        data["date_letters"] = dl
        data["custom_day_templates"] = ct
        data["custom_day_letters"] = cl
        # Keep legacy composite for readers not yet updated (recombine)
        recombined_over = {}
        for k in set(list(dt.keys()) + list(dl.keys()) + list(legacy_over.keys())):
            tmpl = dt.get(k)
            lett = dl.get(k)
            if tmpl and lett and lett != "Everyday":
                recombined_over[k] = f"{tmpl}:{lett}"
            elif tmpl:
                recombined_over[k] = tmpl
            elif lett:
                recombined_over[k] = lett
            else:
                recombined_over[k] = legacy_over.get(k, "Everyday")
        recombined_custom = {}
        for k in set(list(ct.keys()) + list(cl.keys()) + list(legacy_custom.keys())):
            tmpl = ct.get(k)
            lett = cl.get(k)
            if tmpl and lett and lett != "Everyday":
                recombined_custom[k] = f"{tmpl}:{lett}"
            elif tmpl:
                recombined_custom[k] = tmpl
            elif lett:
                recombined_custom[k] = lett
            else:
                recombined_custom[k] = legacy_custom.get(k, "Everyday")
        data["date_overrides"] = _normalize_date_map(recombined_over)
        data["custom_days"] = _normalize_date_map(recombined_custom)
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
    norm_letter = _norm_day_type(s)
    if norm_letter in ("A", "B", "Everyday"):
        return "Regular", norm_letter
    return _norm_template_name(s), "Everyday"


def _resolve_today_entry(data: dict[str, Any], today_key: str, weekday: str | None = None) -> tuple[str, str] | None:
    # Priority: custom_day_* (date specific, highest) → date_* → weekday_* fallback
    # New split maps
    cdt = data.get("custom_day_templates", {})
    cdl = data.get("custom_day_letters", {})
    dt = data.get("date_templates", {})
    dl = data.get("date_letters", {})
    wt = data.get("weekday_templates", {})
    wl = data.get("weekday_letters", {})
    default_template = "Regular"
    if weekday and isinstance(wt, dict) and wt.get(weekday):
        default_template = _norm_template_name(wt.get(weekday))
    default_letter = "Everyday"
    if weekday and isinstance(wl, dict) and wl.get(weekday):
        default_letter = _norm_day_type(wl.get(weekday))

    # Custom day (per-date, highest)
    if isinstance(cdt, dict) and today_key in cdt and str(cdt[today_key]).strip():
        tmpl = _norm_template_name(cdt[today_key])
        lett = _norm_day_type(cdl.get(today_key, default_letter)) if isinstance(cdl, dict) else default_letter
        return tmpl, lett
    if isinstance(cdl, dict) and today_key in cdl and str(cdl[today_key]).strip():
        lett = _norm_day_type(cdl[today_key])
        tmpl = _norm_template_name(cdt.get(today_key, default_template)) if isinstance(cdt, dict) else default_template
        return tmpl, lett
    # Fallback to legacy custom_days composite
    custom = data.get("custom_days", {})
    if isinstance(custom, dict) and today_key in custom and str(custom[today_key]).strip():
        raw = str(custom[today_key]).strip()
        if ":" in raw:
            return _parse_day_value(raw)
        norm_letter = _norm_day_type(raw)
        if norm_letter in ("A", "B", "Everyday"):
            return default_template, norm_letter
        return _parse_day_value(raw)
    # Date overrides (from CSV/ICS import, medium priority)
    if isinstance(dt, dict) and today_key in dt and str(dt[today_key]).strip():
        tmpl = _norm_template_name(dt[today_key])
        lett = _norm_day_type(dl.get(today_key, default_letter)) if isinstance(dl, dict) else default_letter
        return tmpl, lett
    if isinstance(dl, dict) and today_key in dl and str(dl[today_key]).strip():
        lett = _norm_day_type(dl[today_key])
        tmpl = _norm_template_name(dt.get(today_key, default_template)) if isinstance(dt, dict) else default_template
        return tmpl, lett
    over = data.get("date_overrides", {})
    if isinstance(over, dict) and today_key in over and str(over[today_key]).strip():
        raw = str(over[today_key]).strip()
        if ":" in raw:
            return _parse_day_value(raw)
        norm_letter = _norm_day_type(raw)
        if norm_letter in ("A", "B", "Everyday"):
            return default_template, norm_letter
        return _parse_day_value(raw)
    if weekday:
        return default_template, default_letter
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

    # Use display blocks (insert-shift)
    display_blocks = []
    try:
        display_blocks = get_display_blocks(template_name)
    except Exception:
        display_blocks = []
    if not display_blocks:
        # Fallback to raw templates/blocks
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
                return prof, str(b.get("name") or b.get("display_name") or "")
        return "", ""
    t = now.strftime("%H:%M")
    for b in display_blocks:
        if b.get("start", "") <= t <= b.get("end", ""):
            prof = "Block_A_Schedule" if today_letter == "A" else "Block_B_Schedule" if today_letter == "B" else "Block_A_Schedule"
            return prof, b["display_name"]
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


def get_weekday_letters() -> dict[str, str]:
    return dict(load_schedules().get("weekday_letters", {wd: "Everyday" for wd in WEEKDAYS}))


def set_weekday_letter(weekday: str, letter: str) -> None:
    data = load_schedules()
    wl = data.get("weekday_letters", {})
    if not isinstance(wl, dict):
        wl = {}
    if weekday in WEEKDAYS:
        wl[weekday] = _norm_day_type(letter)
    data["weekday_letters"] = {wd: _norm_day_type(wl.get(wd, "Everyday")) for wd in WEEKDAYS}
    data["day_defaults"] = dict(data["weekday_letters"])
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
    norm = _normalize_date_map(m)
    dt, dl = _split_overrides_to_templates_letters(norm)
    data["date_templates"] = dt
    data["date_letters"] = dl
    data["date_overrides"] = norm
    save_schedules(data)


def get_date_templates() -> dict[str, str]:
    return dict(load_schedules().get("date_templates", {}))


def set_date_template(date_str: str, template_name: str) -> None:
    data = load_schedules()
    dt = data.get("date_templates", {})
    if not isinstance(dt, dict):
        dt = {}
    if not template_name.strip():
        dt.pop(date_str, None)
    else:
        dt[date_str] = _norm_template_name(template_name)
    data["date_templates"] = {k: _norm_template_name(v) for k, v in dt.items() if len(k)==10}
    save_schedules(data)


def get_date_letters() -> dict[str, str]:
    return dict(load_schedules().get("date_letters", {}))


def set_date_letter(date_str: str, letter: str) -> None:
    data = load_schedules()
    dl = data.get("date_letters", {})
    if not isinstance(dl, dict):
        dl = {}
    if not letter.strip():
        dl.pop(date_str, None)
    else:
        dl[date_str] = _norm_day_type(letter)
    data["date_letters"] = {k: _norm_day_type(v) for k, v in dl.items() if len(k)==10}
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
    # Also keep split maps in sync if used
    dt = data.get("custom_day_templates", {}) if isinstance(data.get("custom_day_templates"), dict) else {}
    dl = data.get("custom_day_letters", {}) if isinstance(data.get("custom_day_letters"), dict) else {}
    if not value.strip():
        dt.pop(date_str, None)
        dl.pop(date_str, None)
    else:
        if ":" in value:
            tmpl, lett = _parse_day_value(value)
            dt[date_str] = tmpl
            dl[date_str] = lett
        else:
            norm = _norm_day_type(value)
            if norm in ("A","B","Everyday"):
                dl[date_str] = norm
            else:
                dt[date_str] = _norm_template_name(value)
    data["custom_days"] = custom
    data["custom_day_templates"] = {k: _norm_template_name(v) for k, v in dt.items() if len(k)==10}
    data["custom_day_letters"] = {k: _norm_day_type(v) for k, v in dl.items() if len(k)==10}
    save_schedules(data)


def get_custom_day_templates() -> dict[str, str]:
    return dict(load_schedules().get("custom_day_templates", {}))


def get_custom_day_letters() -> dict[str, str]:
    return dict(load_schedules().get("custom_day_letters", {}))


def set_custom_day_template(date_str: str, template_name: str) -> None:
    data = load_schedules()
    ct = data.get("custom_day_templates", {})
    if not isinstance(ct, dict):
        ct = {}
    if not template_name.strip():
        ct.pop(date_str, None)
    else:
        ct[date_str] = _norm_template_name(template_name)
    data["custom_day_templates"] = {k: _norm_template_name(v) for k, v in ct.items() if len(k)==10}
    save_schedules(data)


def set_custom_day_letter(date_str: str, letter: str) -> None:
    data = load_schedules()
    cl = data.get("custom_day_letters", {})
    if not isinstance(cl, dict):
        cl = {}
    if not letter.strip():
        cl.pop(date_str, None)
    else:
        cl[date_str] = _norm_day_type(letter)
    data["custom_day_letters"] = {k: _norm_day_type(v) for k, v in cl.items() if len(k)==10}
    save_schedules(data)


def clear_custom_day(date_str: str) -> None:
    data = load_schedules()
    for key in ("custom_days","custom_day_templates","custom_day_letters"):
        m = data.get(key, {})
        if isinstance(m, dict) and date_str in m:
            m.pop(date_str, None)
            data[key] = m
    save_schedules(data)


def clear_date_override(date_str: str) -> None:
    data = load_schedules()
    for key in ("date_overrides","date_templates","date_letters"):
        m = data.get(key, {})
        if isinstance(m, dict) and date_str in m:
            m.pop(date_str, None)
            data[key] = m
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
