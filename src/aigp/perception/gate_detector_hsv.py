"""Round-1 classical gate detector.

Reality check from the first real race recording (fixtures phase1e): Round-1
gates are saturated RED square rings in a dark warehouse scene, several gates
visible at once along the track, with a cyan racing-line spline. So the
primary mode segments by red hue; the original brightness-threshold mode is
kept for synthetic/mock scenes and as a fallback.

    mode "red_hsv" (default): HSV red mask (both hue bands) -> contours ->
        convex 4-gon -> cyan-prior scoring (see below), largest wins among
        equals
    mode "bright": grayscale threshold (legacy)

Cyan prior: the R2 racing line (H 90-98, S/V high — analysis
2026-07-14-r2-deepdive, measured through-next-gate 100%) threads the NEXT
gate's opening. Candidates whose opening contains cyan get a score boost,
so with several gates in frame the pilot locks the one on the racing line.
Scenes without cyan (mock, some R1 views) fall back to pure largest-area.

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
        self.mode = params.get("perception.detector.mode", default="red_hsv")
        self.threshold = int(params.get("perception.detector.threshold", default=180))
        self.hue_low_max = int(params.get("perception.detector.red_hue_low_max", default=12))
        self.hue_high_min = int(params.get("perception.detector.red_hue_high_min", default=168))
        self.sat_min = int(params.get("perception.detector.red_sat_min", default=90))
        self.val_min = int(params.get("perception.detector.red_val_min", default=70))
        self.min_area_frac = float(params.get("perception.detector.min_area_frac"))
        self.max_area_frac = float(params.get("perception.detector.max_area_frac"))
        self.approx_eps_frac = float(params.get("perception.detector.approx_eps_frac"))
        self.min_confidence = float(params.get("perception.detector.min_confidence"))
        self.gate_w = float(params.get("perception.gate.width_m"))
        self.gate_h = float(params.get("perception.gate.height_m"))
        self.camera = PinholeCamera(
            float(params.get("perception.camera.fov_deg")),
            float(params.get("perception.camera.mount_pitch_deg", default=0.0)))
        self.cyan_prior = bool(params.get("perception.detector.cyan_prior",
                                          default=True))
        self.cyan_hue_min = int(params.get("perception.detector.cyan_hue_min", default=90))
        self.cyan_hue_max = int(params.get("perception.detector.cyan_hue_max", default=100))
        self.cyan_sv_min = int(params.get("perception.detector.cyan_sv_min", default=110))
        self.cyan_boost = float(params.get("perception.detector.cyan_boost", default=3.0))
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    def _mask(self, img: np.ndarray) -> np.ndarray:
        if self.mode == "bright":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
            return mask
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lo = cv2.inRange(hsv, (0, self.sat_min, self.val_min),
                         (self.hue_low_max, 255, 255))
        hi = cv2.inRange(hsv, (self.hue_high_min, self.sat_min, self.val_min),
                         (180, 255, 255))
        return cv2.bitwise_or(lo, hi)

    def detect(self, frame: CameraFrame) -> GateDetection | None:
        img = frame.image
        h, w = img.shape[:2]
        image_area = float(h * w)

        mask = cv2.morphologyEx(self._mask(img), cv2.MORPH_CLOSE, self._kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cyan = None
        if self.cyan_prior and self.mode == "red_hsv":
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            cyan = cv2.inRange(hsv, (self.cyan_hue_min, self.cyan_sv_min, self.cyan_sv_min),
                               (self.cyan_hue_max, 255, 255))
            if not cyan.any():
                cyan = None          # no racing line in scene: pure area

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
            # Several gates are visible along the track. Base score: area
            # (largest = nearest). Cyan prior: the racing line threads the
            # NEXT gate's opening, so a candidate with cyan inside its
            # opening outranks a merely-bigger one.
            score = area
            if cyan is not None:
                cmask = np.zeros(cyan.shape, dtype=np.uint8)
                cv2.fillPoly(cmask, [approx.reshape(-1, 2)], 255)
                if cv2.countNonZero(cv2.bitwise_and(cyan, cmask)) >= 12:
                    score *= self.cyan_boost
            if best is None or score > best[0]:
                best = (score, approx)

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
