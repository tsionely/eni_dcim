"""Run an unattended flight-to-flight tuning campaign.

    python scripts/run_campaign.py --flights 20 --optimizer cem --sim mock
    python scripts/run_campaign.py --flights 20 --optimizer cem --sim real
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aigp.main import main

if __name__ == "__main__":
    sys.exit(main(["--mode", "campaign"] + sys.argv[1:]))
