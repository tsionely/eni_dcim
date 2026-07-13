"""Port-topology probe for sim v1.0.3385+ (run on the Windows machine).

Phase-1b findings: MAVLink telemetry on udp:14550 flows at full rate but the
IMU VALUES are frozen (std=0.000 over 20s); the sim engine itself binds
udp:5601 and udp:14560; nothing ever arrives on the old vision port 5600.
Hypothesis: the live vehicle channel moved to a connect-style topology —
client sends TO sim:14560 (MAVLink) / sim:5601 (vision) and the sim streams
back to the sender.

This probe tests all of it:

  A. legacy listen on 14550  -> message rates + IMU value LIVENESS
  B. connect to sim:14560    -> our heartbeat out, then rates + liveness
  C. vision poke to sim:5601 -> hello datagrams, listen for a stream back,
                                parse first packet against the chunk header

    python scripts/topology_probe.py

Prints a per-channel verdict and the recommended config/sim.json settings.
"""
from __future__ import annotations

import socket
import statistics
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pymavlink import mavutil

from aigp.io.vision_rx import HEADER_FORMAT, HEADER_SIZE


def sample_mavlink(conn, duration_s: float) -> dict:
    """Collect message rates and IMU value statistics."""
    counts: dict[str, int] = {}
    gyro_z: list[float] = []
    accel_z: list[float] = []
    hb_sources = set()
    t_end = time.monotonic() + duration_s
    while time.monotonic() < t_end:
        msg = conn.recv_match(blocking=True, timeout=0.2)
        if msg is None:
            continue
        mtype = msg.get_type()
        if mtype == "BAD_DATA":
            continue
        counts[mtype] = counts.get(mtype, 0) + 1
        if mtype == "HIGHRES_IMU":
            gyro_z.append(msg.zgyro)
            accel_z.append(msg.zacc)
        elif mtype == "HEARTBEAT":
            armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            hb_sources.add((msg.get_srcSystem(), msg.get_srcComponent(), armed))
    return {"counts": counts, "gyro_z": gyro_z, "accel_z": accel_z,
            "hb_sources": hb_sources, "window_s": duration_s}


def report_mavlink(label: str, stats: dict) -> bool:
    """Print stats; returns True if the IMU values look ALIVE."""
    print(f"\n--- {label} ---", flush=True)
    if not stats["counts"]:
        print("  no messages at all", flush=True)
        return False
    for mtype, n in sorted(stats["counts"].items(), key=lambda kv: -kv[1]):
        print(f"  {mtype:28s} {n:6d}  ({n / stats['window_s']:.1f} Hz)", flush=True)
    if stats["hb_sources"]:
        print(f"  heartbeat sources (sys, comp, armed): "
              f"{sorted(stats['hb_sources'])}", flush=True)
    gz = stats["gyro_z"]
    if len(gz) < 10:
        print("  IMU: too few samples for liveness check", flush=True)
        return False
    std = statistics.pstdev(gz)
    print(f"  IMU liveness: gyro_z mean={statistics.mean(gz):+.3f} std={std:.6f}  "
          f"accel_z mean={statistics.mean(stats['accel_z']):+.2f}", flush=True)
    alive = std > 1e-5
    print(f"  -> IMU values {'ALIVE' if alive else 'FROZEN (constant)'}", flush=True)
    return alive


def probe_vision_poke(sim_ip: str, sim_port: int, local_port: int,
                      duration_s: float) -> bool:
    print(f"\n--- vision poke: hello -> {sim_ip}:{sim_port}, "
          f"listening on local {local_port} ---", flush=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.2)
    try:
        sock.bind(("0.0.0.0", local_port))
    except OSError as exc:
        print(f"  could not bind local {local_port} ({exc}); using ephemeral", flush=True)
    hellos = [b"", b"\x01", b"AIGP", b"hello"]
    t_end = time.monotonic() + duration_s
    next_poke = 0.0
    poke_i = 0
    packets = 0
    first: bytes | None = None
    while time.monotonic() < t_end:
        if time.monotonic() >= next_poke:
            payload = hellos[poke_i % len(hellos)]
            try:
                sock.sendto(payload, (sim_ip, sim_port))
            except OSError as exc:
                print(f"  sendto failed: {exc}", flush=True)
            poke_i += 1
            next_poke = time.monotonic() + 1.0
        try:
            data, _ = sock.recvfrom(65536)
        except socket.timeout:
            continue
        packets += 1
        if first is None:
            first = data
    sock.close()
    print(f"  received {packets} datagrams", flush=True)
    if first is not None:
        print(f"  first packet ({len(first)}B) hex[:32]: {first[:32].hex(' ')}", flush=True)
        if len(first) >= HEADER_SIZE:
            fid, cid, total, jpeg, psize, ts = struct.unpack_from(HEADER_FORMAT, first)
            plausible = (0 < total < 512 and cid < total and 0 < jpeg < 10_000_000)
            print(f"  as chunk header: frame={fid} chunk={cid}/{total} jpeg={jpeg}B "
                  f"-> {'MATCHES known format' if plausible else 'unknown format'}",
                  flush=True)
    return packets > 0


def main() -> int:
    verdicts = {}

    # A. Legacy listen on 14550.
    print("A) legacy udpin:14550 — waiting for heartbeat (10s)...", flush=True)
    legacy = mavutil.mavlink_connection("udpin:127.0.0.1:14550")
    if legacy.wait_heartbeat(timeout=10) is not None:
        verdicts["14550 alive"] = report_mavlink("legacy 14550", sample_mavlink(legacy, 8.0))
    else:
        print("  no heartbeat on 14550", flush=True)
        verdicts["14550 alive"] = False
    legacy.close()

    # B. Connect-style to sim:14560.
    print("\nB) udpout to sim:14560 — sending our heartbeat, waiting (10s)...", flush=True)
    conn = mavutil.mavlink_connection("udpout:127.0.0.1:14560",
                                      source_system=245, source_component=190)
    got = None
    for _ in range(10):
        conn.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                                mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        got = conn.recv_match(type="HEARTBEAT", blocking=True, timeout=1.0)
        if got is not None:
            break
    if got is not None:
        print("  heartbeat received from sim on 14560!", flush=True)
        verdicts["14560 alive"] = report_mavlink("connect 14560", sample_mavlink(conn, 8.0))
    else:
        print("  no response on 14560", flush=True)
        verdicts["14560 alive"] = False
    conn.close()

    # C. Vision poke at 5601 (and re-check silent 5600 while at it).
    verdicts["5601 vision"] = probe_vision_poke("127.0.0.1", 5601, 5600, 12.0)

    print("\n=== summary ===", flush=True)
    for k, v in verdicts.items():
        print(f"  {k}: {'YES' if v else 'no'}", flush=True)
    print("\nRecommended config/sim.json changes (for the cloud agent):", flush=True)
    if verdicts.get("14560 alive"):
        print('  mavlink: {"mode": "connect", "ip": "127.0.0.1", "port": 14560}', flush=True)
    if verdicts.get("5601 vision"):
        print('  vision:  {"mode": "subscribe", "remote_port": 5601}', flush=True)
    if not any(verdicts.values()):
        print("  none of the hypotheses confirmed — capture a fuller netstat "
              "(-anob as admin) and sim-side logs", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
