import tempfile
from pathlib import Path
import sys, os
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def _isolate(tmp):
    os.environ["HALLPASS_CONFIG"] = str(Path(tmp) / "config.json")
    os.environ["HALLPASS_DATA_DIR"] = tmp

def test_overlap_returns_both_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass import schedules as S
        S.save_schedules({
            "blocks": S.default_blocks(),
            "templates": {"Regular": [
                {"name": "", "start": "08:00", "end": "10:00"},
                {"name": "Late Lab", "start": "09:00", "end": "11:00"},
            ]},
            "weekday_templates": {w: "Regular" for w in S.WEEKDAYS},
            "weekday_letters": {w: "Everyday" for w in S.WEEKDAYS},
        })
        prof, hits = S.active_blocks(datetime(2026, 9, 23, 9, 30))
        assert hits == ["Block 1", "Late Lab"], hits
        prof1, one = S.active_block(datetime(2026, 9, 23, 9, 30))
        assert one == "Block 1"
        assert S.active_blocks(datetime(2026, 9, 23, 7, 0))[1] == []

def test_overlap_roster_union():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass import schedules as S
        from hallpass import rosters as R
        from hallpass.backend import Backend
        S.save_schedules({
            "blocks": S.default_blocks(),
            "templates": {"Regular": [
                {"name": "", "start": "08:00", "end": "10:00"},
                {"name": "Late Lab", "start": "09:00", "end": "11:00"},
            ]},
            "weekday_templates": {w: "Regular" for w in S.WEEKDAYS},
            "weekday_letters": {w: "Everyday" for w in S.WEEKDAYS},
        })
        R.save_rosters({
            "Block 1": {"Everyday": ["Amy"], "A": [], "B": []},
            "Late Lab": {"Everyday": ["Zoe"], "A": [], "B": []},
        })
        b = Backend.__new__(Backend)
        from hallpass.config import load_config
        b.cfg = load_config()
        b._block_id = ""
        b._active_blocks = ["Block 1", "Late Lab"]
        b._update_roster_cache()
        assert b._roster_cache == ["Amy", "Zoe"], b._roster_cache

def test_time_parse_and_format():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.schedules import parse_time_input, format_12h
        assert parse_time_input("8:30 AM") == "08:30"
        assert parse_time_input("1:30 pm") == "13:30"
        assert parse_time_input("13:30") == "13:30"
        assert parse_time_input("8") == "08:00"
        assert parse_time_input("12am") == "00:00"
        assert parse_time_input("12pm") == "12:00"
        assert parse_time_input("xyz") == ""
        assert format_12h("08:00") == "8:00 AM"
        assert format_12h("13:30") == "1:30 PM"
        assert format_12h("00:00") == "12:00 AM"

def test_flip_weekday_letters():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass import schedules as S
        S.save_schedules({
            "blocks": S.default_blocks(),
            "templates": {"Regular": S.default_blocks()},
            "weekday_templates": {w: "Regular" for w in S.WEEKDAYS},
            "weekday_letters": {"Monday": "A", "Tuesday": "B", "Wednesday": "Everyday", "Thursday": "A", "Friday": "B", "Saturday": "Everyday", "Sunday": "Everyday"},
        })
        assert S.flip_weekday_letters() == 4
        after = S.load_schedules()["weekday_letters"]
        assert after["Monday"] == "B" and after["Tuesday"] == "A"
        assert after["Wednesday"] == "Everyday"
        assert S.flip_weekday_letters() == 4
        back = S.load_schedules()["weekday_letters"]
        assert back["Monday"] == "A" and back["Tuesday"] == "B"

def test_flip_all_everyday_noop():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass import schedules as S
        S.save_schedules({
            "blocks": S.default_blocks(),
            "templates": {"Regular": S.default_blocks()},
            "weekday_templates": {w: "Regular" for w in S.WEEKDAYS},
            "weekday_letters": {w: "Everyday" for w in S.WEEKDAYS},
        })
        assert S.flip_weekday_letters() == 0

def test_roster_rename():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.rosters import create_block_roster, load_rosters_structured, rename_block_roster, set_roster_for_block_variant
        assert create_block_roster("Chem Lab") is True
        set_roster_for_block_variant("Chem Lab", "A", ["Zoe"])
        rename_block_roster("Chem Lab", "Physics Lab")
        s = load_rosters_structured()
        assert "Chem Lab" not in s
        assert s["Physics Lab"]["A"] == ["Zoe"]

def test_roster_create_delete():
    with tempfile.TemporaryDirectory() as tmp:
        _isolate(tmp)
        from hallpass.rosters import create_block_roster, delete_block_roster, load_rosters_structured, set_roster_for_block_variant
        assert create_block_roster("Chem Lab") is True
        assert create_block_roster("Chem Lab") is False
        assert create_block_roster("  ") is False
        set_roster_for_block_variant("Chem Lab", "A", ["Zoe"])
        assert "Chem Lab" in load_rosters_structured()
        delete_block_roster("Chem Lab")
        assert "Chem Lab" not in load_rosters_structured()
