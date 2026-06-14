import sys
from pathlib import Path

APPS_DIR = Path(__file__).resolve().parents[1] / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

