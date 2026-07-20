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

import numpy as np

from aigp.core.agent import Agent
from aigp.core.bus import Bus
from aigp.core.messages import TerminalFeature, Topic
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
            state, _ = state_cell.get()
            prior = None
            if state is not None and state.gate_rel is not None \
                    and state.gate_rel_age_s < 1.0:
                prior = float(np.linalg.norm(state.gate_rel.t))
            detection = self.detector.detect(frame, prior)
            if detection is not None and detection.rel_pose is not None:
                self.detections += 1
                if detection.confidence >= 0.55:   # exact quad or box fallback
                    last_full_fix = time.monotonic()
                anchored = False
                if detection.cert_status == "certified" and self.tracker:
                    # Anchor the certificate ONLY when the fix is
                    # prediction-consistent with the locked target: in
                    # the next-gate-steal window a far gate's quad is a
                    # perfectly valid detection of the WRONG gate, and
                    # certification is per-target (FA=0 manifest case 3).
                    r_fix = float(np.linalg.norm(detection.rel_pose.t))
                    if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                        self.tracker.certificate.on_full_quad(detection.ts_ns)
                        anchored = True
                self.bus.publish_latest(Topic.DETECTION, detection)
                if anchored:
                    # Pixel-row oracle from the full quad itself (enable
                    # build): the terminal channel's e_z source must not
                    # wait for the tracker's first partial frame. corners
                    # are tl,tr,br,bl RAW image pixels — and so are the
                    # tracker's feature pixels (its edge search samples
                    # the real image; the mount de-rotation applies to
                    # its 3D vector, never its pixels). Both FEATURE
                    # sources therefore share the raw-image frame; the
                    # §2.3 sign test on the F2 graze passes exactly in
                    # this frame (0 wrong-sign quads) and FAILS if the
                    # corners are 'helpfully' derotated first.
                    c = np.asarray(detection.corners_px, dtype=np.float64)
                    span = float(np.hypot(*(c[1] - c[0])))
                    if span > 1.0:
                        self.bus.publish_latest(Topic.FEATURE, TerminalFeature(
                            ts_ns=detection.ts_ns,
                            y_top_px=float((c[0][1] + c[1][1]) / 2.0),
                            span_px=span,
                            center_x_px=float((c[0][0] + c[1][0]) / 2.0),
                            cert_status=detection.cert_status,
                            mode="FULL_QUAD"))
                continue
            if detection is not None:
                # Center-only detection (pose rejected by the sanity
                # gates): publish for the yaw servo, but DO run the
                # tracker below — a metric fix may still be extractable
                # from partial edges, and this is exactly the terminal
                # regime where density decides certification (release-bar
                # measurement: 1-7 fix frames below 2.5m per approach).
                self.bus.publish_latest(Topic.DETECTION, detection)
            if self.tracker is None or not self.tracker.enabled:
                continue
            if last_full_fix is None or \
                    time.monotonic() - last_full_fix > self.tracker.max_solo_s:
                continue
            state, _ = state_cell.get()
            if state is None or state.gate_rel is None:
                continue
            # A pose-rejected detection still carries the observed ring
            # center — hand it to the tracker as a re-anchor hint so a
            # staling believed pose cannot blind the edge search (F3).
            hint = detection.center_px if detection is not None else None
            tracked = self.tracker.track(frame, state.gate_rel,
                                         center_hint_px=hint)
            if tracked is not None:
                self.tracker_fixes += 1
                self.bus.publish_latest(Topic.DETECTION, tracked)
                if self.tracker.last_feature is not None:
                    # Terminal feature -> flight log (offline Test-A
                    # material with verified identity, pre-servo).
                    self.bus.publish_latest(Topic.FEATURE,
                                            self.tracker.last_feature)
