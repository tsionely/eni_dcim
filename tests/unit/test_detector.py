import cv2
import numpy as np
import pytest

from aigp.core.messages import CameraFrame
from aigp.core.params import ParamSet
from aigp.perception.gate_detector_hsv import HsvGateDetector, order_corners


@pytest.fixture
def detector():
    return HsvGateDetector(ParamSet.load("config/params_default.json"))


def render_gate_ring(w=640, h=360, cx=320, cy=180, size=120, thickness=16):
    img = np.full((h, w, 3), 40, dtype=np.uint8)
    half = size // 2
    cv2.rectangle(img, (cx - half - thickness, cy - half - thickness),
                  (cx + half + thickness, cy + half + thickness), (255, 255, 255), -1)
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
