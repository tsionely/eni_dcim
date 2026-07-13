"""Full MAVLink census on the legacy channel (run on the Windows machine).

Binds udp:14550 and, for --duration seconds, records EVERY message type it
sees — including types the pilot does not parse — with per-(type, source)
rates and per-field value liveness. Start a race mid-run: if live vehicle
telemetry hides in a message type or source we ignore, this finds it.

    python scripts/mavlink_census.py --duration 60

Also breaks ENCAPSULATED_DATA down by its embedded data_type id.
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pymavlink import mavutil

NUMERIC = (int, float)


def main() -> int:
    parser = argparse.ArgumentParser(description="MAVLink message census")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=14550)
    args = parser.parse_args()

    conn = mavutil.mavlink_connection(f"udpin:{args.ip}:{args.port}")
    print(f"waiting for heartbeat on {args.ip}:{args.port}...", flush=True)
    if conn.wait_heartbeat(timeout=20) is None:
        print("no heartbeat", file=sys.stderr)
        return 1
    print(f"census for {args.duration:.0f}s — start the race while this runs...",
          flush=True)

    counts: dict[tuple, int] = defaultdict(int)              # (type, sys, comp)
    fields: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    encap_types: dict[int, int] = defaultdict(int)

    t_start = time.monotonic()
    t_end = t_start + args.duration
    next_progress = t_start + 10.0
    while time.monotonic() < t_end:
        msg = conn.recv_match(blocking=True, timeout=0.2)
        if msg is None:
            continue
        mtype = msg.get_type()
        if mtype == "BAD_DATA":
            continue
        key = (mtype, msg.get_srcSystem(), msg.get_srcComponent())
        counts[key] += 1
        store = fields[key]
        for name in msg.get_fieldnames():
            val = getattr(msg, name)
            if isinstance(val, NUMERIC) and len(store[name]) < 5000:
                store[name].append(float(val))
        if mtype == "ENCAPSULATED_DATA":
            raw = bytes(msg.data)
            if raw:
                encap_types[raw[0]] += 1
        if time.monotonic() >= next_progress:
            next_progress += 10.0
            print(f"  ...{time.monotonic() - t_start:4.0f}s  "
                  f"{sum(counts.values())} msgs, {len(counts)} (type,src) pairs",
                  flush=True)

    window = time.monotonic() - t_start
    print(f"\n=== census over {window:.1f}s ===", flush=True)
    for key in sorted(counts, key=lambda k: -counts[k]):
        mtype, src_sys, src_comp = key
        n = counts[key]
        live_fields = []
        frozen_fields = []
        nan_fields = []
        for name, vals in fields[key].items():
            finite = [v for v in vals if math.isfinite(v)]
            if len(finite) < len(vals):
                nan_fields.append(name)
                continue
            if len(finite) < 10:
                continue
            (live_fields if statistics.pstdev(finite) > 1e-5 else frozen_fields).append(name)
        print(f"{mtype:32s} src=({src_sys},{src_comp})  {n:6d}  {n / window:7.1f} Hz",
              flush=True)
        if live_fields:
            print(f"    LIVE fields:   {', '.join(sorted(live_fields))}", flush=True)
        if frozen_fields:
            print(f"    frozen fields: {', '.join(sorted(frozen_fields))}", flush=True)
        if nan_fields:
            print(f"    nan/inf:       {', '.join(sorted(nan_fields))}", flush=True)
    if encap_types:
        print(f"\nENCAPSULATED_DATA payload type ids: "
              f"{dict(sorted(encap_types.items()))}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
