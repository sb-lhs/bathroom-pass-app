"""Configuration handling for hallpass-qt.

Resolves /etc/hallpass/config.json with dev fallback to user config / data dir.
Handles password hashing (PBKDF2-like via hashlib with salt), thresholds, alarm sound, TTS toggle.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_BATHROOM_THRESHOLD = 420
DEFAULT_WATER_THRESHOLD = 180
DEFAULT_ALARM_SOUND = "classic_chime.wav"
DEFAULT_TTS_ENABLED = True

# Resolve writable config path: try /etc/hallpass, fallback to user config
SYSTEM_CONFIG_DIR = Path("/etc/hallpass")
SYSTEM_DATA_DIR = Path("/var/lib/hallpass")
USER_CONFIG_DIR = Path.home() / ".config" / "hallpass"
DEV_DATA_DIR = Path.cwd() / "data"

# Allow override via env for testing (read dynamically so tests can set env after import)
def _env_config_path() -> str | None:
    return os.environ.get("HALLPASS_CONFIG")

def _env_data_dir() -> str | None:
    return os.environ.get("HALLPASS_DATA_DIR")


# Legacy aliases (dynamic via functions above; kept for import compatibility)
ENV_CONFIG_PATH = os.environ.get("HALLPASS_CONFIG")
ENV_DATA_DIR = os.environ.get("HALLPASS_DATA_DIR")


def _config_dir() -> Path:
    ecp = _env_config_path()
    if ecp:
        return Path(ecp).parent
    # Prefer system if writable or exists; else user
    if SYSTEM_CONFIG_DIR.exists() and os.access(SYSTEM_CONFIG_DIR, os.W_OK):
        return SYSTEM_CONFIG_DIR
    # In dev (no /etc/hallpass), use user config
    if not SYSTEM_CONFIG_DIR.exists():
        return USER_CONFIG_DIR
    # If system exists but not writable (e.g., running as user), use user
    return USER_CONFIG_DIR


def _data_dir() -> Path:
    edd = _env_data_dir()
    if edd:
        return Path(edd)
    if SYSTEM_DATA_DIR.exists() and os.access(SYSTEM_DATA_DIR, os.W_OK):
        return SYSTEM_DATA_DIR
    if not SYSTEM_DATA_DIR.exists() and os.access("/var/lib", os.W_OK):
        return SYSTEM_DATA_DIR
    # Dev fallback
    return DEV_DATA_DIR


def config_path() -> Path:
    ecp = _env_config_path()
    if ecp:
        return Path(ecp)
    return _config_dir() / "config.json"


def schedules_path() -> Path:
    return _config_dir() / "schedules.json"


def rosters_path() -> Path:
    return _config_dir() / "rosters.json"


def data_dir() -> Path:
    return _data_dir()


def photos_dir() -> Path:
    return data_dir() / "photos"


def csv_path() -> Path:
    return data_dir() / "pass_history.csv"


def db_path() -> Path:
    return data_dir() / "logs.db"


@dataclass(frozen=True)
class AppConfig:
    bathroom_threshold_seconds: int = DEFAULT_BATHROOM_THRESHOLD
    water_threshold_seconds: int = DEFAULT_WATER_THRESHOLD
    admin_password_hash: str = hashlib.sha256(b"").hexdigest()
    salt: str = "hallpass_secure_salt"
    selected_alarm_sound: str = DEFAULT_ALARM_SOUND
    tts_enabled: bool = DEFAULT_TTS_ENABLED
    active_schedule_profile_override: str | None = None

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        # Use sha256 with salt (spec shows sha256). For stronger security, use PBKDF2 but keep compat.
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self.hash_password(password, self.salt) == self.admin_password_hash

    def with_password(self, new_password: str) -> "AppConfig":
        return AppConfig(
            bathroom_threshold_seconds=self.bathroom_threshold_seconds,
            water_threshold_seconds=self.water_threshold_seconds,
            admin_password_hash=self.hash_password(new_password, self.salt),
            salt=self.salt,
            selected_alarm_sound=self.selected_alarm_sound,
            tts_enabled=self.tts_enabled,
            active_schedule_profile_override=self.active_schedule_profile_override,
        )


def load_config() -> AppConfig:
    """Load config from file, returning defaults if missing/corrupt."""
    p = config_path()
    if not p.exists():
        return AppConfig()
    try:
        raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        return AppConfig(
            bathroom_threshold_seconds=int(raw.get("bathroom_threshold_seconds", DEFAULT_BATHROOM_THRESHOLD)),
            water_threshold_seconds=int(raw.get("water_threshold_seconds", DEFAULT_WATER_THRESHOLD)),
            admin_password_hash=str(raw.get("admin_password_hash", hashlib.sha256(b"").hexdigest())),
            salt=str(raw.get("salt", "hallpass_secure_salt")),
            selected_alarm_sound=str(raw.get("selected_alarm_sound", DEFAULT_ALARM_SOUND)),
            tts_enabled=bool(raw.get("tts_enabled", DEFAULT_TTS_ENABLED)),
            active_schedule_profile_override=raw.get("active_schedule_profile_override"),
        )
    except Exception:
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
    # Ensure data dir exists too
    data_dir().mkdir(parents=True, exist_ok=True)
    photos_dir().mkdir(parents=True, exist_ok=True)


def threshold_for(pass_type: str, cfg: AppConfig) -> int:
    """Return threshold seconds for given pass type string."""
    if pass_type.lower() == "water":
        return cfg.water_threshold_seconds
    return cfg.bathroom_threshold_seconds
