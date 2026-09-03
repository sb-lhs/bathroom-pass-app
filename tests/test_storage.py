import tempfile
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hallpass.storage import Storage, PassRecord, PassType, OvertimeStatus, calculate_overtime

def test_overtime_bathroom():
    assert calculate_overtime(500, PassType.Bathroom, 420, 180) == OvertimeStatus.OVERTIME
    assert calculate_overtime(100, PassType.Bathroom, 420, 180) == OvertimeStatus.NOT_OVER

def test_overtime_water():
    assert calculate_overtime(200, PassType.Water, 420, 180) == OvertimeStatus.OVERTIME
    assert calculate_overtime(100, PassType.Water, 420, 180) == OvertimeStatus.NOT_OVER

def test_append_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)/"logs.db"
        csv = Path(tmp)/"pass_history.csv"
        s = Storage(db=db, csv=csv)
        rec = PassRecord(
            student_name="Alex Johnson",
            block_id="Block_1",
            pass_type=PassType.Water,
            time_out=datetime(2026,9,2,9,10,5),
            time_in=datetime(2026,9,2,9,12,20),
            duration_minutes=2.25,
            overtime_status=OvertimeStatus.NOT_OVER,
            photo_out_path="/tmp/out.jpg",
            photo_in_path="/tmp/in.jpg"
        )
        s.append_log(rec)
        logs = s.get_logs()
        assert len(logs)==1
        assert logs[0].student_name=="Alex Johnson"
        assert csv.exists()
        assert "Alex Johnson" in csv.read_text()

def test_dual_type_threshold_distinct():
    assert calculate_overtime(250, PassType.Bathroom, 420, 180) == OvertimeStatus.NOT_OVER
    assert calculate_overtime(250, PassType.Water, 420, 180) == OvertimeStatus.OVERTIME
