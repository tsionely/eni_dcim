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

Close-range additions (Phase 5, analysis 2026-07-16-phase5-closerange —
every recorded flight went detector-blind at ~6.4m and never re-fixed):

  - washed-red branch: near the gate the drone flies inside the racing
    line's glow bloom, which washes the red ring to bright PINK
    (measured on the real frames: H~152, S~40-100, V~248 — outside both
    red hue bands and below the sat floor). A second mask branch accepts
    bright magenta/rose pixels that are red-dominant in BGR.
  - box fallback: the AI-GP banner merging with the ring outline and the
    bloom cutting the bottom bar break the convex-4-gon test even when
    the ring is plainly visible. When no exact quad exists, large
    ring-like components are boxed with minAreaRect and the box corners
    go to PnP (close range only — box_min_area_frac).

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
        self.washed_red = bool(params.get("perception.detector.washed_red", default=True))
        self.washed_hue_min = int(params.get("perception.detector.washed_hue_min", default=135))
        self.washed_sat_min = int(params.get("perception.detector.washed_sat_min", default=20))
        self.washed_val_min = int(params.get("perception.detector.washed_val_min", default=150))
        self.washed_rg_min = int(params.get("perception.detector.washed_rg_min", default=20))
        self.box_fallback = bool(params.get("perception.detector.box_fallback", default=True))
        self.box_min_area_frac = float(params.get("perception.detector.box_min_area_frac",
                                                  default=0.025))
        self.box_min_fill = float(params.get("perception.detector.box_min_fill",
                                             default=0.2))
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
        mask = cv2.bitwise_or(lo, hi)
        if self.washed_red:
            # Bloom-washed ring: bright magenta/rose AND red-dominant.
            # (Plain HSV magenta alone also matches white bloom cores.)
            washed = cv2.inRange(
                hsv, (self.washed_hue_min, self.washed_sat_min, self.washed_val_min),
                (180, 255, 255))
            b, g, r = cv2.split(img)
            rdom = cv2.inRange(cv2.subtract(r, g), self.washed_rg_min, 255)
            rbright = cv2.inRange(r, self.washed_val_min, 255)
            washed = cv2.bitwise_and(washed, cv2.bitwise_and(rdom, rbright))
            mask = cv2.bitwise_or(mask, washed)
        return mask

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

        def cyan_score(base: float, poly: np.ndarray) -> float:
            if cyan is None:
                return base
            cmask = np.zeros(cyan.shape, dtype=np.uint8)
            cv2.fillPoly(cmask, [poly.reshape(-1, 2).astype(np.int32)], 255)
            if cv2.countNonZero(cv2.bitwise_and(cyan, cmask)) >= 12:
                return base * self.cyan_boost
            return base

        best: tuple[float, np.ndarray, float] | None = None
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
            score = cyan_score(area, approx)
            if best is None or score > best[0]:
                best = (score, approx, 1.0)

        mask_frac = float(cv2.countNonZero(mask)) / image_area
        if (best is None and self.box_fallback and self.mode == "red_hsv"
                and mask_frac < 0.35):
            # Close-range rescue: the ring is big and plainly red but its
            # outline is not a clean convex quad (banner merged on top,
            # bloom cut the bottom bar -> "U"). minAreaRect of the broken
            # component still spans the ring's outer corners, and a fix
            # with ~10% pose error beats dead-reckoning drift. Gated to
            # large components so far detection stays exact-quad only, and
            # skipped entirely when the mask covers a wild fraction of the
            # frame (garbage scene — nothing here is a gate).
            for contour in contours:
                area = cv2.contourArea(contour)
                if area / image_area > self.max_area_frac:
                    continue
                rect = cv2.minAreaRect(contour)
                bw, bh = rect[1]
                box_area = bw * bh
                if box_area / image_area < self.box_min_area_frac:
                    continue
                if max(bw, bh) > 2.2 * max(min(bw, bh), 1e-6):
                    continue                 # sliver (gate leaving the FOV)
                # Fill ratio: a broken ring still paints ~25-50% of its
                # box; sparse speckle merged by the closing kernel paints
                # almost nothing and must not become a giant phantom box.
                if area < self.box_min_fill * box_area:
                    continue
                box = cv2.boxPoints(rect)
                score = cyan_score(box_area, box)
                if best is None or score > best[0]:
                    best = (score, box, 0.6)

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
            confidence=best[2],
        )
