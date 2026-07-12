"""Asynchronous flight logger.

Installed as the bus tap: every published message is offered here. The tap
only enqueues (drop-with-counter when full — it must never block a
publisher); a writer thread serializes to JSONL. Camera frames are logged as
metadata only (optionally saving every Nth image as JPEG).
"""
from __future__ import annotations

import json
import queue
import time
from pathlib import Path

import cv2

from aigp.core.agent import Agent
from aigp.core.messages import CameraFrame, Topic, to_jsonable


class TelemetryLogger(Agent):
    name = "telemetry_logger"

    def __init__(self, flight_dir: str | Path, save_frames_every_n: int = 0,
                 maxsize: int = 20000) -> None:
        super().__init__()
        self.flight_dir = Path(flight_dir)
        self.flight_dir.mkdir(parents=True, exist_ok=True)
        self.save_frames_every_n = save_frames_every_n
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self.drops = 0
        self._frame_count = 0

    # -- bus tap (called inline by publishers; must not block) ---------------

    def tap(self, topic: str, msg) -> None:
        try:
            self._q.put_nowait((time.monotonic_ns(), topic, msg))
        except queue.Full:
            self.drops += 1

    # -- writer thread --------------------------------------------------------

    def _run(self) -> None:
        path = self.flight_dir / "flight.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            while self.should_run() or not self._q.empty():
                try:
                    mono_ns, topic, msg = self._q.get(timeout=0.2)
                except queue.Empty:
                    continue
                record = {"mono_ns": mono_ns, "topic": topic}
                if isinstance(msg, CameraFrame):
                    record["data"] = {"frame_id": msg.frame_id, "ts_ns": msg.ts_ns,
                                      "shape": list(msg.image.shape)}
                    self._maybe_save_frame(msg)
                else:
                    record["data"] = to_jsonable(msg)
                f.write(json.dumps(record) + "\n")

    def _maybe_save_frame(self, frame: CameraFrame) -> None:
        self._frame_count += 1
        n = self.save_frames_every_n
        if n <= 0 or self._frame_count % n:
            return
        frames_dir = self.flight_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        cv2.imwrite(str(frames_dir / f"{frame.frame_id:08d}.jpg"), frame.image)
