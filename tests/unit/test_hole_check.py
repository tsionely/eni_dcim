"""Target identity — the hole check (banner hypothesis, R2H census).

A traversable ring shows the scene through its opening (inner region not
red); a banner/signage rectangle is red throughout. The detector must
reject the banner when the check is enabled and keep old behavior when
it is off (default).
"""
import numpy as np
import pytest

from aigp.core.messages import CameraFrame
from aigp.core.params import ParamSet
from aigp.perception.gate_detector_hsv import HsvGateDetector

RED = (40, 40, 230)      # BGR — inside the detector's red HSV band
GREY = (90, 90, 90)


def frame(img):
    return CameraFrame(frame_id=1, ts_ns=0, image=img)


def scene():
    return np.full((360, 640, 3), GREY, dtype=np.uint8)


def draw_ring(img, x0=200, y0=60, size=220, bar=26):
    """Hollow red ring (a real gate): red frame, scene visible inside."""
    x1, y1 = x0 + size, y0 + size
    img[y0:y1, x0:x1] = RED
    img[y0 + bar:y1 - bar, x0 + bar:x1 - bar] = GREY
    return img


def draw_banner(img, x0=200, y0=60, size=220):
    """Solid red rectangle (signage/banner on a wall)."""
    img[y0:y0 + size, x0:x0 + size] = RED
    return img


def detector(**over):
    p = ParamSet.load("config/params_default.json")
    if over:
        p = p.patch(over)
    return HsvGateDetector(p)


def test_ring_accepted_with_hole_check():
    det = detector(**{"perception.detector.hole_check_enable": True})
    d = det.detect(frame(draw_ring(scene())))
    assert d is not None


def test_banner_rejected_with_hole_check():
    det = detector(**{"perception.detector.hole_check_enable": True})
    d = det.detect(frame(draw_banner(scene())))
    assert d is None


def test_banner_accepted_by_default():
    # Default OFF preserves today's behavior (the banner is a convex red
    # quad and the legacy path accepts it) — the flag is the change.
    det = detector()
    d = det.detect(frame(draw_banner(scene())))
    assert d is not None


def test_ring_beats_banner_in_same_scene():
    # Both visible: with the check on, only the ring may win.
    det = detector(**{"perception.detector.hole_check_enable": True})
    img = scene()
    draw_banner(img, x0=40, y0=80, size=200)      # bigger area, solid
    draw_ring(img, x0=360, y0=100, size=170)
    d = det.detect(frame(img))
    assert d is not None
    cx = d.center_px[0]
    assert cx > 320          # locked the ring (right side), not the banner
