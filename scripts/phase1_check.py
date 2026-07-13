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


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 passive connectivity check")
    parser.add_argument("--config", default="config/sim.json")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--out", default=None, help="recording path (.aigprec)")
    args = parser.parse_args()

    cfg = SimConfig.load(args.config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = Path(args.out or f"recordings/phase1-{stamp}.aigprec")

    bus = Bus()
    clock = SimClock()
    recorder = DatagramRecorder(out_path)
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
    # v1.0.3385 lesson: the 14550 channel streams at full rate with FROZEN
    # values. Counting messages is not enough — sample values for liveness.
    gyro_z_samples: list[float] = []

    t_start = time.monotonic()
    t_end = t_start + args.duration
    next_progress = t_start + 10.0
    while time.monotonic() < t_end:
        now = time.monotonic()
        for name, cell in cells.items():
            fresh = cell.get_if_newer(last_seq[name])
            if fresh is not None:
                msg, seq = fresh
                counts[name] += seq - last_seq[name]
                last_seq[name] = seq
                if last_change[name] is not None:
                    max_gap[name] = max(max_gap[name], now - last_change[name])
                last_change[name] = now
                if name == "heartbeat":
                    heartbeat_sources.add((msg.src_system, msg.src_component, msg.armed))
                elif name == "imu" and len(gyro_z_samples) < 20000:
                    gyro_z_samples.append(float(msg.gyro[2]))
        if now >= next_progress:
            next_progress += 10.0
            print(f"  ...{now - t_start:4.0f}s  imu={counts['imu']}  "
                  f"frames={counts['frame']}  race={counts['race']}", flush=True)
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
    import statistics
    imu_alive = False
    if len(gyro_z_samples) >= 10:
        gz_std = statistics.pstdev(gyro_z_samples)
        imu_alive = gz_std > 1e-5
        print(f"imu liveness: gyro_z mean={statistics.mean(gyro_z_samples):+.3f} "
              f"std={gz_std:.6f} -> {'ALIVE' if imu_alive else 'FROZEN'}", flush=True)
    if race is not None:
        print(f"race status: active_gate_index={race.active_gate_index} "
              f"started={race.started} finished={race.finished}", flush=True)
    print(f"recording: {out_path} ({recorder.count} datagrams)", flush=True)

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
