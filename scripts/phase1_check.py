"""Phase-1 connectivity check against the real sim (run on the Windows machine).

Passive diagnostic — connects and LISTENS ONLY (never arms, never commands):

1. waits for the sim heartbeat
2. collects telemetry + camera frames for --duration seconds
3. records the raw vision stream to recordings/phase1-<ts>.aigprec
4. prints a report and a PASS/FAIL verdict against the Phase-1 acceptance
   criteria (docs/05): telemetry + frames flowing for the full window,
   TIMESYNC offset std < 5ms, non-empty recording.

    python scripts/phase1_check.py --duration 60

Exit code 0 = all criteria met.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.app import SimConfig
from aigp.core.bus import Bus
from aigp.core.clock import SimClock
from aigp.core.messages import Topic
from aigp.io.mavlink_io import MavlinkIO
from aigp.io.timesync import TimeSyncTX
from aigp.io.udp_tap import STREAM_VISION, DatagramRecorder
from aigp.io.vision_rx import VisionRX

OFFSET_STD_LIMIT_MS = 5.0


def _max_axis_std(samples: list[list[float]]) -> float:
    """Max standard deviation across IMU components, ignoring nan/inf."""
    import math
    import statistics
    if len(samples) < 6:
        return 0.0
    best = 0.0
    for axis in range(len(samples[0])):
        vals = [s[axis] for s in samples if math.isfinite(s[axis])]
        if len(vals) >= 6:
            best = max(best, statistics.pstdev(vals))
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 passive connectivity check")
    parser.add_argument("--config", default="config/sim.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--out", default=None, help="recording path (.aigprec)")
    parser.add_argument("--record-cap-mb", type=float, default=200.0,
                        help="stop recording after this many MB (race vision "
                             "is ~20 MB/s); 0 = unlimited")
    args = parser.parse_args()

    cfg = SimConfig.load(args.config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = Path(args.out or f"recordings/phase1-{stamp}.aigprec")

    bus = Bus()
    clock = SimClock()
    cap = int(args.record_cap_mb * 1e6) if args.record_cap_mb > 0 else None
    recorder = DatagramRecorder(out_path, max_bytes=cap)
    mavlink = MavlinkIO(bus, clock, cfg.mavlink_ip, cfg.mavlink_port)
    vision = VisionRX(bus, cfg.vision_ip, cfg.vision_port,
                      raw_sink=recorder.sink_for(STREAM_VISION))
    timesync = TimeSyncTX(mavlink, cfg.timesync_hz)

    print(f"Waiting for sim heartbeat on udp:{cfg.mavlink_ip}:{cfg.mavlink_port} "
          f"(timeout {cfg.heartbeat_timeout_s}s)...", flush=True)
    try:
        mavlink.connect(timeout_s=cfg.heartbeat_timeout_s)
    except TimeoutError as exc:
        print(f"FAIL: {exc}", flush=True)
        return 1
    print("Heartbeat received. Listening (passive — not arming)...", flush=True)

    mavlink.start()
    vision.start()
    timesync.start()

    cells = {name: bus.cell(topic) for name, topic in [
        ("imu", Topic.IMU), ("frame", Topic.FRAME), ("race", Topic.RACE),
        ("heartbeat", Topic.HEARTBEAT), ("actuator", Topic.ACTUATOR),
    ]}
    counts = {name: 0 for name in cells}
    last_seq = {name: 0 for name in cells}
    last_change = {name: None for name in cells}
    max_gap = {name: 0.0 for name in cells}
    # The real sim was observed emitting heartbeats from multiple sources
    # with different armed flags — track the distinct sources.
    heartbeat_sources: set[tuple[int, int, bool]] = set()
    # v1.0.3385 lessons: message counts alone lie (values can be static), and
    # gyro_z specifically is a PINNED axis on the real sim — so liveness is
    # judged on the max std across all six IMU components, nan-guarded.
    imu_samples: list[list[float]] = []

    t_start = time.monotonic()
    t_end = t_start + args.duration
    next_progress = t_start + 10.0
    window_gyro: list[float] = []      # per-10s liveness window
    window_frames = 0
    race_started = False
    import statistics
    while time.monotonic() < t_end:
        now = time.monotonic()
        for name, cell in cells.items():
            fresh = cell.get_if_newer(last_seq[name])
            if fresh is not None:
                msg, seq = fresh
                new = seq - last_seq[name]
                counts[name] += new
                last_seq[name] = seq
                if last_change[name] is not None:
                    max_gap[name] = max(max_gap[name], now - last_change[name])
                last_change[name] = now
                if name == "heartbeat":
                    heartbeat_sources.add((msg.src_system, msg.src_component, msg.armed))
                elif name == "imu":
                    components = [*msg.accel.tolist(), *msg.gyro.tolist()]
                    if len(imu_samples) < 20000:
                        imu_samples.append(components)
                    window_gyro.append(components)
                elif name == "frame":
                    window_frames += new
                elif name == "race":
                    race_started = msg.started
        if now >= next_progress:
            # Per-window liveness: catches the idle->racing transition live.
            w_std = _max_axis_std(window_gyro)
            live = "ALIVE" if w_std > 1e-5 else "static"
            print(f"  ...{now - t_start:4.0f}s  imu={counts['imu']} ({live}, "
                  f"max_std={w_std:.4f})  frames+={window_frames}  "
                  f"race_started={race_started}", flush=True)
            next_progress += 10.0
            window_gyro = []
            window_frames = 0
        time.sleep(0.002)

    elapsed = time.monotonic() - t_start
    timesync.stop()
    vision.stop()
    mavlink.stop()
    recorder.close()

    offset_std_ms = clock.offset_std_ns() / 1e6
    race, _ = cells["race"].get()

    print("\n=== Phase-1 report ===", flush=True)
    print(f"window: {elapsed:.1f}s", flush=True)
    for name in ("imu", "frame", "race", "heartbeat", "actuator"):
        rate = counts[name] / elapsed if elapsed > 0 else 0.0
        print(f"{name:>9}: {counts[name]:6d} msgs  ({rate:6.1f} Hz, "
              f"max gap {max_gap[name] * 1000:6.0f} ms)", flush=True)
    print(f"vision decode: ok={vision.frames_decoded} failed={vision.frames_failed} "
          f"pending_partials={vision.assembler.pending}", flush=True)
    print(f"timesync: synced={clock.synced}  offset={clock.offset_ns / 1e6:.2f} ms  "
          f"std={offset_std_ms:.2f} ms", flush=True)
    print("heartbeat sources (system, component, armed): "
          + (", ".join(str(s) for s in sorted(heartbeat_sources)) or "none"), flush=True)
    imu_alive = False
    if len(imu_samples) >= 10:
        max_std = _max_axis_std(imu_samples)
        imu_alive = max_std > 1e-5
        print(f"imu liveness: max per-axis std={max_std:.6f} "
              f"-> {'ALIVE' if imu_alive else 'STATIC'} "
              f"(static is expected for a parked drone)", flush=True)
    if race is not None:
        print(f"race status: active_gate_index={race.active_gate_index} "
              f"started={race.started} finished={race.finished}", flush=True)
    print(f"recording: {out_path} ({recorder.count} datagrams"
          + (f", {recorder.skipped} skipped past the {args.record_cap_mb:.0f}MB cap"
             if recorder.skipped else "") + ")", flush=True)

    checks = {
        f"telemetry window >= {args.duration:.0f}s": elapsed >= args.duration - 1.0,
        "IMU flowing": counts["imu"] > 0 and max_gap["imu"] < 1.0,
        "IMU values alive (not frozen)": imu_alive,
        "frames decoded": vision.frames_decoded > 0,
        "race status received": counts["race"] > 0,
        f"timesync offset std < {OFFSET_STD_LIMIT_MS}ms":
            clock.synced and offset_std_ms < OFFSET_STD_LIMIT_MS,
        "recording non-empty": recorder.count > 0,
    }
    print("\n=== acceptance ===", flush=True)
    ok = True
    for label, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}", flush=True)
        ok = ok and passed
    print(f"\n{'PHASE-1 CHECK PASSED' if ok else 'PHASE-1 CHECK FAILED'}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
