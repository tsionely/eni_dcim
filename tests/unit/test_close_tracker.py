"""GateCloseTracker: synthetic-scene validation.

The synthetic-clipping trick from the think-tank round: render a gate at a
KNOWN pose, break it the way the real scene does (cut bars, border
clipping), hand the tracker a perturbed prior, and demand metric recovery.
mount_pitch is zeroed so the rendered quad matches plain pinhole geometry;
the projection path itself is exercised (identity de-rotation).
"""
import cv2
import numpy as np
import pytest

from aigp.core.messages import CameraFrame, RelPose
from aigp.core.params import ParamSet
from aigp.perception.close_tracker import GateCloseTracker
from aigp.perception.gate_detector_hsv import HsvGateDetector

W, H, FX = 640, 360, 320.0          # fov 90deg -> fx = 320


def make_tracker():
    params = ParamSet.load("config/params_default.json").patch(
        {"perception.camera.mount_pitch_deg": 0.0})
    return GateCloseTracker(params, HsvGateDetector(params))


def render_gate(t, gate=1.6, bar_px=18, drop_bottom=False, only_sides=False):
    """Red ring at camera-frame position t (fronto-parallel), dark scene.

    The 1.6m model square is the ring's OUTER boundary — matching what the
    acquisition detector measures (outer contour corners against the 1.6
    PnP model) — so bars are drawn INWARD from it.
    """
    img = np.full((H, W, 3), 30, dtype=np.uint8)
    cx = FX * t[0] / t[2] + W / 2.0
    cy = FX * t[1] / t[2] + H / 2.0
    half = FX * (gate / 2.0) / t[2]
    x0, x1 = int(cx - half), int(cx + half)
    y0, y1 = int(cy - half), int(cy + half)
    red = (30, 30, 230)
    if not only_sides:
        cv2.rectangle(img, (x0, y0), (x1, y0 + bar_px), red, -1)
        if not drop_bottom:
            cv2.rectangle(img, (x0, y1 - bar_px), (x1, y1), red, -1)
    cv2.rectangle(img, (x0, y0), (x0 + bar_px, y1), red, -1)
    cv2.rectangle(img, (x1 - bar_px, y0), (x1, y1), red, -1)
    return img


def prior(t):
    return RelPose(t=np.array(t, dtype=float), normal=np.array([0.0, 0.0, -1.0]))


def test_recovers_broken_ring_from_offset_prior():
    """Bottom bar washed out + prior off by (0.2, -0.15, 0.4): the tracker
    must pull the pose back onto the true gate."""
    tr = make_tracker()
    truth = [0.0, 0.0, 3.0]
    frame = CameraFrame(1, 0, render_gate(truth, drop_bottom=True))
    det = tr.track(frame, prior([0.2, -0.15, 3.4]))
    assert det is not None
    t = det.rel_pose.t
    assert abs(t[0] - truth[0]) < 0.10
    assert abs(t[1] - truth[1]) < 0.12
    assert abs(t[2] - truth[2]) < 0.35
    assert det.confidence < 0.7            # position-only fix downstream


def test_recovers_border_clipped_gate():
    """Right edge out of frame (the edge_clip failure class): lateral must
    still be corrected from the visible bars."""
    tr = make_tracker()
    truth = [1.3, 0.0, 2.0]                # right edge projects past x=640
    frame = CameraFrame(1, 0, render_gate(truth))
    det = tr.track(frame, prior([1.15, 0.1, 2.2]))
    assert det is not None
    t = det.rel_pose.t
    assert abs(t[0] - truth[0]) < 0.12
    assert abs(t[1] - truth[1]) < 0.12


def test_no_track_without_support():
    tr = make_tracker()
    empty = np.full((H, W, 3), 30, dtype=np.uint8)
    assert tr.track(CameraFrame(1, 0, empty), prior([0.0, 0.0, 3.0])) is None


def test_out_of_range_prior_rejected():
    tr = make_tracker()
    frame = CameraFrame(1, 0, render_gate([0.0, 0.0, 3.0]))
    assert tr.track(frame, prior([0.0, 0.0, 9.0])) is None


def test_sides_only_stays_bounded():
    """Only the two vertical bars visible (top/bottom washed): lateral must
    be corrected; vertical may be pulled toward the bar ends (real
    evidence) but must never overshoot past the truth-prior interval."""
    tr = make_tracker()
    truth = [0.0, 0.0, 3.0]
    frame = CameraFrame(1, 0, render_gate(truth, only_sides=True))
    p = [0.25, 0.30, 3.0]                  # x wrong by 0.25, y wrong by 0.30
    det = tr.track(frame, prior(p))
    if det is None:                        # <2 edges may legitimately bail
        pytest.skip("tracker rejected sides-only support")
    t = det.rel_pose.t
    assert abs(t[0] - truth[0]) < 0.12     # lateral corrected
    assert -0.08 <= t[1] <= p[1] + 0.05    # bounded by (truth, prior)


def test_side_bar_separation_recovers_absolute_range():
    """Advisory-3 H5: the side bars' separation is the deepest ABSOLUTE
    range source (valid to ~0.8m) — the SVD truncation must keep the
    separation direction, not discard it. Range-off prior, sides only:
    Z must be recovered. (Capture basin is bounded by search_px: a range
    error beyond ~0.4m at 2m puts the predicted edges outside the ROI
    and the tracker returns None — graceful, never wrong.)"""
    tr = make_tracker()
    truth = [0.0, 0.0, 2.0]
    frame = CameraFrame(1, 0, render_gate(truth, only_sides=True))
    det = tr.track(frame, prior([0.05, 0.0, 2.3]))
    assert det is not None
    assert abs(det.rel_pose.t[2] - 2.0) < 0.1
    assert abs(det.rel_pose.t[0]) < 0.1


def test_terminal_feature_extracted_with_certified_pair():
    """Contract step 4: after a full-quad anchor, a tracked frame with a
    visible top edge yields a TerminalFeature whose row and span match
    the rendered geometry, carrying the certificate state."""
    tr = make_tracker()
    truth = [0.0, 0.0, 2.5]
    tr.certificate.on_full_quad(0)
    frame = CameraFrame(1, int(0.05e9), render_gate(truth))
    det = tr.track(frame, prior([0.05, 0.0, 2.6]))
    assert det is not None
    f = tr.last_feature
    assert f is not None
    # Rendered geometry at z=2.5: outer half-size = 320*0.8/2.5 = 102.4px.
    assert abs(f.y_top_px - (180 - 102.4)) < 8
    assert abs(f.span_px - 2 * 102.4) < 12
    assert f.cert_status in ("certified", "probation")
    assert f.mode == "BAR_FULL"


def test_no_feature_without_top_edge():
    tr = make_tracker()
    tr.certificate.on_full_quad(0)
    truth = [0.0, 0.0, 2.5]
    frame = CameraFrame(1, int(0.05e9), render_gate(truth, only_sides=True))
    det = tr.track(frame, prior([0.05, 0.0, 2.6]))
    if det is None:
        pytest.skip("sides-only rejected")
    assert tr.last_feature is None


def test_single_bar_is_rejected():
    """One visible bar = one edge direction: rank-deficient, no fix."""
    tr = make_tracker()
    img = np.full((H, W, 3), 30, dtype=np.uint8)
    cv2.rectangle(img, (300, 100), (318, 260), (30, 30, 230), -1)  # one bar
    det = tr.track(CameraFrame(1, 0, img), prior([0.0, 0.0, 3.0]))
    assert det is None
