"""Qt bridge exposing Python logic to QML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl

from .audio import AlarmService, TTSService
from .camera import SilentCamera
from .config import AppConfig, data_dir, is_first_run, load_config, photos_dir, save_config, set_initial_admin_password, threshold_for
from .export import detect_usb_drives, export_auto
from .rosters import (
    PROFILE_A,
    PROFILE_B,
    delete_block_roster,
    get_roster,
    get_roster_for_block,
    load_rosters,
    load_rosters_flat,
    load_rosters_nested,
    merge_roster_csv,
    rename_block_roster,
    save_flat,
    set_roster_for,
    set_roster_for_block,
)
from .schedules import active_block, get_blocks, load_schedules, save_schedules, resolve_today_letter
from .state_machine import PassStateMachine, PassType, State
from .storage import Storage


class Backend(QObject):
    # Signals for QML bindings
    rosterChanged = Signal()
    queueChanged = Signal()
    stateChanged = Signal(str)
    activeBlockChanged = Signal(str)
    activeProfileChanged = Signal(str)
    elapsedChanged = Signal(int)
    configChanged = Signal()
    exportStatusChanged = Signal(str)
    rosterImportStatusChanged = Signal(str)
    alarmSoundsChanged = Signal()
    scheduleChanged = Signal()
    historyChanged = Signal()
    photosChanged = Signal()
    passwordStatusChanged = Signal(str)
    alarmTestStatusChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.cfg: AppConfig = load_config()
        self.storage = Storage()
        self.camera = SilentCamera(warm=True, camera_index=int(getattr(self.cfg, "selected_camera_index", 0)))
        self.alarm = AlarmService()
        self.tts = TTSService()
        self.alarm.set_sound(self.cfg.selected_alarm_sound)

        self._block_id = "Block 1"
        self._profile = "Block_A_Schedule"
        self._resolve_block()

        self.sm = PassStateMachine(self.cfg, self.storage, lambda: self._block_id)
        self.sm.on_tts = self._on_tts
        self.sm.on_alarm_start = self.alarm.start
        self.sm.on_alarm_stop = self.alarm.stop
        self.sm.on_state_changed = self._on_state_changed

        # Timer
        self._elapsed = 0
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start()

        self._is_admin = False
        self._export_status = ""
        self._roster_import_status = ""
        self._photos_status = ""
        self._password_status = ""
        self._alarm_test_status = ""
        # Auto-purge photos older than 7 days on startup
        try:
            self._purge_old_photos_internal(days=7)
        except Exception:
            pass
        # Daily timer for weekly autodelete
        self._photos_timer = QTimer(self)
        self._photos_timer.setInterval(24*60*60*1000)
        self._photos_timer.timeout.connect(lambda: self._purge_old_photos_internal(days=7))
        self._photos_timer.start()

        # Resolve roster for current block
        self._update_roster_cache()

    def _resolve_block(self) -> None:
        try:
            prof, blk = active_block(override=self.cfg.active_schedule_profile_override)
            self._profile = prof
            self._block_id = blk
        except Exception:
            pass

    def _update_roster_cache(self) -> None:
        try:
            # New: per-block roster (ignores profile, uses block name)
            flat = load_rosters_flat()
            if self._block_id in flat:
                self._roster_cache = list(flat[self._block_id])
            else:
                # Fallback legacy profile-aware
                self._roster_cache = get_roster(self._profile, self._block_id)
            self._nested_rosters = load_rosters_nested()
            self._flat_rosters = flat
        except Exception:
            self._roster_cache = []
            self._nested_rosters = {}
            self._flat_rosters = {}

    def _get_roster_text(self, profile: str, block: str) -> str:
        try:
            lst = get_roster(profile, block)
            return ", ".join(lst)
        except Exception:
            return ""

    # --- QML Properties ---
    @Property(list, notify=rosterChanged)  # type: ignore
    def roster(self) -> list[str]:
        return getattr(self, "_roster_cache", [])

    @Property(list, notify=queueChanged)  # type: ignore
    def queue(self) -> list[dict[str, str]]:
        return [{"name": q.name, "passType": q.pass_type.value} for q in self.sm.queue_list()]

    @Property(str, notify=stateChanged)  # type: ignore
    def stateMode(self) -> str:
        return self.sm.state.value

    @Property(str, notify=activeBlockChanged)  # type: ignore
    def activeBlock(self) -> str:
        return self._block_id

    @Property(str, notify=activeProfileChanged)  # type: ignore
    def activeProfile(self) -> str:
        return self._profile

    @Property(str, notify=activeProfileChanged)  # type: ignore
    def activeDayLetter(self) -> str:
        try:
            return resolve_today_letter(override=self.cfg.active_schedule_profile_override)
        except Exception:
            return "A"

    @Property(int, notify=elapsedChanged)  # type: ignore
    def elapsedSeconds(self) -> int:
        return self._elapsed

    @Property(str, notify=stateChanged)  # type: ignore
    def activeStudent(self) -> str:
        return self.sm.active.student_name if self.sm.active else ""

    @Property(str, notify=stateChanged)  # type: ignore
    def activePassType(self) -> str:
        return self.sm.active.pass_type.value if self.sm.active else ""

    @Property(int, notify=stateChanged)  # type: ignore
    def thresholdSeconds(self) -> int:
        if self.sm.active:
            return threshold_for(self.sm.active.pass_type.value, self.cfg)
        return self.cfg.bathroom_threshold_seconds

    @Property(bool, notify=stateChanged)  # type: ignore
    def alarmMuted(self) -> bool:
        return self.sm.active.muted if self.sm.active else False

    @Property(int, notify=configChanged)  # type: ignore
    def bathroomThreshold(self) -> int:
        return self.cfg.bathroom_threshold_seconds

    @Property(int, notify=configChanged)  # type: ignore
    def waterThreshold(self) -> int:
        return self.cfg.water_threshold_seconds

    @Property(bool, notify=configChanged)  # type: ignore
    def ttsEnabled(self) -> bool:
        return self.cfg.tts_enabled

    @Property(list, notify=alarmSoundsChanged)  # type: ignore
    def alarmSounds(self) -> list[str]:
        return self.alarm.list_sounds()

    @Property(str, notify=configChanged)  # type: ignore
    def selectedAlarmSound(self) -> str:
        return self.cfg.selected_alarm_sound

    @Property(list, notify=activeProfileChanged)  # type: ignore
    def scheduleProfiles(self) -> list[str]:
        try:
            return list(load_schedules().get("profiles", {}).keys())
        except Exception:
            return ["Block_A_Schedule", "Block_B_Schedule", "Assembly"]

    @Property(list, notify=scheduleChanged)  # type: ignore
    def blocks(self) -> list[dict[str, str]]:
        try:
            return load_schedules().get("blocks", [])
        except Exception:
            return []

    @Property(list, notify=scheduleChanged)  # type: ignore
    def aDayPeriods(self) -> list[dict[str, str]]:
        try:
            # New: filter blocks by day_type Everyday/A, but keep legacy compat
            data = load_schedules()
            if "blocks" in data:
                return [b for b in data["blocks"] if b.get("day_type", "Everyday") in ("Everyday", "A")]
            prof = data.get("profiles", {}).get("Block_A_Schedule", {})
            return prof.get("periods", [])
        except Exception:
            return []

    @Property(list, notify=scheduleChanged)  # type: ignore
    def bDayPeriods(self) -> list[dict[str, str]]:
        try:
            data = load_schedules()
            if "blocks" in data:
                return [b for b in data["blocks"] if b.get("day_type", "Everyday") in ("Everyday", "B")]
            prof = data.get("profiles", {}).get("Block_B_Schedule", {})
            return prof.get("periods", [])
        except Exception:
            return []

    @Property("QVariantMap", notify=scheduleChanged)  # type: ignore
    def dayDefaults(self) -> dict[str, str]:
        try:
            raw = load_schedules().get("day_defaults", {})
            # Normalize legacy Block_A_Schedule -> A
            out: dict[str, str] = {}
            for k, v in raw.items():
                if isinstance(v, str):
                    if "Block_A" in v or v == "A":
                        out[k] = "A"
                    elif "Block_B" in v or v == "B":
                        out[k] = "B"
                    elif v in ("Everyday", "A", "B"):
                        out[k] = v
                    else:
                        out[k] = "A"
            return out
        except Exception:
            return {}

    # A/B roster text (comma-separated) for QML binding — legacy compat
    def _roster_text(self, profile: str, block: str) -> str:
        try:
            return ", ".join(get_roster(profile, block))
        except Exception:
            return ""

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterA1(self) -> str:
        return self._roster_text(PROFILE_A, "Block 1")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterA2(self) -> str:
        return self._roster_text(PROFILE_A, "Block 2")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterA3(self) -> str:
        return self._roster_text(PROFILE_A, "Block 3")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterA4(self) -> str:
        return self._roster_text(PROFILE_A, "Block 4")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterB1(self) -> str:
        return self._roster_text(PROFILE_B, "Block 1")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterB2(self) -> str:
        return self._roster_text(PROFILE_B, "Block 2")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterB3(self) -> str:
        return self._roster_text(PROFILE_B, "Block 3")

    @Property(str, notify=rosterChanged)  # type: ignore
    def rosterB4(self) -> str:
        return self._roster_text(PROFILE_B, "Block 4")

    @Property("QVariantMap", notify=rosterChanged)  # type: ignore
    def flatRosters(self) -> dict:
        try:
            return load_rosters_flat()
        except Exception:
            return {}

    @Property(list, notify=historyChanged)  # type: ignore
    def passHistory(self) -> list[dict]:
        try:
            # Recent 20, newest first
            logs = self.storage.get_logs()
            # last 20 reversed
            recent = logs[-20:][::-1]
            out=[]
            for r in recent:
                # Format times as HH:MM
                tout = r.time_out.strftime("%H:%M")
                tin = r.time_in.strftime("%H:%M") if r.time_in else ""
                # duration already minutes, but show mm:ss
                mins=int(r.duration_minutes)
                secs=int(round((r.duration_minutes-mins)*60))
                dur=f"{mins}:{secs:02d}"
                out.append({
                    "student": r.student_name,
                    "block": r.block_id,
                    "passType": r.pass_type.value,
                    "overtime": r.overtime_status.value,
                    "timeOut": tout,
                    "timeIn": tin,
                    "duration": dur,
                    "date": r.time_out.strftime("%m/%d"),
                })
            return out
        except Exception:
            return []

    @Property(list, notify=photosChanged)  # type: ignore
    def photos(self) -> list[dict]:
        try:
            return self._list_photos()
        except Exception:
            return []

    @Property("QVariantMap", notify=photosChanged)  # type: ignore
    def photoStats(self) -> dict:
        try:
            lst = self._list_photos()
            total = len(lst)
            if not total:
                return {"count": 0, "totalSize": "0 KB", "oldest": "-", "newest": "-", "folder": str(photos_dir())}
            import os
            # sizes
            total_bytes = sum(int(p.get("size", 0)) for p in lst)
            # folder
            folder = str(photos_dir())
            # oldest/newest by mtime
            try:
                oldest = min(lst, key=lambda x: x.get("mtime", 0))
                newest = max(lst, key=lambda x: x.get("mtime", 0))
                oldest_s = oldest.get("date", "-")
                newest_s = newest.get("date", "-")
            except Exception:
                oldest_s = newest_s = "-"
            # human size
            if total_bytes < 1024:
                hs = f"{total_bytes} B"
            elif total_bytes < 1024*1024:
                hs = f"{total_bytes/1024:.1f} KB"
            else:
                hs = f"{total_bytes/(1024*1024):.1f} MB"
            return {"count": total, "totalSize": hs, "oldest": oldest_s, "newest": newest_s, "folder": folder}
        except Exception:
            return {"count": 0, "totalSize": "0 KB", "oldest": "-", "newest": "-", "folder": str(photos_dir())}

    @Property(str, notify=photosChanged)  # type: ignore
    def photosFolder(self) -> str:
        try:
            return str(photos_dir())
        except Exception:
            return ""

    @Property(str, notify=photosChanged)  # type: ignore
    def photosStatus(self) -> str:
        return getattr(self, "_photos_status", "")

    @Property(str, notify=passwordStatusChanged)  # type: ignore
    def passwordStatus(self) -> str:
        return getattr(self, "_password_status", "")

    @Property(list, notify=photosChanged)  # type: ignore
    def availableCameras(self) -> list[int]:
        try:
            return self.camera.available_indices()
        except Exception:
            return [0]

    @Property(str, notify=alarmTestStatusChanged)  # type: ignore
    def alarmTestStatus(self) -> str:
        return getattr(self, "_alarm_test_status", "")

    @Property(bool, notify=configChanged)  # type: ignore
    def isFirstRun(self) -> bool:
        try:
            return is_first_run()
        except Exception:
            return False

    @Property(bool, notify=configChanged)  # type: ignore
    def isAdminAuthenticated(self) -> bool:
        return self._is_admin

    @Property(str, notify=exportStatusChanged)  # type: ignore
    def exportStatus(self) -> str:
        return self._export_status

    @Property(str, notify=rosterImportStatusChanged)  # type: ignore
    def rosterImportStatus(self) -> str:
        return self._roster_import_status

    @Property(bool, notify=configChanged)  # type: ignore
    def requireQuitAuth(self) -> bool:
        return self.cfg.admin_password_hash != AppConfig().admin_password_hash

    # --- New per-block helpers ---
    @Slot(str, result=str)
    def getRosterForBlock(self, block_name: str) -> str:
        try:
            lst = get_roster_for_block(block_name)
            return ", ".join(lst)
        except Exception:
            return ""

    @Slot(str, str, result=bool)
    def setRosterForBlock(self, block_name: str, csv_text: str) -> bool:
        try:
            names = [n.strip() for n in csv_text.split(",") if n.strip()]
            seen: dict[str, str] = {}
            for n in names:
                key = n.strip()
                if key and key not in seen:
                    seen[key] = key
            cleaned = list(seen.values())
            set_roster_for_block(block_name, cleaned)
            self._update_roster_cache()
            self.rosterChanged.emit()
            self._roster_import_status = f"Saved {block_name} — {len(cleaned)} students"
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return True
        except Exception as e:
            self._roster_import_status = f"Save failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return False

    @Slot(str, str, result=bool)
    def importRosterForBlock(self, file_url: str, block_name: str) -> bool:
        try:
            path = file_url
            if path.startswith("file://"):
                path = QUrl(path).toLocalFile()
            p = Path(path)
            merge_roster_csv(p, target_block=block_name)
            self._update_roster_cache()
            self._roster_import_status = f"Imported {p.name} into {block_name}"
            self.rosterChanged.emit()
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return True
        except Exception as e:
            self._roster_import_status = f"Import failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return False

    # Schedule block CRUD
    @Slot(str, str, str, str, result=bool)
    def addBlock(self, name: str, start: str, end: str, day_type: str) -> bool:
        try:
            name = name.strip()
            if not name:
                self._roster_import_status = "Block name required"
                self.rosterImportStatusChanged.emit(self._roster_import_status)
                return False
            data = load_schedules()
            blocks = data.get("blocks", [])
            if any(b.get("name", "").lower() == name.lower() for b in blocks):
                self._roster_import_status = f"Block '{name}' already exists"
                self.rosterImportStatusChanged.emit(self._roster_import_status)
                return False
            # Validate times
            def ok(t: str) -> bool:
                try:
                    h, m = t.split(":"); return 0 <= int(h) <= 23 and 0 <= int(m) <= 59
                except Exception:
                    return False
            if not ok(start) or not ok(end):
                self._roster_import_status = "Use HH:MM (e.g., 08:00)"
                self.rosterImportStatusChanged.emit(self._roster_import_status)
                return False
            dt = day_type if day_type in ("Everyday", "A", "B", "Late Start", "Early Dismissal", "PowerHour") else "Everyday"
            blocks.append({"name": name, "start": start.strip(), "end": end.strip(), "day_type": dt})
            data["blocks"] = blocks
            save_schedules(data)
            # Ensure roster entry exists
            flat = load_rosters_flat()
            if name not in flat:
                flat[name] = []
                save_flat(flat)
            self._resolve_block()
            self._update_roster_cache()
            self.scheduleChanged.emit()
            self.rosterChanged.emit()
            self.activeBlockChanged.emit(self._block_id)
            return True
        except Exception as e:
            self._roster_import_status = f"Add failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return False

    @Slot(str, str, str, str, str, result=bool)
    def updateBlock(self, old_name: str, new_name: str, start: str, end: str, day_type: str) -> bool:
        try:
            old_name = old_name.strip(); new_name = new_name.strip()
            if not new_name:
                return False
            data = load_schedules()
            blocks = data.get("blocks", [])
            idx = -1
            for i, b in enumerate(blocks):
                if b.get("name", "") == old_name:
                    idx = i; break
            if idx == -1:
                return False
            # Duplicate check if renaming
            if old_name.lower() != new_name.lower() and any(b.get("name","").lower()==new_name.lower() for b in blocks):
                self._roster_import_status = f"Block '{new_name}' already exists"
                self.rosterImportStatusChanged.emit(self._roster_import_status)
                return False
            dt = day_type if day_type in ("Everyday", "A", "B", "Late Start", "Early Dismissal", "PowerHour") else "Everyday"
            blocks[idx] = {"name": new_name, "start": start.strip(), "end": end.strip(), "day_type": dt}
            data["blocks"] = blocks
            save_schedules(data)
            if old_name != new_name:
                rename_block_roster(old_name, new_name)
            self._resolve_block()
            self._update_roster_cache()
            self.scheduleChanged.emit()
            self.rosterChanged.emit()
            self.activeBlockChanged.emit(self._block_id)
            return True
        except Exception as e:
            self._roster_import_status = f"Update failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return False

    @Slot(str, result=bool)
    def deleteBlock(self, name: str) -> bool:
        try:
            data = load_schedules()
            blocks = data.get("blocks", [])
            nblocks = [b for b in blocks if b.get("name","") != name]
            if len(nblocks) == len(blocks):
                return False
            if len(nblocks) == 0:
                self._roster_import_status = "Must keep at least one block"
                self.rosterImportStatusChanged.emit(self._roster_import_status)
                return False
            data["blocks"] = nblocks
            save_schedules(data)
            delete_block_roster(name)
            self._resolve_block()
            self._update_roster_cache()
            self.scheduleChanged.emit()
            self.rosterChanged.emit()
            self.activeBlockChanged.emit(self._block_id)
            return True
        except Exception as e:
            self._roster_import_status = f"Delete failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)
            return False

    # --- Slots ---
    @Slot(str, str)
    def selectStudent(self, name: str, pass_type: str) -> None:
        self._resolve_block()
        self._update_roster_cache()
        pt = PassType.Water if pass_type == "Water" else PassType.Bathroom
        photo = self.camera.capture("out", student=name, block=self._block_id or "NoBlock")
        ok = self.sm.select_student(name, pt, photo)
        if ok:
            self._elapsed = 0
            self.stateChanged.emit(self.sm.state.value)
            self.elapsedChanged.emit(self._elapsed)
            self.queueChanged.emit()
            self.photosChanged.emit()

    @Slot(str, str)
    def enqueue(self, name: str, pass_type: str) -> None:
        self._resolve_block()
        self._update_roster_cache()
        pt = PassType.Water if pass_type == "Water" else PassType.Bathroom
        photo = self.camera.capture("out", student=name, block=self._block_id or "NoBlock")
        if self.sm.enqueue(name, pt, photo):
            self.queueChanged.emit()
            self.photosChanged.emit()

    @Slot()
    def returnPass(self) -> None:
        # Capture 'in' with current active student's name/block (the returning student's block, not current time's)
        active_name = self.sm.active.student_name if self.sm.active else ""
        active_block = self.sm.active.block_id if self.sm.active else self._block_id
        # Don't re-resolve here — use the block the pass was started in
        photo_in = self.camera.capture("in", student=active_name, block=active_block or "NoBlock")
        rec = self.sm.return_pass(photo_in)
        self._elapsed = 0
        self.stateChanged.emit(self.sm.state.value)
        self.elapsedChanged.emit(self._elapsed)
        self.queueChanged.emit()
        self.historyChanged.emit()
        self.photosChanged.emit()

    @Slot()
    def muteAlarm(self) -> None:
        self.sm.mute_alarm()
        self.stateChanged.emit(self.sm.state.value)

    @Slot(str, str, result=bool)
    def setInitialPassword(self, new_password: str, confirm_password: str) -> bool:
        if not new_password or new_password != confirm_password:
            self._is_admin = False
            self._password_status = "Passwords do not match"
            try: self.passwordStatusChanged.emit(self._password_status)
            except Exception: pass
            self.configChanged.emit()
            return False
        if len(new_password) < 4:
            self._is_admin = False
            self._password_status = "Password must be at least 4 characters"
            try: self.passwordStatusChanged.emit(self._password_status)
            except Exception: pass
            self.configChanged.emit()
            return False
        try:
            self.cfg = set_initial_admin_password(new_password)
            self._is_admin = True
            self._password_status = "Password set"
            try: self.passwordStatusChanged.emit(self._password_status)
            except Exception: pass
            self.configChanged.emit()
            return True
        except Exception as e:
            import traceback; traceback.print_exc()
            self._is_admin = False
            self._password_status = f"Failed: {e}"
            try: self.passwordStatusChanged.emit(self._password_status)
            except Exception: pass
            self.configChanged.emit()
            return False

    @Slot(str, result=bool)
    def verifyAdmin(self, password: str) -> bool:
        # Test mode bypass handled in AppConfig.verify_password
        ok = self.cfg.verify_password(password)
        # Refresh cfg in case first_run state changed
        try:
            self.cfg = load_config()
        except Exception:
            pass
        self._is_admin = ok
        self.configChanged.emit()
        return ok

    @Slot()
    def logoutAdmin(self) -> None:
        self._is_admin = False
        self._password_status = ""
        try: self.passwordStatusChanged.emit(self._password_status)
        except Exception: pass
        self.configChanged.emit()

    @Property(int, notify=configChanged)  # type: ignore
    def selectedCameraIndex(self) -> int:
        return int(getattr(self.cfg, "selected_camera_index", 0))

    @Property(list, notify=configChanged)  # type: ignore
    def availableCameraIndices(self) -> list[int]:
        try:
            return self.camera.available_indices(force_probe=True)
        except Exception:
            return [0]

    @Slot(int, result=bool)
    def setSelectedCameraIndex(self, idx: int) -> bool:
        try:
            idx = int(idx)
            self.cfg = AppConfig(
                bathroom_threshold_seconds=self.cfg.bathroom_threshold_seconds,
                water_threshold_seconds=self.cfg.water_threshold_seconds,
                admin_password_hash=self.cfg.admin_password_hash,
                salt=self.cfg.salt,
                selected_alarm_sound=self.cfg.selected_alarm_sound,
                tts_enabled=self.cfg.tts_enabled,
                active_schedule_profile_override=self.cfg.active_schedule_profile_override,
                first_run=self.cfg.first_run,
                default_admin_pass=self.cfg.default_admin_pass,
                selected_camera_index=idx,
                camera_picker_shown=True,
            )
            save_config(self.cfg)
            # Update camera
            try:
                self.camera._camera_index = idx
                self.camera._available_indices = [idx]
                self.camera.warm()
            except Exception:
                pass
            self.configChanged.emit()
            return True
        except Exception:
            return False

    @Slot(result=bool)
    def markCameraPickerShown(self) -> bool:
        try:
            self.cfg = AppConfig(
                bathroom_threshold_seconds=self.cfg.bathroom_threshold_seconds,
                water_threshold_seconds=self.cfg.water_threshold_seconds,
                admin_password_hash=self.cfg.admin_password_hash,
                salt=self.cfg.salt,
                selected_alarm_sound=self.cfg.selected_alarm_sound,
                tts_enabled=self.cfg.tts_enabled,
                active_schedule_profile_override=self.cfg.active_schedule_profile_override,
                first_run=self.cfg.first_run,
                default_admin_pass=self.cfg.default_admin_pass,
                selected_camera_index=self.cfg.selected_camera_index,
                camera_picker_shown=True,
            )
            save_config(self.cfg)
            self.configChanged.emit()
            return True
        except Exception:
            return False

    @Property(bool, notify=configChanged)  # type: ignore
    def needsCameraPicker(self) -> bool:
        try:
            return not bool(getattr(self.cfg, "camera_picker_shown", False)) and len(self.camera.available_indices()) > 1
        except Exception:
            return False

    @Slot(str, str, str)
    def importRoster(self, file_url: str, block_id: str, profile: str) -> None:
        # Legacy compat: ignore profile, use block_id as block name
        try:
            path = file_url
            if path.startswith("file://"):
                path = QUrl(path).toLocalFile()
            p = Path(path)
            # Map legacy Block_1 etc to actual block name
            flat = load_rosters_flat()
            target = block_id
            # If block_id like Block_1 and flat has "Block 1" (space), map
            if target not in flat and target.replace("_", " ") in flat:
                target = target.replace("_", " ")
            merge_roster_csv(p, target_block=target)
            self._update_roster_cache()
            self._roster_import_status = f"Imported {p.name} into {target}"
            self.rosterChanged.emit()
            self.rosterImportStatusChanged.emit(self._roster_import_status)
        except Exception as e:
            self._roster_import_status = f"Import failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)

    @Slot(str, str, str)
    def setRosterText(self, profile: str, block_id: str, csv_text: str) -> None:
        # Legacy compat -> delegate to per-block
        try:
            target = block_id
            flat = load_rosters_flat()
            if target not in flat and target.replace("_", " ") in flat:
                target = target.replace("_", " ")
            self.setRosterForBlock(target, csv_text)
        except Exception as e:
            self._roster_import_status = f"Save failed: {e}"
            self.rosterImportStatusChanged.emit(self._roster_import_status)

    @Slot(str)
    def setAlarmSound(self, name: str) -> None:
        self.cfg = AppConfig(
            bathroom_threshold_seconds=self.cfg.bathroom_threshold_seconds,
            water_threshold_seconds=self.cfg.water_threshold_seconds,
            admin_password_hash=self.cfg.admin_password_hash,
            salt=self.cfg.salt,
            selected_alarm_sound=name,
            tts_enabled=self.cfg.tts_enabled,
            active_schedule_profile_override=self.cfg.active_schedule_profile_override,
            selected_camera_index=self.cfg.selected_camera_index,
            camera_picker_shown=self.cfg.camera_picker_shown,
        )
        save_config(self.cfg)
        self.sm.cfg = self.cfg
        self.alarm.set_sound(name)
        self.configChanged.emit()

    @Slot(str)
    def testAlarm(self, name: str) -> None:
        try:
            self.alarm.set_sound(name)
            ok = self.alarm.test()
            if ok:
                self._alarm_test_status = f"Playing: {name}"
            else:
                p = self.alarm._resolve(name)
                self._alarm_test_status = f"Failed: {name} not found" if not p else f"Played {name} (check volume/mute)"
            self.alarmTestStatusChanged.emit(self._alarm_test_status)
        except Exception as e:
            self._alarm_test_status = f"Error: {e}"
            self.alarmTestStatusChanged.emit(self._alarm_test_status)

    @Slot(bool)
    def setTtsEnabled(self, enabled: bool) -> None:
        self.cfg = AppConfig(
            bathroom_threshold_seconds=self.cfg.bathroom_threshold_seconds,
            water_threshold_seconds=self.cfg.water_threshold_seconds,
            admin_password_hash=self.cfg.admin_password_hash,
            salt=self.cfg.salt,
            selected_alarm_sound=self.cfg.selected_alarm_sound,
            tts_enabled=enabled,
            active_schedule_profile_override=self.cfg.active_schedule_profile_override,
            selected_camera_index=self.cfg.selected_camera_index,
            camera_picker_shown=self.cfg.camera_picker_shown,
        )
        save_config(self.cfg)
        self.sm.cfg = self.cfg
        self.configChanged.emit()

    @Slot(str, int)
    def adjustThreshold(self, pass_type: str, delta: int) -> None:
        if pass_type == "Bathroom":
            new_val = max(60, self.cfg.bathroom_threshold_seconds + delta)
            self.cfg = AppConfig(
                bathroom_threshold_seconds=new_val,
                water_threshold_seconds=self.cfg.water_threshold_seconds,
                admin_password_hash=self.cfg.admin_password_hash,
                salt=self.cfg.salt,
                selected_alarm_sound=self.cfg.selected_alarm_sound,
                tts_enabled=self.cfg.tts_enabled,
                active_schedule_profile_override=self.cfg.active_schedule_profile_override,
                selected_camera_index=self.cfg.selected_camera_index,
                camera_picker_shown=self.cfg.camera_picker_shown,
            )
        else:
            new_val = max(60, self.cfg.water_threshold_seconds + delta)
            self.cfg = AppConfig(
                bathroom_threshold_seconds=self.cfg.bathroom_threshold_seconds,
                water_threshold_seconds=new_val,
                admin_password_hash=self.cfg.admin_password_hash,
                salt=self.cfg.salt,
                selected_alarm_sound=self.cfg.selected_alarm_sound,
                tts_enabled=self.cfg.tts_enabled,
                active_schedule_profile_override=self.cfg.active_schedule_profile_override,
                selected_camera_index=self.cfg.selected_camera_index,
                camera_picker_shown=self.cfg.camera_picker_shown,
            )
        save_config(self.cfg)
        self.sm.cfg = self.cfg
        self.configChanged.emit()
        self.stateChanged.emit(self.sm.state.value)
        self.elapsedChanged.emit(self._elapsed)

    @Slot(str, result=str)
    def exportLogs(self, choice: str) -> str:
        try:
            dest = export_auto(choice)
            self._export_status = f"Exported to {dest}"
            self.exportStatusChanged.emit(self._export_status)
            return str(dest)
        except Exception as e:
            self._export_status = f"Export failed: {e}"
            self.exportStatusChanged.emit(self._export_status)
            return ""

    @Slot(str)
    def setActiveProfile(self, profile: str) -> None:
        # Legacy: profile may be Block_A_Schedule or A/B/Everyday
        # Map to override letter
        letter = profile
        if "Block_A" in profile or profile == "A":
            letter = "A"
        elif "Block_B" in profile or profile == "B":
            letter = "B"
        elif profile in ("Everyday", "A", "B"):
            letter = profile
        else:
            letter = "A"
        self.cfg = AppConfig(
            bathroom_threshold_seconds=self.cfg.bathroom_threshold_seconds,
            water_threshold_seconds=self.cfg.water_threshold_seconds,
            admin_password_hash=self.cfg.admin_password_hash,
            salt=self.cfg.salt,
            selected_alarm_sound=self.cfg.selected_alarm_sound,
            tts_enabled=self.cfg.tts_enabled,
            active_schedule_profile_override=letter,
            selected_camera_index=self.cfg.selected_camera_index,
            camera_picker_shown=self.cfg.camera_picker_shown,
        )
        save_config(self.cfg)
        self.sm.cfg = self.cfg
        self._profile = f"Block_{letter}_Schedule" if letter in ("A","B") else "Block_A_Schedule"
        self._resolve_block()
        self._update_roster_cache()
        self.activeProfileChanged.emit(self._profile)
        self.activeBlockChanged.emit(self._block_id)
        self.rosterChanged.emit()
        self.configChanged.emit()

    @Slot()
    def reloadSchedules(self) -> None:
        self._resolve_block()
        self._update_roster_cache()
        self.activeProfileChanged.emit(self._profile)
        self.activeBlockChanged.emit(self._block_id)
        self.rosterChanged.emit()
        self.scheduleChanged.emit()

    @Slot(str, str, str, str)
    def savePeriod(self, profile: str, block_id: str, start: str, end: str) -> None:
        # Legacy savePeriod -> map to updateBlock (ignore profile)
        try:
            flat = load_rosters_flat()
            target = block_id
            if target not in flat and target.replace("_", " ") in flat:
                target = target.replace("_", " ")
            # If block exists, update it preserving day_type
            data = load_schedules()
            for b in data.get("blocks", []):
                if b.get("name") == target:
                    self.updateBlock(target, target, start, end, b.get("day_type","Everyday"))
                    return
            # Otherwise add new
            self.addBlock(target, start, end, "Everyday")
        except Exception:
            pass

    @Slot(str, str)
    def setDayDefault(self, weekday: str, profile: str) -> None:
        try:
            letter = profile
            if "Block_A" in profile or profile == "A" or "A Day" in profile:
                letter = "A"
            elif "Block_B" in profile or profile == "B" or "B Day" in profile:
                letter = "B"
            elif profile == "Everyday":
                letter = "A"  # default
            data = load_schedules()
            data.setdefault("day_defaults", {})[weekday] = letter
            save_schedules(data)
            self.scheduleChanged.emit()
            self._resolve_block()
            self._update_roster_cache()
            self.activeBlockChanged.emit(self._block_id)
            self.rosterChanged.emit()
        except Exception:
            pass

    @Slot()
    def resetSchedules(self) -> None:
        from .schedules import default_schedules
        save_schedules(default_schedules())
        # Also reset rosters to default flat? Keep existing? Reset to default flat for clean state
        from .rosters import default_flat, save_flat
        save_flat(default_flat())
        self.scheduleChanged.emit()
        self._resolve_block()
        self._update_roster_cache()
        self.activeBlockChanged.emit(self._block_id)
        self.rosterChanged.emit()

    @Slot()
    def exitFullscreen(self) -> None:
        pass

    @Slot(result=bool)
    def verifyQuit(self) -> bool:
        if self.requireQuitAuth and not self._is_admin:
            return False
        return True

    # Internal
    def _tick(self) -> None:
        if self.sm.active:
            self._elapsed = int((__import__("datetime").datetime.now() - self.sm.active.time_out).total_seconds())
            self.sm.tick(self._elapsed)
            self.elapsedChanged.emit(self._elapsed)
            if self.sm.is_overtime():
                self.stateChanged.emit(State.OVERTIME.value)
            else:
                self.stateChanged.emit(self.sm.state.value)
        else:
            # Periodically re-resolve block in case time moved to new period
            old_block = self._block_id
            old_profile = self._profile
            self._resolve_block()
            if old_block != self._block_id or old_profile != self._profile:
                self._update_roster_cache()
                self.activeBlockChanged.emit(self._block_id)
                self.activeProfileChanged.emit(self._profile)
                self.rosterChanged.emit()

    def _on_tts(self, text: str) -> None:
        self.tts.speak(text)

    @Slot()
    def refreshHistory(self) -> None:
        self.historyChanged.emit()

    def _list_photos(self) -> list[dict]:
        import os, datetime
        from pathlib import Path
        try:
            pdir = photos_dir()
            if not pdir.exists():
                return []
            files = sorted(pdir.glob("*.jpg"), key=lambda x: x.stat().st_mtime, reverse=True)
            # Also include .jpeg, .png if any
            for ext in ["*.jpeg", "*.png", "*.JPG"]:
                files.extend(sorted(pdir.glob(ext), key=lambda x: x.stat().st_mtime, reverse=True))
            # Build recent 100
            out=[]
            # Build log lookup for photo path -> student/block
            log_map={}
            try:
                for rec in self.storage.get_logs():
                    if rec.photo_out_path:
                        log_map[rec.photo_out_path] = rec
                    if rec.photo_in_path:
                        log_map[rec.photo_in_path] = rec
            except Exception:
                pass
            for f in files[:100]:
                try:
                    st = f.stat()
                    mtime = st.st_mtime
                    dt = datetime.datetime.fromtimestamp(mtime)
                    datestr = dt.strftime("%m/%d %H:%M")
                    # Try to parse student from log
                    rec = log_map.get(str(f))
                    student = rec.student_name if rec else ""
                    block = rec.block_id if rec else ""
                    ptype = rec.pass_type.value if rec else ""
                    overtime = rec.overtime_status.value if rec else ""
                    out.append({
                        "path": str(f),
                        "file": f.name,
                        "url": f.as_uri(),
                        "size": st.st_size,
                        "mtime": mtime,
                        "date": datestr,
                        "student": student,
                        "block": block,
                        "passType": ptype,
                        "overtime": overtime,
                    })
                except Exception:
                    continue
            return out
        except Exception:
            return []

    def _purge_old_photos_internal(self, days: int = 7) -> int:
        import time, os
        from pathlib import Path
        try:
            pdir = photos_dir()
            if not pdir.exists():
                return 0
            cutoff = time.time() - days*24*60*60
            removed=0
            for f in pdir.glob("*.*"):
                try:
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        # Only purge image files
                        if f.suffix.lower() in [".jpg",".jpeg",".png"]:
                            f.unlink()
                            removed+=1
                except Exception:
                    continue
            if removed:
                self._photos_status = f"Auto-deleted {removed} photos older than {days} days"
                self.photosChanged.emit()
            return removed
        except Exception as e:
            self._photos_status = f"Purge failed: {e}"
            self.photosChanged.emit()
            return 0

    @Slot(result=str)
    def testCameraCapture(self) -> str:
        try:
            p = self.camera.capture("test", student="Test", block=self._block_id)
            self._photos_status = f"Test capture: {p}"
            self.photosChanged.emit()
            return p
        except Exception as e:
            self._photos_status = f"Camera test failed: {e}"
            self.photosChanged.emit()
            return ""

    @Slot(result=bool)
    def refreshPhotos(self) -> bool:
        try:
            self.photosChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, result=int)
    def purgeOldPhotos(self, days: int = 7) -> int:
        n = self._purge_old_photos_internal(days=days)
        if n==0:
            self._photos_status = f"No photos older than {days} days"
        else:
            self._photos_status = f"Deleted {n} photos older than {days} days"
        self.photosChanged.emit()
        return n

    @Slot(str, result=bool)
    def deletePhoto(self, path: str) -> bool:
        try:
            from pathlib import Path
            # Handle file:// url
            if path.startswith("file://"):
                path = QUrl(path).toLocalFile()
            p = Path(path)
            # Safety: ensure inside photos_dir
            try:
                p.resolve().relative_to(photos_dir().resolve())
            except Exception:
                # Allow if it's exact file in photos dir
                if p.parent.resolve() != photos_dir().resolve() and p.parent != photos_dir():
                    self._photos_status = "Delete failed: outside photos folder"
                    self.photosChanged.emit()
                    return False
            if p.exists() and p.is_file():
                p.unlink()
                self._photos_status = f"Deleted {p.name}"
                self.photosChanged.emit()
                return True
            else:
                self._photos_status = "File not found"
                self.photosChanged.emit()
                return False
        except Exception as e:
            self._photos_status = f"Delete failed: {e}"
            self.photosChanged.emit()
            return False

    @Slot(result=str)
    def openCameraSettings(self) -> str:
        try:
            import subprocess, sys
            # Open Privacy & Security > Camera on macOS
            if sys.platform == "darwin":
                subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"])
            self._photos_status = "Opened System Settings → Privacy → Camera — enable Terminal/OpenCode, then relaunch"
            self.photosChanged.emit()
            return "opened"
        except Exception as e:
            self._photos_status = f"Open Settings failed: {e}"
            self.photosChanged.emit()
            return ""

    @Slot(result=str)
    def revealPhotosFolder(self) -> str:
        try:
            import subprocess, sys
            folder = str(photos_dir())
            # On macOS open folder, on Linux xdg-open
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                elif sys.platform.startswith("linux"):
                    subprocess.Popen(["xdg-open", folder])
                else:
                    subprocess.Popen(["explorer", folder])
            except Exception:
                pass
            self._photos_status = f"Folder: {folder}"
            self.photosChanged.emit()
            return folder
        except Exception as e:
            return str(photos_dir())

    def _on_state_changed(self, s: State) -> None:
        self.stateChanged.emit(s.value)
