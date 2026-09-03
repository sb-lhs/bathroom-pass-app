"""Configuration handling for hallpass-qt — First-Run State pattern.

Resolves /etc/hallpass/config.json with dev fallback to user config / data dir.
Handles password hashing (PBKDF2), thresholds, alarm sound, TTS toggle.
Separates repository template (config.default.json) from runtime user data.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_BATHROOM_THRESHOLD = 420
DEFAULT_WATER_THRESHOLD = 180
DEFAULT_ALARM_SOUND = "mixkit-facility-alarm-sound-999.wav"
DEFAULT_TTS_ENABLED = True
DEFAULT_ADMIN_PASS = "admin123"

# Paths
SYSTEM_CONFIG_DIR = Path("/etc/hallpass")
SYSTEM_DATA_DIR = Path("/var/lib/hallpass")
USER_CONFIG_DIR = Path.home() / ".config" / "hallpass"
DEV_DATA_DIR = Path.cwd() / "data"
REPO_DEFAULT_CONFIG = Path.cwd() / "config.default.json"
SYSTEM_DEFAULT_CONFIG = Path("/usr/share/hallpass/config.default.json")

# Allow override via env for testing (read dynamically so tests can set env after import)
def _env_config_path() -> str | None:
    return os.environ.get("HALLPASS_CONFIG")

def _env_data_dir() -> str | None:
    return os.environ.get("HALLPASS_DATA_DIR")

def _is_test_mode() -> bool:
    return os.getenv("HALLPASS_TEST_MODE") == "1"


# Legacy aliases (dynamic via functions above; kept for import compatibility)
ENV_CONFIG_PATH = os.environ.get("HALLPASS_CONFIG")
ENV_DATA_DIR = os.environ.get("HALLPASS_DATA_DIR")


def _config_dir() -> Path:
    ecp = _env_config_path()
    if ecp:
        return Path(ecp).parent
    if SYSTEM_CONFIG_DIR.exists() and os.access(SYSTEM_CONFIG_DIR, os.W_OK):
        return SYSTEM_CONFIG_DIR
    if not SYSTEM_CONFIG_DIR.exists():
        return USER_CONFIG_DIR
    return USER_CONFIG_DIR


def _data_dir() -> Path:
    edd = _env_data_dir()
    if edd:
        return Path(edd)
    if SYSTEM_DATA_DIR.exists() and os.access(SYSTEM_DATA_DIR, os.W_OK):
        return SYSTEM_DATA_DIR
    if not SYSTEM_DATA_DIR.exists() and os.access("/var/lib", os.W_OK):
        return SYSTEM_DATA_DIR
    return DEV_DATA_DIR


def config_path() -> Path:
    ecp = _env_config_path()
    if ecp:
        return Path(ecp)
    return _config_dir() / "config.json"


def default_config_path() -> Path:
    # Prefer system installed template, fallback to repo
    if SYSTEM_DEFAULT_CONFIG.exists():
        return SYSTEM_DEFAULT_CONFIG
    return REPO_DEFAULT_CONFIG


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
    first_run: bool = False
    default_admin_pass: str = DEFAULT_ADMIN_PASS
    selected_camera_index: int = 0
    camera_picker_shown: bool = False
    simple_mode: bool = False
    simple_roster: list[str] = field(default_factory=list)

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        """PBKDF2 SHA256 with 100k iterations. Returns (hash_hex, salt)."""
        if not salt:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        # For backward compat, also support legacy sha256(salt+password) check in verify
        return hashed, salt

    @staticmethod
    def hash_password_legacy(password: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        # Test mode bypass
        if _is_test_mode():
            return True
        # Try PBKDF2 first
        try:
            pbkdf_hash, _ = self.hash_password(password, self.salt)
            if pbkdf_hash == self.admin_password_hash:
                return True
        except Exception:
            pass
        # Fallback legacy sha256(salt+password)
        try:
            if self.hash_password_legacy(password, self.salt) == self.admin_password_hash:
                return True
        except Exception:
            pass
        # Default admin pass on first_run (repo template)
        if self.first_run and password == self.default_admin_pass:
            return True
        return False

    def with_password(self, new_password: str) -> "AppConfig":
        hashed, salt = self.hash_password(new_password)
        return AppConfig(
            bathroom_threshold_seconds=self.bathroom_threshold_seconds,
            water_threshold_seconds=self.water_threshold_seconds,
            admin_password_hash=hashed,
            salt=salt,
            selected_alarm_sound=self.selected_alarm_sound,
            tts_enabled=self.tts_enabled,
            active_schedule_profile_override=self.active_schedule_profile_override,
            first_run=False,
            default_admin_pass=self.default_admin_pass,
            selected_camera_index=self.selected_camera_index,
            camera_picker_shown=self.camera_picker_shown,
            simple_mode=self.simple_mode,
            simple_roster=list(self.simple_roster) if self.simple_roster else [],
        )


def _ensure_config_exists() -> Path:
    """Ensure config.json exists at runtime — copy from default template if missing."""
    p = config_path()
    if p.exists():
        return p
    # Try to create from default template
    default_p = default_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if default_p.exists():
        try:
            data = json.loads(default_p.read_text(encoding="utf-8"))
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
            try:
                import os as _os
                _os.chmod(p, 0o666)
            except Exception:
                pass
            return p
        except Exception:
            pass
    # Fallback: create minimal first-run config
    fallback = {
        "first_run": True,
        "default_admin_pass": DEFAULT_ADMIN_PASS,
        "admin_password_hash": "",
        "salt": "",
        "bathroom_threshold_seconds": DEFAULT_BATHROOM_THRESHOLD,
        "water_threshold_seconds": DEFAULT_WATER_THRESHOLD,
        "selected_alarm_sound": DEFAULT_ALARM_SOUND,
        "tts_enabled": DEFAULT_TTS_ENABLED,
        "active_schedule_profile_override": None,
        "selected_camera_index": 0,
        "camera_picker_shown": False,
        "simple_mode": False,
        "simple_roster": [],
    }
    p.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
    return p


def load_config() -> AppConfig:
    """Load config from file, returning defaults if missing/corrupt. Handles first-run."""
    # Test mode: auto-authenticate, don't require file
    if _is_test_mode():
        return AppConfig(first_run=False, admin_password_hash="test", salt="test", default_admin_pass=DEFAULT_ADMIN_PASS)

    p = _ensure_config_exists()
    if not p.exists():
        return AppConfig(first_run=True, default_admin_pass=DEFAULT_ADMIN_PASS)
    try:
        raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        return AppConfig(
            bathroom_threshold_seconds=int(raw.get("bathroom_threshold_seconds", DEFAULT_BATHROOM_THRESHOLD)),
            water_threshold_seconds=int(raw.get("water_threshold_seconds", DEFAULT_WATER_THRESHOLD)),
            admin_password_hash=str(raw.get("admin_password_hash", "")),
            salt=str(raw.get("salt", "")),
            selected_alarm_sound=str(raw.get("selected_alarm_sound", DEFAULT_ALARM_SOUND)),
            tts_enabled=bool(raw.get("tts_enabled", DEFAULT_TTS_ENABLED)),
            active_schedule_profile_override=raw.get("active_schedule_profile_override"),
            first_run=bool(raw.get("first_run", False)),
            default_admin_pass=str(raw.get("default_admin_pass", DEFAULT_ADMIN_PASS)),
            selected_camera_index=int(raw.get("selected_camera_index", 0)),
            camera_picker_shown=bool(raw.get("camera_picker_shown", False)),
            simple_mode=bool(raw.get("simple_mode", False)),
            simple_roster=list(raw.get("simple_roster", [])),
        )
    except Exception:
        return AppConfig(first_run=True, default_admin_pass=DEFAULT_ADMIN_PASS)


def save_config(cfg: AppConfig) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Never write default_admin_pass in clear for non-first-run? Keep but empty after first_run
    data = asdict(cfg)
    if not cfg.first_run:
        # Remove default_admin_pass from persisted file after setup
        data.pop("default_admin_pass", None)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        import os as _os
        _os.chmod(p, 0o666)
    except Exception:
        pass
    data_dir().mkdir(parents=True, exist_ok=True)
    photos_dir().mkdir(parents=True, exist_ok=True)


def set_initial_admin_password(new_password: str) -> AppConfig:
    """Set initial admin password on first run — generates salt, hashes, clears first_run."""
    cfg = load_config()
    hashed, salt = AppConfig.hash_password(new_password)
    new_cfg = AppConfig(
        bathroom_threshold_seconds=cfg.bathroom_threshold_seconds,
        water_threshold_seconds=cfg.water_threshold_seconds,
        admin_password_hash=hashed,
        salt=salt,
        selected_alarm_sound=cfg.selected_alarm_sound,
        tts_enabled=cfg.tts_enabled,
        active_schedule_profile_override=cfg.active_schedule_profile_override,
        first_run=False,
        default_admin_pass=cfg.default_admin_pass,
        selected_camera_index=cfg.selected_camera_index,
        camera_picker_shown=cfg.camera_picker_shown,
        simple_mode=cfg.simple_mode,
        simple_roster=list(cfg.simple_roster) if cfg.simple_roster else [],
    )
    save_config(new_cfg)
    return new_cfg


def is_first_run() -> bool:
    return load_config().first_run


def threshold_for(pass_type: str, cfg: AppConfig) -> int:
    """Return threshold seconds for given pass type string."""
    if pass_type.lower() == "water":
        return cfg.water_threshold_seconds
    return cfg.bathroom_threshold_seconds
