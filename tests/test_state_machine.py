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

def _machine(tmp, **cfg_kw):
    from pathlib import Path as _P
    db = _P(tmp)/"logs.db"
    csv = _P(tmp)/"pass_history.csv"
    s = Storage(db=db, csv=csv)
    kw = {"bathroom_threshold_seconds": 420, "water_threshold_seconds": 180, "tts_enabled": False}
    kw.update(cfg_kw)
    cfg = AppConfig(**kw)
    return PassStateMachine(cfg, s, lambda: "Block_1")

def test_headcount_cap_and_shared_queue():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sm = _machine(tmp, pass_mode="headcount", max_concurrent=2)
        assert sm.select_student("A", PassType.Bathroom, "")
        assert sm.select_student("B", PassType.Bathroom, "")
        assert sm.select_student("C", PassType.Bathroom, "") == ""
        assert len(sm.active_passes()) == 2
        assert sm.enqueue("C", PassType.Bathroom) is True
        assert len(sm.queue) == 1
        rec = sm.return_pass("", key="pool:0")
        assert rec is not None and rec.slot == ""
        names = sorted(a.student_name for a in sm.active_passes())
        assert names == ["B", "C"]

def test_slots_isolation_and_per_slot_queue():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sm = _machine(tmp, pass_mode="slots", pass_slots=["Boys pass", "Girls pass"])
        k1 = sm.select_student("A", PassType.Bathroom, "", slot="Boys pass")
        assert k1 == "Boys pass"
        assert sm.select_student("B", PassType.Bathroom, "", slot="Boys pass") == ""
        k2 = sm.select_student("C", PassType.Water, "", slot="Girls pass")
        assert k2 == "Girls pass"
        assert sm.enqueue("D", PassType.Bathroom, slot="Boys pass") is True
        assert sm.enqueue("E", PassType.Bathroom) is False
        rec = sm.return_pass("", key="Boys pass")
        assert rec is not None and rec.slot == "Boys pass"
        assert sm.actives["Boys pass"].student_name == "D"
        assert sm.actives["Girls pass"].student_name == "C"

def test_shared_alarm_edge_and_mute_all():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sm = _machine(tmp, pass_mode="headcount", max_concurrent=2, bathroom_threshold_seconds=60)
        starts = []
        stops = []
        sm.on_alarm_start = lambda: starts.append(1)
        sm.on_alarm_stop = lambda: stops.append(1)
        sm.select_student("A", PassType.Bathroom, "")
        sm.select_student("B", PassType.Bathroom, "")
        sm.tick()
        assert sm.state == State.ACTIVE and starts == []
        import datetime as dt
        for a in sm.active_passes():
            a.time_out = dt.datetime.now() - dt.timedelta(seconds=120)
        sm.tick()
        assert sm.state == State.OVERTIME and starts == [1]
        sm.mute_alarm()
        assert stops == [1]
        assert all(a.muted for a in sm.active_passes())

def test_simple_mode_single_pass():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        sm = _machine(tmp, pass_mode="simple", max_concurrent=5)
        assert sm.select_student("A", PassType.Bathroom, "")
        assert sm.select_student("B", PassType.Bathroom, "") == ""
        assert len(sm.active_passes()) == 1
        assert sm.enqueue("B", PassType.Bathroom) is True
        rec = sm.return_pass("")
        assert rec is not None
        assert sm.actives["pool:0"].student_name == "B"

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
