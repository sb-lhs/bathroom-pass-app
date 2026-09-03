"""Export CSV + photos to USB (/media) or local folder."""
from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime

from .config import csv_path, db_path, photos_dir, data_dir


def detect_usb_drives() -> list[Path]:
    """Auto-detect USB mounts under /media (and /run/media)."""
    candidates: list[Path] = []
    for base in [Path("/media"), Path("/run/media")]:
        if not base.exists():
            continue
        for user in base.iterdir():
            if user.is_dir():
                for mount in user.iterdir():
                    if mount.is_dir():
                        # Heuristic: check if writable and looks like USB (not root)
                        try:
                            if mount.stat().st_dev != Path("/").stat().st_dev or (mount / ".").exists():
                                candidates.append(mount)
                        except Exception:
                            candidates.append(mount)
            # Also direct mounts under /media
            if base == Path("/media") and user.is_dir() and user not in candidates:
                # If /media/<device> directly (no user subdir)
                try:
                    if any(user.iterdir()):
                        pass
                    else:
                        candidates.append(user)
                except Exception:
                    pass
    # Fallback: list /media/* if any
    fallback = [p for p in Path("/media").glob("*") if p.is_dir()] if Path("/media").exists() else []
    for p in fallback:
        if p not in candidates:
            candidates.append(p)
    return sorted(set(candidates))


def export_to(target: Path) -> Path:
    """Export CSV and photos to target folder. Returns export dir path."""
    target.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = target / f"hallpass_export_{ts}"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Copy CSV
    src_csv = csv_path()
    if src_csv.exists():
        shutil.copy2(src_csv, export_dir / "pass_history.csv")
    else:
        (export_dir / "pass_history.csv").write_text(
            "Student Name,Block ID,Pass Type,Time Out,Time In,Duration (Minutes),Overtime Status,Photo Out Path,Photo In Path\n",
            encoding="utf-8",
        )

    # Copy photos
    src_photos = photos_dir()
    dst_photos = export_dir / "photos"
    if src_photos.exists():
        shutil.copytree(src_photos, dst_photos, dirs_exist_ok=True)
    else:
        dst_photos.mkdir(parents=True, exist_ok=True)

    # Also copy DB for completeness
    src_db = db_path()
    if src_db.exists():
        shutil.copy2(src_db, export_dir / "logs.db")

    return export_dir


def export_auto(target_choice: str | None = None) -> Path:
    """target_choice: 'usb' -> auto-detect first USB, 'local' -> ~/hallpass_export, or explicit path."""
    if target_choice and target_choice.startswith("/"):
        return export_to(Path(target_choice))
    if target_choice == "usb":
        drives = detect_usb_drives()
        if drives:
            return export_to(drives[0])
        # Fallback to local if no USB
        return export_to(Path.home() / "hallpass_export")
    if target_choice == "local":
        return export_to(Path.home() / "hallpass_export")
    # Auto: prefer USB if present
    drives = detect_usb_drives()
    if drives:
        return export_to(drives[0])
    return export_to(Path.home() / "hallpass_export")
