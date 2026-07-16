"""FPV camera stream receiver.

The sim streams JPEG frames over UDP, split into chunk packets with the
header struct "<IHHIIQ" (carried over from the official template):

    frame_id, chunk_id, total_chunks, jpeg_size, payload_size, sim_time_ns

ChunkAssembler is pure logic (unit-testable without sockets). VisionRX is the
socket-facing agent thread. Fixes over the template: the socket has a timeout
so stop() converges, and partial frames are garbage-collected so packet loss
does not grow memory unboundedly.
"""
from __future__ import annotations

import socket
import struct
import time

import cv2
import numpy as np

from aigp.core.agent import Agent
from aigp.core.bus import Bus
from aigp.core.messages import CameraFrame, Topic

HEADER_FORMAT = "<IHHIIQ"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class ChunkAssembler:
    """Reassembles chunked JPEG frames from raw datagrams."""

    def __init__(self, stale_after_s: float = 2.0) -> None:
        self.stale_after_s = stale_after_s
        self._frames: dict[int, dict] = {}

    def feed(self, packet: bytes, now: float | None = None) -> tuple[int, int, bytes] | None:
        """Feed one datagram. Returns (frame_id, sim_time_ns, jpeg_bytes) when a
        frame completes, else None."""
        if now is None:
            now = time.monotonic()
        if len(packet) < HEADER_SIZE:
            return None
        frame_id, chunk_id, total_chunks, jpeg_size, payload_size, sim_time_ns = (
            struct.unpack_from(HEADER_FORMAT, packet)
        )
        payload = packet[HEADER_SIZE:]

        entry = self._frames.get(frame_id)
        if entry is None:
            entry = self._frames[frame_id] = {
                "chunks": {},
                "total": total_chunks,
                "time": sim_time_ns,
                "first_seen": now,
            }
        entry["chunks"][chunk_id] = payload

        if len(entry["chunks"]) == entry["total"]:
            jpeg = bytearray()
            for i in range(entry["total"]):
                chunk = entry["chunks"].get(i)
                if chunk is None:
                    # Duplicate chunk_ids filled the count but a piece is
                    # missing; drop the frame.
                    del self._frames[frame_id]
                    return None
                jpeg.extend(chunk)
            del self._frames[frame_id]
            self._gc(now)
            return frame_id, entry["time"], bytes(jpeg)

        self._gc(now)
        return None

    def _gc(self, now: float) -> None:
        stale = [fid for fid, e in self._frames.items()
                 if now - e["first_seen"] > self.stale_after_s]
        for fid in stale:
            del self._frames[fid]

    @property
    def pending(self) -> int:
        return len(self._frames)


class VisionRX(Agent):
    name = "vision_rx"

    def __init__(self, bus: Bus, listen_ip: str, listen_port: int,
                 raw_sink=None, mode: str = "listen",
                 remote: tuple[str, int] | None = None,
                 hello_interval_s: float = 1.0) -> None:
        super().__init__()
        self.bus = bus
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.raw_sink = raw_sink        # optional callable(bytes) for recording
        # "listen": sim pushes to our port. "subscribe": sim binds `remote`;
        # we poke it from our socket and it streams back to the source
        # address (v1.0.3385-style topology).
        self.mode = mode
        self.remote = remote
        self.hello_interval_s = hello_interval_s
        self.assembler = ChunkAssembler()
        self.frames_decoded = 0
        self.frames_failed = 0
        self.frames_duplicate = 0
        self._last_frame_id: int | None = None

    def _is_new_exposure(self, frame_id: int) -> bool:
        """Drop the sim's frame REBROADCASTS before the JPEG decode.

        v1.0.3385 re-sends each exposure ~8-9x (measured: ~280 frame
        messages/s vs ~30 unique/s on real recordings). Without this,
        every duplicate costs a full imdecode + detector pass, the
        estimator ingests each exposure ~9x as independent measurements,
        and a FROZEN stream keeps feeding the frame watchdog. IDs only
        grow within a stream; a large backward jump means the sim
        restarted its numbering (new race) — accept and re-anchor.
        """
        last = self._last_frame_id
        if last is not None and frame_id <= last and frame_id > last - 1000:
            return False
        self._last_frame_id = frame_id
        return True

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.bind((self.listen_ip, self.listen_port))
        next_hello = 0.0
        got_stream = False
        try:
            while self.should_run():
                if self.mode == "subscribe" and self.remote is not None:
                    now = time.monotonic()
                    # Poke fast until the stream starts, then keep alive.
                    interval = 5.0 if got_stream else self.hello_interval_s
                    if now >= next_hello:
                        try:
                            sock.sendto(b"\x01", self.remote)
                        except OSError:
                            pass
                        next_hello = now + interval
                try:
                    packet, _ = sock.recvfrom(65536)
                except socket.timeout:
                    continue
                got_stream = True
                if self.raw_sink is not None:
                    self.raw_sink(packet)
                done = self.assembler.feed(packet)
                if done is None:
                    continue
                frame_id, sim_time_ns, jpeg = done
                if not self._is_new_exposure(frame_id):
                    self.frames_duplicate += 1
                    continue
                img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    self.frames_failed += 1
                    continue
                self.frames_decoded += 1
                self.bus.publish_latest(
                    Topic.FRAME, CameraFrame(frame_id=frame_id, ts_ns=sim_time_ns, image=img)
                )
        finally:
            sock.close()
