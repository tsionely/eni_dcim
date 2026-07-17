"""GateCloseTracker: model-based edge tracking for the final meters.

The acquisition detector needs the whole ring as a clean convex quad; at
close range that stops being available (border clipping, the AI-GP banner
merging into the outline, the racing line's bloom cutting bars) exactly
when guidance needs fixes the most. This tracker closes that gap
(think-tank round 2 design, merged with round 1's n-of-4 idea):

    1. project the PREDICTED gate quad (dead-reckoned by the estimator)
       into the image,
    2. run 1D searches along each visible edge's normal for the red-mask
       boundary,
    3. solve a robust translation-only update (IRLS + Huber), truncating
       unobservable directions via SVD — a single visible bar is a valid
       1D measurement, never a failure,
    4. hand back a lower-confidence GateDetection; the estimator applies
       it to POSITION only (velocity keeps needing full fixes: a fix
       derived from the prediction must not also confirm the prediction's
       derivative — that is the circularity trap).

Fronto-parallel v1: gate orientation is frozen (head-on approach; the
normal search corrects translation, which is what the last meters need).
The caller enforces the solo-duration cap: without a fresh full-detector
fix for perception.close_tracker.max_solo_s, tracking stops rather than
letting the loop feed on itself.
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import CameraFrame, GateDetection, RelPose
from aigp.core.params import ParamSet
from aigp.perception.camera import PinholeCamera
from aigp.perception.certificate import SidePairCertificate
from aigp.perception.gate_detector_hsv import HsvGateDetector, order_corners


class GateCloseTracker:
    def __init__(self, params: ParamSet, detector: HsvGateDetector) -> None:
        p = params
        self.enabled = bool(p.get("perception.close_tracker.enabled", default=True))
        self.max_range = float(p.get("perception.close_tracker.max_range_m", default=7.0))
        self.search_px = int(p.get("perception.close_tracker.search_px", default=20))
        self.samples_per_edge = int(p.get("perception.close_tracker.samples_per_edge",
                                          default=12))
        self.max_step_m = float(p.get("perception.close_tracker.max_step_m", default=0.6))
        self.min_support = int(p.get("perception.close_tracker.min_support", default=10))
        self.max_solo_s = float(p.get("perception.close_tracker.max_solo_s", default=1.0))
        self.gate_w = float(p.get("perception.gate.width_m"))
        self.gate_h = float(p.get("perception.gate.height_m"))
        self.detector = detector          # shares the (washed-red) mask
        self.camera = PinholeCamera(
            float(p.get("perception.camera.fov_deg")),
            float(p.get("perception.camera.mount_pitch_deg", default=0.0)))
        r = self.camera._mount_rot
        self._derot_to_opt = r.T if r is not None else np.eye(3)
        self.certificate = SidePairCertificate()

    # ----------------------------------------------------------- geometry

    def _project(self, pts_derot: np.ndarray, k: np.ndarray) -> np.ndarray:
        pts_opt = pts_derot @ self._derot_to_opt.T
        z = pts_opt[:, 2:3]
        uv = pts_opt[:, :2] / z
        return np.stack([k[0, 0] * uv[:, 0] + k[0, 2],
                         k[1, 1] * uv[:, 1] + k[1, 2]], axis=1), pts_opt

    def _corners_derot(self, t: np.ndarray) -> np.ndarray:
        hw, hh = self.gate_w / 2.0, self.gate_h / 2.0
        # tl, tr, br, bl in the de-rotated camera frame (x right, y down).
        return t + np.array([[-hw, -hh, 0.0], [hw, -hh, 0.0],
                             [hw, hh, 0.0], [-hw, hh, 0.0]])

    # ------------------------------------------------------------ tracking

    def track(self, frame: CameraFrame, prior: RelPose) -> GateDetection | None:
        if not self.enabled:
            return None
        t = np.asarray(prior.t, dtype=np.float64).copy()
        rng = float(np.linalg.norm(t))
        if not np.isfinite(rng) or rng > self.max_range or t[2] < 0.3:
            return None

        img = frame.image
        h, w = img.shape[:2]
        k = self.camera.matrix(w, h)
        mask = self.detector.red_mask(img)
        if not mask.any():
            return None

        for _ in range(2):                      # measure -> solve, twice
            corners_derot = self._corners_derot(t)
            px, opt = self._project(corners_derot, k)
            if (opt[:, 2] <= 0.1).any():
                return None
            center_px = px.mean(axis=0)
            rows_a, rows_b, offsets = [], [], []
            edge_ids = []
            edge_widths: dict[int, list[float]] = {}
            edge_offs: dict[int, list[float]] = {}
            for e in range(4):
                p0, p1 = px[e], px[(e + 1) % 4]
                edge = p1 - p0
                elen = float(np.linalg.norm(edge))
                if elen < 8.0:
                    continue
                n2 = np.array([edge[1], -edge[0]]) / elen
                # Outward: away from the projected quad center.
                mid = (p0 + p1) / 2.0
                if float(np.dot(n2, mid - center_px)) < 0:
                    n2 = -n2
                for s in np.linspace(0.12, 0.88, self.samples_per_edge):
                    sp = p0 + s * edge
                    hit = self._edge_offset(mask, sp, n2, w, h)
                    if hit is None:
                        continue
                    off, bar_w = hit
                    edge_widths.setdefault(e, []).append(bar_w)
                    edge_offs.setdefault(e, []).append(off)
                    # Jacobian of the pixel along n2 w.r.t. t (derot frame):
                    # P_opt = R^T (t + c); dpx/dP_opt via pinhole; dP_opt/dt = R^T.
                    p_opt = (1 - s) * opt[e] + s * opt[(e + 1) % 4]
                    x, y, z = p_opt
                    dpi = np.array([[k[0, 0] / z, 0.0, -k[0, 0] * x / z / z],
                                    [0.0, k[1, 1] / z, -k[1, 1] * y / z / z]])
                    rows_a.append(n2 @ dpi @ self._derot_to_opt)
                    rows_b.append(off)
                    edge_ids.append(e)
            if len(rows_b) < self.min_support or len(set(edge_ids)) < 2:
                return None
            a = np.asarray(rows_a)
            b = np.asarray(rows_b, dtype=np.float64)
            delta = self._solve(a, b)
            if delta is None:
                return None
            step = float(np.linalg.norm(delta))
            if step > self.max_step_m:
                delta = delta * (self.max_step_m / step)
            t = t + delta

        if float(np.linalg.norm(t - prior.t)) > self.max_step_m * 1.5:
            return None                       # ran away from the prior
        # Certificate update from the final iteration's side-pair
        # measurements (edges: 1=right, 3=left; outward offsets widen).
        mid_l = (px[3] + px[0]) / 2.0
        mid_r = (px[1] + px[2]) / 2.0
        sep_pred = float(np.linalg.norm(mid_r - mid_l))
        med = lambda v: float(np.median(v)) if v else 0.0
        sep_meas = sep_pred + med(edge_offs.get(1)) + med(edge_offs.get(3))
        fx_w = float(k[0, 0]) * self.gate_w
        n_att = float(self.samples_per_edge)
        self.certificate.update(
            frame.ts_ns, float(prior.t[2]), sep_pred, sep_meas, fx_w,
            edge_widths.get(3, []), edge_widths.get(1, []),
            len(edge_widths.get(3, [])) / n_att,
            len(edge_widths.get(1, [])) / n_att)
        corners_derot = self._corners_derot(t)
        px, _ = self._project(corners_derot, k)
        corners = order_corners(px)
        return GateDetection(
            ts_ns=frame.ts_ns,
            corners_px=corners,
            center_px=(float(px[:, 0].mean()), float(px[:, 1].mean())),
            image_size=(w, h),
            rel_pose=RelPose(t=t, normal=np.asarray(prior.normal, dtype=float)),
            confidence=0.5,
            cert_status=self.certificate.status_at(frame.ts_ns),
        )

    def _edge_offset(self, mask: np.ndarray, sp: np.ndarray, n2: np.ndarray,
                     w: int, h: int) -> tuple[float, float] | None:
        """Scan outside-in along the outward normal for the red boundary.

        Returns (offset, bar_width_px): offset = signed distance from the
        predicted edge to the OUTER red boundary; bar_width_px = length of
        the contiguous red run inward from it (the bar's thickness along
        the normal — the certificate's bar-ness invariant lives on it: a
        banner sheet edge or pillar has no bounded red run at bar width).
        """
        r = self.search_px
        run = 0
        start = None
        for s in range(r, -r - 1, -1):
            x = int(round(sp[0] + n2[0] * s))
            y = int(round(sp[1] + n2[1] * s))
            if x < 0 or y < 0 or x >= w or y >= h:
                run = 0
                continue
            if mask[y, x]:
                run += 1
                if run >= 2 and start is None:
                    start = s + 1             # first ON of the run
            else:
                if start is not None:
                    return float(start), float(start - (s + 1))
                run = 0
        if start is not None:                 # red continues to scan end
            return float(start), float(start + r)
        return None

    @staticmethod
    def _solve(a: np.ndarray, b: np.ndarray) -> np.ndarray | None:
        """IRLS (Huber, 3px) translation solve with SVD truncation: axes the
        visible edges cannot observe are left UNTOUCHED, not extrapolated."""
        wgt = np.ones(len(b))
        delta = np.zeros(3)
        for _ in range(3):
            aw = a * wgt[:, None]
            bw = b * wgt
            u, s, vt = np.linalg.svd(aw, full_matrices=False)
            if s[0] < 1e-9:
                return None
            s_inv = np.array([1.0 / si if si > 0.05 * s[0] else 0.0 for si in s])
            delta = vt.T @ (s_inv * (u.T @ bw))
            resid = np.maximum(np.abs(b - a @ delta), 1e-9)
            wgt = np.where(resid <= 3.0, 1.0, 3.0 / resid)
        if not np.isfinite(delta).all():
            return None
        return delta
