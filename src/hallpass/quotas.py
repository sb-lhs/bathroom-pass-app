"""Pass quotas: daily-per-type + per-block caps, per-student overrides, one-time grants.

Quotas are 0 (= unlimited) unless an admin sets them. CANCELLED passes and
denied attempts never consume quota. One-time grants expire with the day.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .config import _config_dir

GRANT_FILE = "quota_grants.json"


def limits_for(cfg: Any, student: str) -> dict[str, int]:
    name = str(student or "").strip()
    over = {}
    try:
        over = (cfg.quota_overrides or {}).get(name, {})
    except Exception:
        over = {}
    def pick(key: str, fallback: int) -> int:
        try:
            v = int(over.get(key, fallback))
            return max(0, v)
        except Exception:
            return max(0, int(fallback or 0))
    return {
        "daily_bathroom": pick("daily_bathroom", getattr(cfg, "quota_daily_bathroom", 0)),
        "daily_water": pick("daily_water", getattr(cfg, "quota_daily_water", 0)),
        "per_block": pick("per_block", getattr(cfg, "quota_per_block", 0)),
    }


def _grants_path():
    return _config_dir() / GRANT_FILE


def _load_grants() -> set[str]:
    try:
        p = _grants_path()
        if not p.exists():
            return set()
        raw = json.loads(p.read_text(encoding="utf-8"))
        return set(str(x) for x in raw) if isinstance(raw, list) else set()
    except Exception:
        return set()


def _save_grants(keys: set[str]) -> None:
    try:
        p = _grants_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(sorted(keys), indent=2), encoding="utf-8")
    except Exception:
        pass


def grant_override(student: str, day: str | None = None) -> bool:
    name = str(student or "").strip().lower()
    if not name:
        return False
    if day is None:
        day = datetime.now().strftime("%Y-%m-%d")
    keys = {k for k in _load_grants() if k.endswith(f"|{day}")}
    keys.add(f"{name}|{day}")
    _save_grants(keys)
    return True


def _consume_grant(student: str, day: str) -> bool:
    key = f"{str(student or '').strip().lower()}|{day}"
    keys = _load_grants()
    if key not in keys:
        return False
    keys.discard(key)
    _save_grants(keys)
    return True


def check_quota(storage: Any, cfg: Any, student: str, pass_type: str, block_id: str, now: datetime | None = None) -> dict[str, Any]:
    name = str(student or "").strip()
    if now is None:
        now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    limits = limits_for(cfg, name)
    ptype = "Water" if str(pass_type or "").strip().lower() == "water" else "Bathroom"
    daily_key = "daily_water" if ptype == "Water" else "daily_bathroom"
    limit_daily = int(limits[daily_key])
    limit_block = int(limits["per_block"])
    used_daily = 0
    used_block = 0
    try:
        used_daily = int(storage.count_passes(name, day, pass_type=ptype))
        used_block = int(storage.count_passes(name, day, block=str(block_id or "")))
    except Exception:
        pass
    result = {
        "allowed": True,
        "reason": "",
        "used_daily": used_daily,
        "limit_daily": limit_daily,
        "used_block": used_block,
        "limit_block": limit_block,
        "override": False,
    }
    if limit_daily <= 0 and limit_block <= 0:
        return result
    if _consume_grant(name, day):
        result["override"] = True
        result["reason"] = "one-time override"
        return result
    if limit_daily > 0 and used_daily >= limit_daily:
        result["allowed"] = False
        result["reason"] = f"daily {used_daily}/{limit_daily}"
        return result
    if limit_block > 0 and used_block >= limit_block:
        result["allowed"] = False
        result["reason"] = f"block {used_block}/{limit_block} in {block_id}"
        return result
    return result
