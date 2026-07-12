"""Render the standard post-flight figure for a flight log directory.

    python scripts/plot_flight.py logs/<flight_id>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.telemetry.plots import plot_flight


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: plot_flight.py <flight log dir>", file=sys.stderr)
        return 2
    flight_dir = Path(sys.argv[1])
    out = flight_dir / "flight.png"
    plot_flight(flight_dir / "flight.jsonl", out)
    print(f"Wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
