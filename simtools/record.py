"""UDP recorder/forwarder — run on the Windows machine next to the real sim.

Sits between the sim and the pilot: binds the sim-facing ports, records every
datagram to an .aigprec file (see aigp/io/udp_tap.py for the format) and
forwards to the pilot's ports.

    sim --UDP 5600--> record.py --UDP 5601--> pilot (vision)
    sim --UDP 14550-> record.py --UDP 14551-> pilot (MAVLink, both directions)

Usage:
    python simtools/record.py --out recordings/flight1.aigprec

Then point the pilot's config at the forwarded ports (14551 / 5601).
Recordings become regression fixtures for `aigp --mode replay` and
simtools/replay_server.py.
"""
from __future__ import annotations

import argparse
import socket
import threading
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.io.udp_tap import STREAM_MAVLINK, STREAM_VISION, DatagramRecorder


def forward_loop(listen_port: int, forward_port: int, stream_id: int,
                 recorder: DatagramRecorder, stop: threading.Event,
                 bidirectional: bool) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.2)
    sock.bind(("0.0.0.0", listen_port))
    upstream_addr = None   # the sim's address, learned from the first packet

    fwd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fwd.settimeout(0.2)
    fwd_addr = ("127.0.0.1", forward_port)

    def back_loop() -> None:
        # Pilot -> sim direction (MAVLink commands).
        while not stop.is_set():
            try:
                data, _ = fwd.recvfrom(65536)
            except socket.timeout:
                continue
            recorder.write(stream_id, data)
            if upstream_addr is not None:
                sock.sendto(data, upstream_addr)

    if bidirectional:
        threading.Thread(target=back_loop, daemon=True).start()

    while not stop.is_set():
        try:
            data, addr = sock.recvfrom(65536)
        except socket.timeout:
            continue
        upstream_addr = addr
        recorder.write(stream_id, data)
        fwd.sendto(data, fwd_addr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record + forward sim UDP traffic")
    parser.add_argument("--out", required=True, help="output .aigprec path")
    parser.add_argument("--mavlink-in", type=int, default=14550)
    parser.add_argument("--mavlink-out", type=int, default=14551)
    parser.add_argument("--vision-in", type=int, default=5600)
    parser.add_argument("--vision-out", type=int, default=5601)
    args = parser.parse_args()

    recorder = DatagramRecorder(args.out)
    stop = threading.Event()
    threads = [
        threading.Thread(target=forward_loop,
                         args=(args.mavlink_in, args.mavlink_out, STREAM_MAVLINK,
                               recorder, stop, True), daemon=True),
        threading.Thread(target=forward_loop,
                         args=(args.vision_in, args.vision_out, STREAM_VISION,
                               recorder, stop, False), daemon=True),
    ]
    for t in threads:
        t.start()
    print(f"Recording to {args.out} (MAVLink {args.mavlink_in}->{args.mavlink_out}, "
          f"vision {args.vision_in}->{args.vision_out}). Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        stop.set()
        time.sleep(0.5)
        recorder.close()
        print(f"Saved {recorder.count} datagrams.", flush=True)


if __name__ == "__main__":
    main()
