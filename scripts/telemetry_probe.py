"""T0 — inventory the telemetry a running sim actually sends.

Connects to the sim's MAVLink stream and, for a fixed window, counts every
message type, measures its rate, and records one full sample payload per
type. Run against the VQ1 (telemetry-enabled) sim first; the diff of its
output against a VQ2 run IS the telemetry interface — the truth channels
the VQ1 pivot builds on.

No commands are sent. Read-only: safe to run any time the sim is up
(main menu or in-race; in-race shows the full stream).

Usage (repo venv only):
  .venv\\Scripts\\python.exe scripts\\telemetry_probe.py [seconds] [udp:host:port]
Defaults: 30 seconds, udp:0.0.0.0:14550.

Output: telemetry_probe_<stamp>.json next to the repo root (commit it),
plus a human table on stdout.
"""
import json
import sys
import time
from pathlib import Path

from pymavlink import mavutil

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    endpoint = sys.argv[2] if len(sys.argv) > 2 else "udp:0.0.0.0:14550"

    print(f"listening on {endpoint} for {seconds:.0f}s ...", flush=True)
    conn = mavutil.mavlink_connection(endpoint)

    counts: dict[str, int] = {}
    samples: dict[str, dict] = {}
    first_ts: dict[str, float] = {}
    last_ts: dict[str, float] = {}

    t0 = time.monotonic()
    while time.monotonic() - t0 < seconds:
        msg = conn.recv_match(blocking=True, timeout=1.0)
        if msg is None:
            continue
        mtype = msg.get_type()
        if mtype == "BAD_DATA":
            continue
        now = time.monotonic()
        counts[mtype] = counts.get(mtype, 0) + 1
        first_ts.setdefault(mtype, now)
        last_ts[mtype] = now
        if mtype not in samples:
            try:
                samples[mtype] = msg.to_dict()
            except Exception:
                samples[mtype] = {"repr": repr(msg)}

    rows = []
    for mtype in sorted(counts, key=lambda k: -counts[k]):
        span = max(last_ts[mtype] - first_ts[mtype], 1e-9)
        rate = (counts[mtype] - 1) / span if counts[mtype] > 1 else 0.0
        rows.append({"type": mtype, "count": counts[mtype],
                     "rate_hz": round(rate, 2), "sample": samples[mtype]})

    stamp = time.strftime("%Y%m%dT%H%M%S")
    out = ROOT / f"telemetry_probe_{stamp}.json"
    out.write_text(json.dumps(
        {"endpoint": endpoint, "seconds": seconds, "messages": rows},
        indent=1), encoding="utf-8")

    print(f"\n{'TYPE':34s} {'COUNT':>7s} {'RATE_HZ':>8s}")
    for r in rows:
        print(f"{r['type']:34s} {r['count']:7d} {r['rate_hz']:8.2f}")
    print(f"\n{len(rows)} message types; full samples in {out.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
