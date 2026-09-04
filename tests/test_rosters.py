import tempfile, json
from pathlib import Path
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_non_destructive_merge():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HALLPASS_CONFIG"] = str(Path(tmp)/"config.json")
        os.environ["HALLPASS_DATA_DIR"] = tmp
        from hallpass.rosters import load_rosters, save_rosters, merge_roster_csv, load_rosters_nested
        from hallpass.config import rosters_path
        # Ensure fresh
        save_rosters({"Block_1": ["Alex Johnson"]})
        # Create CSV with one new + one existing
        csv_path = Path(tmp)/"import.csv"
        csv_path.write_text("Student Name,Block ID\nSam Rivera,Block_1\nAlex Johnson,Block_1\n", encoding="utf-8")
        merged = merge_roster_csv(csv_path)
        # merged is structured: Block_1 -> {Everyday, A, B} or legacy nested/flat
        if "Block_A_Schedule" in merged:
            block = merged.get("Block_A_Schedule", {}).get("Block_1", [])
        else:
            val = merged.get("Block_1", [])
            block = val.get("Everyday", []) if isinstance(val, dict) else val
        assert "Sam Rivera" in block
        assert block.count("Alex Johnson")==1
        assert "Alex Johnson" in block

def test_headerless_csv():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HALLPASS_CONFIG"] = str(Path(tmp)/"config2.json")
        from hallpass.rosters import save_rosters, merge_roster_csv
        save_rosters({"Block_1": []})
        csv_path = Path(tmp)/"import2.csv"
        csv_path.write_text("Jordan Lee,Block_1\n", encoding="utf-8")
        merged = merge_roster_csv(csv_path)
        if "Block_A_Schedule" in merged:
            block = merged.get("Block_A_Schedule", {}).get("Block_1", [])
        else:
            val = merged.get("Block_1", [])
            block = val.get("Everyday", []) if isinstance(val, dict) else val
        assert "Jordan Lee" in block
