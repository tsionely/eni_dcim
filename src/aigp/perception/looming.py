"""Looming sensor: a vision-only obstacle proxy for the PilotAgent.

The R2 census's residual death class is forward-into-structure WITH a
fresh gate lock — the detector sees only red gates, so scenery between
the drone and the gate is invisible to the whole stack. This sensor
turns the camera's view of that scenery into one scalar: LOOMING, the
rate at which central non-gate texture is expanding. An approaching
surface expands; a receding or lateral-moving scene does not.

Method (cheap, no training, no map): keep a short history of small
grayscale center crops. Compare the current crop against a ~base_s-old
one twice — as-is, and with the old crop zoomed by `scale`. If the
zoomed past explains the present better than the unzoomed past, the
scene has expanded by ~scale over base_s. Score = correlation margin
(zoomed minus unzoomed), EMA-smoothed, floored at 0. The gate's own
bbox is masked out of both crops: the gate SHOULD grow on approach and
must not read as an obstacle.

Pure numpy + cv2; runs on a 64x48 crop (sub-ms). Config-gated
(perception.looming.enable, default OFF).
"""
from __future__ import annotations

from collections import deque

import cv2
import numpy as np


class LoomingSensor:
    def __init__(self, base_s: float = 0.3, crop_frac: float = 0.5,
                 scale: float = 1.08, ema: float = 0.4,
                 size: tuple[int, int] = (64, 48)) -> None:
        self.base_ns = int(base_s * 1e9)
        self.crop_frac = float(crop_frac)
        self.scale = float(scale)
        self.ema = float(ema)
        self.size = size                    # (w, h)
        self._hist: deque = deque(maxlen=32)   # (ts_ns, crop float32)
        self._score = 0.0

    def _crop(self, frame: np.ndarray,
              gate_bbox: tuple[float, float, float, float] | None) -> np.ndarray:
        h, w = frame.shape[:2]
        cw, ch = int(w * self.crop_frac), int(h * self.crop_frac)
        x0, y0 = (w - cw) // 2, (h - ch) // 2
        roi = frame[y0:y0 + ch, x0:x0 + cw]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
        small = cv2.resize(gray, self.size, interpolation=cv2.INTER_AREA)
        small = small.astype(np.float32)
        if gate_bbox is not None:
            # Map the gate bbox (full-frame px) into crop coords and blank
            # it to the crop mean — gate growth is progress, not danger.
            gx0, gy0, gx1, gy1 = gate_bbox
            sx = self.size[0] / cw
            sy = self.size[1] / ch
            bx0 = int(max(0, (gx0 - x0) * sx))
            by0 = int(max(0, (gy0 - y0) * sy))
            bx1 = int(min(self.size[0], (gx1 - x0) * sx + 1))
            by1 = int(min(self.size[1], (gy1 - y0) * sy + 1))
            if bx1 > bx0 and by1 > by0:
                small[by0:by1, bx0:bx1] = float(small.mean())
        return small

    @staticmethod
    def _ncc(a: np.ndarray, b: np.ndarray) -> float:
        """Normalized correlation of two same-size float images."""
        a = a - a.mean()
        b = b - b.mean()
        denom = float(np.sqrt((a * a).sum() * (b * b).sum()))
        if denom < 1e-6:
            return 0.0
        return float((a * b).sum() / denom)

    def _zoom(self, img: np.ndarray) -> np.ndarray:
        """Zoom in by self.scale about the center (crop-and-resize)."""
        w, h = self.size
        cw, ch = int(w / self.scale), int(h / self.scale)
        x0, y0 = (w - cw) // 2, (h - ch) // 2
        inner = img[y0:y0 + ch, x0:x0 + cw]
        return cv2.resize(inner, (w, h), interpolation=cv2.INTER_LINEAR)

    def update(self, frame: np.ndarray, ts_ns: int,
               gate_bbox: tuple[float, float, float, float] | None = None
               ) -> float | None:
        cur = self._crop(frame, gate_bbox)
        old = None
        for t, img in self._hist:
            if ts_ns - t >= self.base_ns:
                old = img              # youngest crop >= base_s old
            else:
                break
        self._hist.append((ts_ns, cur))
        if old is None:
            return None
        corr_same = self._ncc(old, cur)
        corr_zoom = self._ncc(self._zoom(old), cur)
        raw = max(0.0, corr_zoom - corr_same)
        self._score = (1.0 - self.ema) * self._score + self.ema * raw
        return self._score

    @property
    def score(self) -> float:
        return self._score

    def reset(self) -> None:
        self._hist.clear()
        self._score = 0.0
