"""Extract a commit-sized slice from a large .aigprec recording.

The Phase-1d race recording is ~1.29 GB — far over the fixtures/ size limit.
A slice keeps the wire format intact so replay and detector work run on real
data without the full file:

    python scripts/slice_recording.py recordings/big.aigprec fixtures_slice.aigprec \
        --start-s 5 --max-mb 40

Slices from --start-s (relative to the first datagram) until --max-mb of
payload is written or --duration-s elapses.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.io.udp_tap import DatagramRecorder, read_recording


def main() -> int:
    parser = argparse.ArgumentParser(description="Slice an .aigprec recording")
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--start-s", type=float, default=0.0,
                        help="skip this many seconds from the first datagram")
    parser.add_argument("--duration-s", type=float, default=None)
    parser.add_argument("--max-mb", type=float, default=40.0)
    args = parser.parse_args()

    out = DatagramRecorder(args.dst)
    t0 = None
    written_bytes = 0
    total = kept = 0
    for mono_ns, stream_id, data in read_recording(args.src):
        total += 1
        if t0 is None:
            t0 = mono_ns
        rel_s = (mono_ns - t0) / 1e9
        if rel_s < args.start_s:
            continue
        if args.duration_s is not None and rel_s > args.start_s + args.duration_s:
            break
        if written_bytes + len(data) > args.max_mb * 1e6:
            break
        out.write(stream_id, data, mono_ns=mono_ns)
        written_bytes += len(data)
        kept += 1
    out.close()
    print(f"kept {kept}/{total} datagrams, {written_bytes / 1e6:.1f} MB -> {args.dst}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
