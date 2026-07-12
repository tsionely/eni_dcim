"""Run a single supervised flight against the real sim (Windows machine).

    python scripts/fly_once.py [--max-duration 60]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.main import main

if __name__ == "__main__":
    sys.exit(main(["--mode", "fly"] + sys.argv[1:]))
