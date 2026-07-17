"""Perception agent: pulls the latest camera frame, runs the detector,
publishes detections. Runs in its own thread at camera rate — cv2 releases
the GIL during the heavy work, so it coexists with the 250Hz control loop.

Two-tier perception (phase 5b): the acquisition detector (full quad / box
fallback) leads; when it misses AND we recently had a full fix, the
GateCloseTracker refines the estimator's dead-reckoned gate against
partial edges (border-clipped / bloom-cut rings). Tracker-only operation
is capped at max_solo_s so the loop cannot feed on its own predictions.
"""
from __future__ import annotations

import time

from aigp.core.agent import Agent
from aigp.core.bus import Bus
from aigp.core.messages import Topic
from aigp.core.params import ParamSet
from aigp.perception.close_tracker import GateCloseTracker
from aigp.perception.interface import GateDetector


class PerceptionAgent(Agent):
    name = "perception"

    def __init__(self, bus: Bus, detector: GateDetector,
                 params: ParamSet | None = None) -> None:
        super().__init__()
        self.bus = bus
        self.detector = detector
        self.frames_seen = 0
        self.detections = 0
        self.tracker_fixes = 0
        self.tracker = None
        if params is not None and hasattr(detector, "red_mask"):
            self.tracker = GateCloseTracker(params, detector)

    def _run(self) -> None:
        frame_cell = self.bus.cell(Topic.FRAME)
        state_cell = self.bus.cell(Topic.STATE)
        last_seq = 0
        last_full_fix = None
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
                if detection.confidence >= 0.55:   # exact quad or box fallback
                    last_full_fix = time.monotonic()
                self.bus.publish_latest(Topic.DETECTION, detection)
                continue
            if self.tracker is None or not self.tracker.enabled:
                continue
            if last_full_fix is None or \
                    time.monotonic() - last_full_fix > self.tracker.max_solo_s:
                continue
            state, _ = state_cell.get()
            if state is None or state.gate_rel is None:
                continue
            tracked = self.tracker.track(frame, state.gate_rel)
            if tracked is not None:
                self.tracker_fixes += 1
                self.bus.publish_latest(Topic.DETECTION, tracked)
