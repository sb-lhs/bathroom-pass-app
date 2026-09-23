import tempfile, json
from pathlib import Path
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _fixture():
    return {
        "school": "Fixture High",
        "slug": "fixture-high",
        "location": "Town, ST",
        "contributor": "Tester",
        "version": 1,
        "templates": {
            "Regular": [
                {"start": "08:00", "end": "09:20", "name": "Block 1"},
                {"start": "09:25", "end": "10:45", "name": "Block 2"},
            ],
            "Late Start": [
                {"start": "09:50", "end": "10:50", "name": "Block 1"},
                {"start": "10:55", "end": "11:55", "name": "Block 2"},
            ],
        },
        "weekday_templates": {"Monday": "Regular", "Wednesday": "Late Start"},
        "weekday_letters": {"Monday": "A"},
    }


def _write_preset(tmpdir, data):
    from hallpass.schedules import _user_schools_dir
    d = _user_schools_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{data['slug']}.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_fixture_validates():
    from hallpass.schedules import validate_school_preset
    assert validate_school_preset(_fixture()) == []


def test_validate_rejects_bad():
    from hallpass.schedules import validate_school_preset
    import copy
    bad = copy.deepcopy(_fixture())
    bad["templates"]["Regular"][0]["start"] = "25:00"
    assert validate_school_preset(bad) != []
    bad2 = copy.deepcopy(_fixture())
    bad2["weekday_templates"] = {"Funday": "Regular"}
    assert validate_school_preset(bad2) != []
    bad3 = copy.deepcopy(_fixture())
    bad3["weekday_letters"] = {"Monday": "C"}
    assert validate_school_preset(bad3) != []
    bad4 = {"school": "X"}
    assert validate_school_preset(bad4) != []


def test_apply_merge_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HALLPASS_CONFIG"] = str(Path(tmp) / "config.json")
        os.environ["HALLPASS_DATA_DIR"] = tmp
        from hallpass.schedules import apply_school_preset, get_templates
        _write_preset(tmp, _fixture())
        first = apply_school_preset("fixture-high")
        assert len(first["added"]) == 2 and first["skipped"] == []
        assert "Late Start" in get_templates()
        second = apply_school_preset("fixture-high")
        assert second["added"] == [] and len(second["skipped"]) == 2


def test_apply_collision_renames():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HALLPASS_CONFIG"] = str(Path(tmp) / "config.json")
        os.environ["HALLPASS_DATA_DIR"] = tmp
        from hallpass.schedules import apply_school_preset, get_templates, set_templates
        _write_preset(tmp, _fixture())
        t = get_templates()
        t["Regular"] = [{"start": "08:00", "end": "09:00", "name": ""}]
        set_templates(t)
        result = apply_school_preset("fixture-high")
        assert "Fixture High — Regular" in result["added"]
        assert "Fixture High — Regular" in get_templates()


def test_apply_weekdays():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HALLPASS_CONFIG"] = str(Path(tmp) / "config.json")
        os.environ["HALLPASS_DATA_DIR"] = tmp
        from hallpass.schedules import apply_school_preset, apply_school_preset_weekdays, get_weekday_templates, get_weekday_letters
        _write_preset(tmp, _fixture())
        apply_school_preset("fixture-high")
        assert apply_school_preset_weekdays("fixture-high") is True
        assert get_weekday_templates()["Wednesday"] == "Late Start"
        assert get_weekday_letters()["Monday"] == "A"
        assert apply_school_preset_weekdays("no-such-school") is False


def test_export_import_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HALLPASS_CONFIG"] = str(Path(tmp) / "config.json")
        os.environ["HALLPASS_DATA_DIR"] = tmp
        from hallpass.schedules import export_school_preset, import_school_preset_file, list_school_presets, validate_school_preset
        result = export_school_preset("Roundtrip High", "roundtrip-high", "Town, ST", "Tester")
        assert result["ok"] is True
        assert validate_school_preset(result["preset"]) == []
        src = Path(tmp) / "roundtrip-high.json"
        src.write_text(json.dumps(result["preset"], indent=2), encoding="utf-8")
        imported = import_school_preset_file(src)
        assert imported == {"ok": True, "slug": "roundtrip-high"}
        slugs = [p["slug"] for p in list_school_presets()]
        assert "roundtrip-high" in slugs
