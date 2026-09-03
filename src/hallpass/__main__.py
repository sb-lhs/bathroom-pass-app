from .__init__ import __version__
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import main
if __name__ == "__main__":
    raise SystemExit(main())
