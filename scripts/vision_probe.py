"""Vision-stream diagnostic (run against the REAL sim on the Windows machine).

Phase-1 found MAVLink perfectly healthy but ZERO datagrams on udp:5600 —
even during an armed flight with the race started. This probe pins down where
the video went:

- binds a RANGE of UDP ports simultaneously (default 5595-5615) and counts
  datagrams per port, so a port change in the sim version is caught
- hexdumps the first packet per port and tries to parse it with the known
  chunk header, so a format change is caught
- with --arm it also connects MAVLink, arms (which starts the race) and holds
  a gentle climb, so race-gated streaming is caught

    python scripts/vision_probe.py --duration 30
    python scripts/vision_probe.py --duration 30 --arm

If every port stays silent even with --arm:
  1. netstat -ano | findstr 5600        (is anything sending/bound?)
  2. Search the sim install for stream config:
     Get-ChildItem <simdir> -Recurse -Include *.ini,*.json,*.cfg |
         Select-String -Pattern '5600|[Vv]ideo|[Ss]tream|[Pp]ort'
  3. Windows Defender Firewall: allow python.exe inbound UDP (or test 30s
     with the firewall off).
"""
from __future__ import annotations

import argparse
import select
import socket
import struct
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.io.vision_rx import HEADER_FORMAT, HEADER_SIZE


def arm_and_hover(mav_ip: str, mav_port: int, duration_s: float, stop: threading.Event) -> None:
    from pymavlink import mavutil
    conn = mavutil.mavlink_connection(f"udpin:{mav_ip}:{mav_port}")
    print("[arm] waiting for heartbeat...", flush=True)
    if conn.wait_heartbeat(timeout=20) is None:
        print("[arm] no heartbeat — skipping armed segment", flush=True)
        return
    conn.mav.command_long_send(conn.target_system, conn.target_component,
                               mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                               1, 0, 0, 0, 0, 0, 0)
    print("[arm] armed; holding gentle climb then hover", flush=True)
    mask = (mavutil.mavlink.POSITION_TARGET_TYPEMASK_X_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_Y_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
            | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE)
    t0 = time.monotonic()
    while not stop.is_set() and time.monotonic() - t0 < duration_s:
        vz = -0.5 if time.monotonic() - t0 < 2.0 else 0.0
        conn.mav.set_position_target_local_ned_send(
            0, conn.target_system, conn.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED, mask,
            0, 0, 0, 0.0, 0.0, vz, 0, 0, 0, 0, 0)
        time.sleep(0.05)
    conn.mav.command_long_send(conn.target_system, conn.target_component,
                               mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                               0, 0, 0, 0, 0, 0, 0)
    conn.close()
    print("[arm] disarmed", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="UDP vision stream diagnostic")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--port-from", type=int, default=5595)
    parser.add_argument("--port-to", type=int, default=5615)
    parser.add_argument("--arm", action="store_true",
                        help="also arm the drone over MAVLink during the listen window")
    parser.add_argument("--mav-ip", default="127.0.0.1")
    parser.add_argument("--mav-port", type=int, default=14550)
    args = parser.parse_args()

    socks: dict[int, socket.socket] = {}
    for port in range(args.port_from, args.port_to + 1):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setblocking(False)
            s.bind(("0.0.0.0", port))
            socks[port] = s
        except OSError as exc:
            print(f"port {port}: could not bind ({exc})", flush=True)
    if not socks:
        print("no ports bound — nothing to do", file=sys.stderr)
        return 2
    print(f"listening on udp {min(socks)}-{max(socks)} for {args.duration:.0f}s "
          f"({'armed flight' if args.arm else 'passive'})...", flush=True)

    stop = threading.Event()
    armer = None
    if args.arm:
        armer = threading.Thread(target=arm_and_hover,
                                 args=(args.mav_ip, args.mav_port, args.duration, stop),
                                 daemon=True)
        armer.start()

    counts: dict[int, int] = {p: 0 for p in socks}
    total_bytes: dict[int, int] = {p: 0 for p in socks}
    first_packet: dict[int, bytes] = {}
    fd_to_port = {s.fileno(): p for p, s in socks.items()}

    t_end = time.monotonic() + args.duration
    while time.monotonic() < t_end:
        ready, _, _ = select.select(list(socks.values()), [], [], 0.2)
        for s in ready:
            try:
                data, _ = s.recvfrom(65536)
            except OSError:
                continue
            port = fd_to_port[s.fileno()]
            counts[port] += 1
            total_bytes[port] += len(data)
            first_packet.setdefault(port, data)
    stop.set()
    if armer is not None:
        armer.join(timeout=5)
    for s in socks.values():
        s.close()

    print("\n=== results ===", flush=True)
    any_traffic = False
    for port in sorted(socks):
        if counts[port] == 0:
            continue
        any_traffic = True
        print(f"port {port}: {counts[port]} datagrams, {total_bytes[port]} bytes", flush=True)
        pkt = first_packet[port]
        print(f"  first packet ({len(pkt)}B) hex[:32]: {pkt[:32].hex(' ')}", flush=True)
        if len(pkt) >= HEADER_SIZE:
            frame_id, chunk_id, total_chunks, jpeg_size, payload_size, ts = (
                struct.unpack_from(HEADER_FORMAT, pkt))
            plausible = (0 < total_chunks < 512 and chunk_id < total_chunks
                         and 0 < jpeg_size < 10_000_000
                         and payload_size == len(pkt) - HEADER_SIZE)
            print(f"  as chunk header: frame_id={frame_id} chunk={chunk_id}/{total_chunks} "
                  f"jpeg={jpeg_size}B payload={payload_size}B ts={ts} "
                  f"-> {'MATCHES known format' if plausible else 'does NOT match'}", flush=True)
    if not any_traffic:
        print("NO datagrams on any port in range.", flush=True)
        print("Next: check netstat, sim config files, firewall (see module docstring).",
              flush=True)
    return 0 if any_traffic else 1


if __name__ == "__main__":
    sys.exit(main())
