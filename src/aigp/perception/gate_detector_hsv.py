"""Round-1 classical gate detector.

The Round-1 environment is desaturated and high contrast: gates are bright
against a dark background. Pipeline:

    grayscale -> threshold -> morphological close -> contours
    -> convex 4-gon fit -> corner ordering -> confidence -> PnP

All thresholds live in the ParamSet (perception.detector.*) so the tuning
loop can adjust them.
"""
from __future__ import annotations

import cv2
import numpy as np

from aigp.core.messages import CameraFrame, GateDetection
from aigp.core.params import ParamSet
from aigp.perception.camera import PinholeCamera
from aigp.perception.interface import GateDetector


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as tl, tr, br, bl."""
    pts = pts.reshape(4, 2).astype(np.float64)
    s = pts.sum(axis=1)
    d = pts[:, 0] - pts[:, 1]
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmax(d)]
    bl = pts[np.argmin(d)]
    return np.array([tl, tr, br, bl])


class HsvGateDetector(GateDetector):
    def __init__(self, params: ParamSet) -> None:
        self.threshold = int(params.get("perception.detector.threshold"))
        self.min_area_frac = float(params.get("perception.detector.min_area_frac"))
        self.max_area_frac = float(params.get("perception.detector.max_area_frac"))
        self.approx_eps_frac = float(params.get("perception.detector.approx_eps_frac"))
        self.min_confidence = float(params.get("perception.detector.min_confidence"))
        self.gate_w = float(params.get("perception.gate.width_m"))
        self.gate_h = float(params.get("perception.gate.height_m"))
        self.camera = PinholeCamera(float(params.get("perception.camera.fov_deg")))
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    def detect(self, frame: CameraFrame) -> GateDetection | None:
        img = frame.image
        h, w = img.shape[:2]
        image_area = float(h * w)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best: tuple[float, np.ndarray] | None = None
        for contour in contours:
            area = cv2.contourArea(contour)
            frac = area / image_area
            if frac < self.min_area_frac or frac > self.max_area_frac:
                continue
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, self.approx_eps_frac * perimeter, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            # Rectangularity: contour area vs. its rotated bounding box area.
            (_, (bw, bh), _) = cv2.minAreaRect(contour)
            box_area = bw * bh
            if box_area <= 0:
                continue
            rectangularity = area / box_area
            confidence = min(1.0, rectangularity) * min(1.0, frac / self.min_area_frac / 4.0 + 0.5)
            if confidence < self.min_confidence:
                continue
            if best is None or area > best[0]:
                best = (area, approx)

        if best is None:
            return None

        corners = order_corners(best[1])
        center = (float(corners[:, 0].mean()), float(corners[:, 1].mean()))
        rel_pose = self.camera.solve_gate_pnp(corners, (w, h), self.gate_w, self.gate_h)
        return GateDetection(
            ts_ns=frame.ts_ns,
            corners_px=corners,
            center_px=center,
            image_size=(w, h),
            rel_pose=rel_pose,
            confidence=1.0,
        )
