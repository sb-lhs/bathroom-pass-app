import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hallpass.config import AppConfig
from hallpass.storage import Storage, PassType
from hallpass.state_machine import PassStateMachine, State

def test_full_flow_idle_active_return_idle():
    import datetime as dt
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)/"logs.db"
        csv = Path(tmp)/"pass_history.csv"
        s = Storage(db=db, csv=csv)
        cfg = AppConfig(bathroom_threshold_seconds=420, water_threshold_seconds=180, tts_enabled=False)
        sm = PassStateMachine(cfg, s, lambda: "Block_1")
        assert sm.state == State.IDLE
        assert sm.select_student("Alex Johnson", PassType.Bathroom, "/tmp/out.jpg")
        assert sm.state == State.ACTIVE
        sm.tick(10)
        assert sm.state == State.ACTIVE
        sm.tick(500)
        assert sm.state == State.OVERTIME
        sm.mute_alarm()
        assert sm.active.muted is True
        # Backdate time_out to simulate 500s elapsed for real overtime calc (return_pass uses wall clock)
        assert sm.active is not None
        sm.active.time_out = dt.datetime.now() - dt.timedelta(seconds=500)
        rec = sm.return_pass("/tmp/in.jpg")
        assert rec is not None
        assert rec.overtime_status.value == "OVERTIME"
        assert sm.state == State.IDLE

def test_queue_advance_and_tts():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)/"logs.db"
        csv = Path(tmp)/"pass_history.csv"
        s = Storage(db=db, csv=csv)
        cfg = AppConfig(bathroom_threshold_seconds=420, water_threshold_seconds=180, tts_enabled=True)
        sm = PassStateMachine(cfg, s, lambda: "Block_1")
        tts_calls=[]
        sm.on_tts = lambda txt: tts_calls.append(txt)
        sm.select_student("Alex Johnson", PassType.Water, "/tmp/out.jpg")
        sm.enqueue("Sam Rivera", PassType.Bathroom)
        assert len(sm.queue)==1
        sm.return_pass("/tmp/in.jpg")
        # Should advance to Sam Rivera
        assert sm.active is not None
        assert sm.active.student_name == "Sam Rivera"
        assert len(tts_calls)==1
        assert "Sam Rivera" in tts_calls[0]

def test_water_vs_bathroom_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)/"logs.db"
        csv = Path(tmp)/"pass_history.csv"
        s = Storage(db=db, csv=csv)
        cfg = AppConfig(bathroom_threshold_seconds=420, water_threshold_seconds=180)
        sm = PassStateMachine(cfg, s, lambda: "Block_1")
        sm.select_student("A", PassType.Water, "/tmp/out.jpg")
        sm.tick(190)
        assert sm.state == State.OVERTIME
        sm.return_pass("/tmp/in.jpg")
        sm.select_student("B", PassType.Bathroom, "/tmp/out2.jpg")
        sm.tick(190)
        assert sm.state == State.ACTIVE  # bathroom not overtime at 190
