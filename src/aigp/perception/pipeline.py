"""Perception agent: pulls the latest camera frame, runs the detector,
publishes detections. Runs in its own thread at camera rate — cv2 releases
the GIL during the heavy work, so it coexists with the 250Hz control loop.
"""
from __future__ import annotations

import time

from aigp.core.agent import Agent
from aigp.core.bus import Bus
from aigp.core.messages import Topic
from aigp.perception.interface import GateDetector


class PerceptionAgent(Agent):
    name = "perception"

    def __init__(self, bus: Bus, detector: GateDetector) -> None:
        super().__init__()
        self.bus = bus
        self.detector = detector
        self.frames_seen = 0
        self.detections = 0

    def _run(self) -> None:
        frame_cell = self.bus.cell(Topic.FRAME)
        last_seq = 0
        while self.should_run():
            fresh = frame_cell.get_if_newer(last_seq)
            if fresh is None:
                time.sleep(0.002)
                continue
            frame, last_seq = fresh
            self.frames_seen += 1
            detection = self.detector.detect(frame)
            if detection is not None:
                self.detections += 1
                self.bus.publish_latest(Topic.DETECTION, detection)
