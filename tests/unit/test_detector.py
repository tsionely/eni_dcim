import cv2
import numpy as np
import pytest

from aigp.core.messages import CameraFrame
from aigp.core.params import ParamSet
from aigp.perception.gate_detector_hsv import HsvGateDetector, order_corners


@pytest.fixture
def detector():
    return HsvGateDetector(ParamSet.load("config/params_default.json"))


def render_gate_ring(w=640, h=360, cx=320, cy=180, size=120, thickness=16,
                     color=(30, 30, 230)):
    """Red gate ring on a dark background — matches the real Round-1 scene."""
    img = np.full((h, w, 3), 40, dtype=np.uint8)
    half = size // 2
    cv2.rectangle(img, (cx - half - thickness, cy - half - thickness),
                  (cx + half + thickness, cy + half + thickness), color, -1)
    cv2.rectangle(img, (cx - half, cy - half), (cx + half, cy + half), (40, 40, 40), -1)
    return img


def test_detects_centered_gate(detector):
    frame = CameraFrame(1, 0, render_gate_ring())
    det = detector.detect(frame)
    assert det is not None
    assert abs(det.center_px[0] - 320) < 10
    assert abs(det.center_px[1] - 180) < 10
    assert det.rel_pose is not None
    assert det.rel_pose.t[2] > 0          # gate in front of the camera


def test_detects_offset_gate(detector):
    frame = CameraFrame(1, 0, render_gate_ring(cx=450, cy=120, size=80))
    det = detector.detect(frame)
    assert det is not None
    assert det.center_px[0] > 400
    assert det.center_px[1] < 160


def test_empty_frame(detector):
    img = np.full((360, 640, 3), 40, dtype=np.uint8)
    assert detector.detect(CameraFrame(1, 0, img)) is None


def test_noise_frame(detector):
    rng = np.random.default_rng(0)
    img = rng.integers(0, 90, (360, 640, 3), dtype=np.uint8)  # dark noise
    assert detector.detect(CameraFrame(1, 0, img)) is None


def test_picks_largest_of_multiple_gates(detector):
    # Two gates like the real track: near (large) and far (small).
    img = render_gate_ring(cx=320, cy=170, size=100)
    small = render_gate_ring(cx=340, cy=200, size=24, thickness=5)
    mask = small.sum(axis=2) > 200
    img[mask] = small[mask]
    det = detector.detect(CameraFrame(1, 0, img))
    assert det is not None
    assert abs(det.center_px[0] - 320) < 10
    assert abs(det.center_px[1] - 170) < 10


def test_distance_scales_inversely_with_size(detector):
    near = detector.detect(CameraFrame(1, 0, render_gate_ring(size=200)))
    far = detector.detect(CameraFrame(2, 0, render_gate_ring(size=60)))
    assert near is not None and far is not None
    assert near.rel_pose is not None and far.rel_pose is not None
    assert far.rel_pose.distance > near.rel_pose.distance


def test_order_corners():
    pts = np.array([[10, 10], [100, 12], [98, 90], [12, 88]], dtype=np.float64)
    shuffled = pts[[2, 0, 3, 1]]
    ordered = order_corners(shuffled)
    assert np.allclose(ordered, pts)


def test_detects_bloom_washed_ring(detector):
    """Phase 5: inside the racing line's glow the ring turns bright PINK
    (measured H~152 S~76 V~245 on the real frames) — outside both red hue
    bands. The washed-red branch must still see it."""
    pink = (206, 172, 245)                   # BGR of the measured washed ring
    frame = CameraFrame(1, 0, render_gate_ring(color=pink))
    det = detector.detect(frame)
    assert det is not None
    assert abs(det.center_px[0] - 320) < 10
    assert abs(det.center_px[1] - 180) < 10


def render_broken_ring(w=640, h=360, cx=320, cy=180, size=150, thickness=20):
    """Ring with the bottom bar washed out (bloom cut) — a big open shape."""
    img = render_gate_ring(w, h, cx, cy, size, thickness)
    half = size // 2
    cv2.rectangle(img, (cx - half + 1, cy + half),
                  (cx + half - 1, cy + half + thickness), (40, 40, 40), -1)
    return img


def test_broken_ring_box_fallback(detector):
    """Phase 5: bloom cuts the bottom bar -> outline is not a convex 4-gon
    and every recorded flight went blind here. The minAreaRect fallback
    must produce a (lower-confidence) fix with roughly the right center."""
    det = detector.detect(CameraFrame(1, 0, render_broken_ring()))
    assert det is not None
    assert det.confidence < 1.0              # fallback, not an exact quad
    assert abs(det.center_px[0] - 320) < 15
    assert abs(det.center_px[1] - 180) < 15
    assert det.rel_pose is not None and det.rel_pose.t[2] > 0


def test_small_broken_ring_not_rescued(detector):
    """The box fallback is a close-range rescue only: a small broken ring
    (far gate) must NOT produce a sloppy fix."""
    det = detector.detect(CameraFrame(1, 0, render_broken_ring(size=40, thickness=6)))
    assert det is None


def test_exact_quad_wins_over_fallback(detector):
    """When a clean quad exists the exact path must be used (confidence 1)."""
    det = detector.detect(CameraFrame(1, 0, render_gate_ring(size=150)))
    assert det is not None and det.confidence == 1.0


def test_scale_gate_rejects_narrow_substructure_pose():
    """F2 autopsy (D5): the detector locked a narrow sub-structure and PnP
    invented a pose — R·max(w,h)px ran at a third of fx·gate_w. Such a
    pose must be dropped (center kept for yaw, rel_pose None), while a
    proper ring's pose passes the same gate."""
    from aigp.core.params import ParamSet
    from aigp.perception.gate_detector_hsv import HsvGateDetector
    det = HsvGateDetector(ParamSet.load("config/params_default.json"))
    # A solid narrow red strip forms a clean convex quad.
    img = np.full((360, 640, 3), 40, dtype=np.uint8)
    cv2.rectangle(img, (280, 165), (382, 195), (30, 30, 230), -1)
    d = det.detect(CameraFrame(1, 0, img))
    assert d is None or d.rel_pose is None
    ring = det.detect(CameraFrame(1, 0, render_gate_ring()))
    assert ring is not None and ring.rel_pose is not None
