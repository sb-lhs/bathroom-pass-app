import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hallpass.updater import _version_tuple, is_newer


def test_version_tuple():
    assert _version_tuple("0.3.6") == (0, 3, 6, 0)
    assert _version_tuple("v0.3.6") == (0, 3, 6, 0)
    assert _version_tuple("1.10.2") == (1, 10, 2, 0)
    assert _version_tuple("2") == (2, 0, 0, 0)


def test_is_newer():
    assert is_newer("0.3.7", "0.3.6") is True
    assert is_newer("v0.3.7", "0.3.6") is True
    assert is_newer("0.3.6", "0.3.6") is False
    assert is_newer("0.3.5", "0.3.6") is False
    assert is_newer("0.4.0", "0.3.9") is True
    assert is_newer("1.0.0", "0.9.9") is True
