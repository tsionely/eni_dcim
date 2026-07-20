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
        self.parallel_below_m = float(params.get(
            "perception.close_tracker.parallel_below_m",
            default=3.5)) if params is not None else 3.5
        if params is not None and hasattr(detector, "red_mask"):
            self.tracker = GateCloseTracker(params, detector)

    @staticmethod
    def anchor_consistent(prior: float | None, r_fix: float) -> bool:
        """Prediction-consistency gate for certificate anchoring —
        pinned by the P4(d) regression fixture: in the next-gate-steal
        window a far gate's quad is a perfectly valid detection of the
        WRONG gate, and certification is per-target. An inconsistent
        fix relocks (never anchors); F4 frames 308-315 (fixes at
        17-20m under a sub-meter live lock) are the recorded case the
        detector-only acceptance got wrong and this gate got right."""
        return prior is None or abs(r_fix - prior) <= 0.4 * prior

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
                    if self.anchor_consistent(prior, r_fix):
                        self.tracker.certificate.on_full_quad(
                            detection.ts_ns,
                            z_m=float(detection.rel_pose.t[2]))
                        anchored = True
                    else:
                        # Prediction-INCONSISTENT fix = a different
                        # target: the certificate never survives a
                        # target change (the silent-inheritance root of
                        # the successor-certificate fiction — the audit
                        # found this wire missing).
                        self.tracker.certificate.on_relock_or_collision()
                        self._side_armed = False
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
                    # PARALLEL SIDE PRODUCTION (rung-2 starvation fix):
                    # the close tracker was SIDE's only producer yet ran
                    # only when the detector failed — a 29-recording
                    # sweep found not one legal full->side transition
                    # because the overlap volume that matures the rung
                    # never existed. Below parallel_below_m the tracker
                    # now runs on the SAME anchored frame; only its
                    # FEATURE is published, on its OWN topic (a
                    # latest-value cell must not let the side row shadow
                    # the full row), and never its detection — the
                    # detector's fix is the better pose; one estimate
                    # per channel.
                    if (self.tracker is not None and self.tracker.enabled
                            and float(detection.rel_pose.t[2])
                            <= self.parallel_below_m):
                        # ARM on a fresh measured detection; the latch
                        # holds through detector loss (the exact
                        # condition SIDE exists to survive) and range
                        # bounce — it releases only with the approach
                        # (recording/attempt end).
                        self._side_armed = True
                        # FALLBACK-REALISTIC SEEDING (advisory-15B §2):
                        # the prior is the believed continuity chain —
                        # the same prior the tracker will have when it
                        # runs ALONE — never the same-frame detection
                        # pose (a seeded copy makes the overlap
                        # consistency partly self-fulfilling). The SIDE
                        # metric itself is pixel-derived either way;
                        # seeding only aims the search ROI.
                        st, _ = state_cell.get()
                        prior_pose = (st.gate_rel if st is not None
                                      and st.gate_rel is not None
                                      else detection.rel_pose)
                        tracked = self.tracker.track(
                            frame, prior_pose,
                            center_hint_px=detection.center_px)
                        if (tracked is not None
                                and self.tracker.last_feature is not None):
                            self.bus.publish_latest(
                                Topic.FEATURE_SIDE,
                                self.tracker.last_feature)
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
            if not getattr(self, "_side_armed", False) and (
                    last_full_fix is None
                    or time.monotonic() - last_full_fix
                    > self.tracker.max_solo_s):
                # Unarmed: the historical solo budget. Armed (a fresh
                # measured detection <=parallel_below_m this approach):
                # the tracker continues through detector loss — never
                # disarmed by the very condition it exists to survive.
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
