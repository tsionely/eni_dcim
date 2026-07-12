"""Replay a recorded UDP session with original timing.

Re-emits the datagrams of an .aigprec recording to the pilot's ports so
perception/estimation development can run against REAL sim data without the
sim. (One-directional: replayed MAVLink telemetry is emitted, pilot commands
are ignored.)

    python simtools/replay_server.py recordings/flight1.aigprec
"""
from __future__ import annotations

import argparse
import socket
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.io.udp_tap import STREAM_MAVLINK, STREAM_VISION, read_recording


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay an .aigprec recording")
    parser.add_argument("recording")
    parser.add_argument("--mavlink-port", type=int, default=14550)
    parser.add_argument("--vision-port", type=int, default=5600)
    parser.add_argument("--speed", type=float, default=1.0,
                        help="playback speed multiplier")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    targets = {
        STREAM_MAVLINK: ("127.0.0.1", args.mavlink_port),
        STREAM_VISION: ("127.0.0.1", args.vision_port),
    }

    t0_rec = None
    t0_play = time.monotonic_ns()
    count = 0
    for mono_ns, stream_id, data in read_recording(args.recording):
        if t0_rec is None:
            t0_rec = mono_ns
        due = t0_play + int((mono_ns - t0_rec) / args.speed)
        delay = (due - time.monotonic_ns()) / 1e9
        if delay > 0:
            time.sleep(delay)
        sock.sendto(data, targets[stream_id])
        count += 1
    print(f"Replayed {count} datagrams.", flush=True)


if __name__ == "__main__":
    main()
