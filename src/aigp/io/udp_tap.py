"""Raw datagram recording.

File format (little-endian), shared with simtools/record.py and
simtools/replay_server.py:

    magic:  8 bytes  b"AIGPREC1"
    record: <QBI> mono_ns, stream_id, length   followed by `length` raw bytes

stream_id: 0 = MAVLink port, 1 = vision port.
"""
from __future__ import annotations

import struct
import threading
import time
from pathlib import Path
from typing import BinaryIO, Iterator

MAGIC = b"AIGPREC1"
RECORD_HEADER = "<QBI"
RECORD_HEADER_SIZE = struct.calcsize(RECORD_HEADER)

STREAM_MAVLINK = 0
STREAM_VISION = 1


class DatagramRecorder:
    def __init__(self, path: str | Path, max_bytes: int | None = None) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._f: BinaryIO = open(path, "wb")
        self._f.write(MAGIC)
        self._lock = threading.Lock()
        self.count = 0
        # Cap the file size (a 60s race at 224Hz vision is ~1.3 GB); once
        # exceeded, further datagrams are counted in `skipped` not written.
        self.max_bytes = max_bytes
        self._written = 0
        self.skipped = 0

    def write(self, stream_id: int, data: bytes, mono_ns: int | None = None) -> None:
        if mono_ns is None:
            mono_ns = time.monotonic_ns()
        with self._lock:
            if self.max_bytes is not None and self._written + len(data) > self.max_bytes:
                self.skipped += 1
                return
            self._f.write(struct.pack(RECORD_HEADER, mono_ns, stream_id, len(data)))
            self._f.write(data)
            self._written += len(data)
            self.count += 1

    def sink_for(self, stream_id: int):
        """Returns a callable(bytes) bound to one stream, e.g. for VisionRX."""
        def sink(data: bytes) -> None:
            self.write(stream_id, data)
        return sink

    def close(self) -> None:
        with self._lock:
            self._f.close()


def read_recording(path: str | Path) -> Iterator[tuple[int, int, bytes]]:
    """Yields (mono_ns, stream_id, data) records."""
    with open(path, "rb") as f:
        if f.read(len(MAGIC)) != MAGIC:
            raise ValueError(f"{path} is not an AIGP recording")
        while True:
            header = f.read(RECORD_HEADER_SIZE)
            if len(header) < RECORD_HEADER_SIZE:
                return
            mono_ns, stream_id, length = struct.unpack(RECORD_HEADER, header)
            data = f.read(length)
            if len(data) < length:
                return
            yield mono_ns, stream_id, data
