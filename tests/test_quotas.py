import tempfile
from pathlib import Path
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def _isolate(tmp):
    os.environ["HALLPASS_CONFIG"] = str(Path(tmp) / "config.json")
    os.environ["HALLPASS_DATA_DIR"] = tmp
    for f in ["quota_grants.json"]:
        p = Path(tmp) / f
        if p.exists():
            p.unlink()

def _mklog(storage, student, ptype="Bathroom", block="Block 1", day=None, status="NOT OVER"):
    from hallpass.storage import PassRecord, PassType, OvertimeStatus
    now = datetime.now() if day is None else datetime.strptime(day, "%Y-%m-%d").replace(hour=9)
    storage.append_log(PassRecord(
        student_name=student, block_id=block,
        pass_type=PassType.Water if ptype == "Water" else PassType.Bathroom,
        time_out=now, time_in=now + timedelta(minutes=3),
        duration_minutes=3.0,
        overtime_status=OvertimeStatus.CANCELLED if status == "CANCELLED" else OvertimeStatus.NOT_OVER,
        photo_out_path="", photo_in_path="",
    ))

def test_daily_cap_trips():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.config import AppConfig
        from hallpass.storage import Storage
        from hallpass.quotas import check_quota
        s = Storage(db=Path(tmp)/"logs.db", csv=Path(tmp)/"pass_history.csv")
        cfg = AppConfig(quota_daily_bathroom=2)
        _mklog(s, "Amy"); _mklog(s, "Amy")
        r = check_quota(s, cfg, "Amy", "Bathroom", "Block 1")
        assert r["allowed"] is False and "daily 2/2" in r["reason"]
        r2 = check_quota(s, cfg, "Amy", "Water", "Block 1")
        assert r2["allowed"] is True

def test_block_cap_and_next_block_ok():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.config import AppConfig
        from hallpass.storage import Storage
        from hallpass.quotas import check_quota
        s = Storage(db=Path(tmp)/"logs.db", csv=Path(tmp)/"pass_history.csv")
        cfg = AppConfig(quota_per_block=1)
        _mklog(s, "Amy", block="Block 1")
        r = check_quota(s, cfg, "Amy", "Bathroom", "Block 1")
        assert r["allowed"] is False and "block 1/1" in r["reason"]
        assert check_quota(s, cfg, "Amy", "Bathroom", "Block 2")["allowed"] is True

def test_cancelled_and_denied_dont_consume():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.config import AppConfig
        from hallpass.storage import Storage
        from hallpass.quotas import check_quota
        s = Storage(db=Path(tmp)/"logs.db", csv=Path(tmp)/"pass_history.csv")
        cfg = AppConfig(quota_daily_bathroom=1)
        _mklog(s, "Amy", status="CANCELLED")
        assert check_quota(s, cfg, "Amy", "Bathroom", "Block 1")["allowed"] is True
        s.log_denied("Amy", "Block 1", "Bathroom", "", "daily 0/1")
        assert check_quota(s, cfg, "Amy", "Bathroom", "Block 1")["allowed"] is True
        assert len(s.get_denials()) == 1

def test_per_student_beats_global_and_grant_single_use():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.config import AppConfig
        from hallpass.storage import Storage
        from hallpass.quotas import check_quota, grant_override
        s = Storage(db=Path(tmp)/"logs.db", csv=Path(tmp)/"pass_history.csv")
        cfg = AppConfig(quota_daily_bathroom=1, quota_overrides={"Amy": {"daily_bathroom": 3, "daily_water": 0, "per_block": 0}})
        _mklog(s, "Amy"); _mklog(s, "Amy")
        assert check_quota(s, cfg, "Amy", "Bathroom", "Block 1")["allowed"] is True
        _mklog(s, "Amy")
        assert check_quota(s, cfg, "Amy", "Bathroom", "Block 1")["allowed"] is False
        assert grant_override("Amy") is True
        r = check_quota(s, cfg, "Amy", "Bathroom", "Block 1")
        assert r["allowed"] is True and r["override"] is True
        assert check_quota(s, cfg, "Amy", "Bathroom", "Block 1")["allowed"] is False

def test_backend_void_requires_password():
    import os as _os
    _os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from PySide6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication([])
        from hallpass.backend import Backend
        from hallpass.storage import PassType
        b = Backend()
        assert b.setInitialPassword("secret123", "secret123") is True
        b.selectStudent("Amy", "Bathroom")
        assert len(b.activePasses) == 1
        assert b.voidActivePass("pool:0", "wrong") is False
        assert len(b.activePasses) == 1
        assert b.voidActivePass("pool:0", "secret123") is True
        assert len(b.activePasses) == 0
        logs = b.storage.get_logs()
        assert logs[-1].overtime_status.value == "CANCELLED"
