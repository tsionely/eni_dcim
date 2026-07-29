"""LoomingSensor: expansion reads positive, static/pan read ~zero."""
import numpy as np
import pytest

from aigp.perception.looming import LoomingSensor


def textured(seed=7, size=(120, 160)):
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 255, size=(*size, 3), dtype=np.uint8)
    # Smooth a little so zoom interpolation correlates.
    import cv2
    return cv2.GaussianBlur(img, (7, 7), 2.0)


def zoom(img, factor):
    import cv2
    h, w = img.shape[:2]
    ch, cw = int(h / factor), int(w / factor)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return cv2.resize(img[y0:y0 + ch, x0:x0 + cw], (w, h))


def feed(sensor, frames, dt_ns=int(0.1e9)):
    out = []
    for i, f in enumerate(frames):
        r = sensor.update(f, i * dt_ns)
        if r is not None:
            out.append(r)
    return out


def test_static_scene_scores_zero():
    img = textured()
    s = LoomingSensor()
    scores = feed(s, [img] * 12)
    assert scores and max(scores) < 0.01


def test_approaching_surface_scores_positive():
    img = textured()
    frames = [zoom(img, 1.0 + 0.04 * i) for i in range(12)]
    s = LoomingSensor()
    scores = feed(s, frames)
    assert scores and scores[-1] > 0.01


def test_expansion_beats_static():
    img = textured()
    st = feed(LoomingSensor(), [img] * 12)
    zm = feed(LoomingSensor(), [zoom(img, 1.0 + 0.04 * i) for i in range(12)])
    assert zm[-1] > st[-1] + 0.005


def test_gate_bbox_masked_out():
    # Expansion confined to the gate bbox must NOT raise the score much:
    # blank the growing region via the bbox and the rest is static.
    img = textured()
    h, w = img.shape[:2]
    frames = []
    for i in range(12):
        f = img.copy()
        # A growing bright square in the center (the "gate").
        r = 10 + 3 * i
        f[h // 2 - r:h // 2 + r, w // 2 - r:w // 2 + r] = 240
        frames.append(f)
    bbox = (w // 2 - 50, h // 2 - 50, w // 2 + 50, h // 2 + 50)
    s = LoomingSensor()
    scores = []
    for i, f in enumerate(frames):
        rr = s.update(f, i * int(0.1e9), gate_bbox=bbox)
        if rr is not None:
            scores.append(rr)
    assert scores and scores[-1] < 0.02
