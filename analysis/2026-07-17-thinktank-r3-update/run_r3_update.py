"""Think-tank ROUND-3 UPDATE pack — AGENTS.md DATA ANALYST item 5 (f)(g)(i)(h).

HEAD >= 84a9cdf. Priority: (f) Test A RERUN → (g) H3 → (i) row-consistency → (h) T3.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LOGS = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs")
FIX5 = ROOT / "fixtures" / "20260716T212744-phase5-closerange-frames"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.core.messages import CameraFrame, RelPose, StateEstimate  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from aigp.planning.race_planner import RacePlanner  # noqa: E402
from aigp.planning.vertical_terminal import top_bar_vertical_error  # noqa: E402

GATE_W = 1.6
GATE_H = 1.6
FX_NOM = 320.0
PRODUCT_NOM = FX_NOM * GATE_W  # 512
SCALE_MIN = 0.65  # HEAD default → product floor ≈ 333
SCALE_MAX = 1.5
D_STAR_BAR = 0.80  # top-bar center above opening (≈ H/2)
D_STAR_BANNER = 0.15  # R4: banner bottom above opening center
F1_ID = "20260716T203450-2ca531c3"
F2_ID = "20260716T212408-2ca531c3"
# Import helpers from prior pack
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-17-thinktank-r3"))
from run_round3_pack import (  # noqa: E402
    flight_paths,
    load_log,
    order_corners_tl_tr_br_bl,
    top_bar_from_corners,
)


def scale_gate_label(corners, t_vec, normal, img_w=640, img_h=360) -> dict:
    """Apply HEAD scale+grazing gate to a logged quad. killed=strip."""
    pts = order_corners_tl_tr_br_bl(np.asarray(corners, float).reshape(-1, 2))
    w_px = float(np.linalg.norm(pts[1] - pts[0]))
    h_px = float(np.linalg.norm(pts[3] - pts[0]))
    R = float(np.linalg.norm(t_vec))
    product = R * max(w_px, h_px)
    ratio = product / PRODUCT_NOM
    nz = abs(float(normal[2])) if normal is not None and len(normal) >= 3 else None
    scale_ok = SCALE_MIN <= ratio <= SCALE_MAX
    normal_ok = nz is None or nz >= 0.35
    killed = not (scale_ok and normal_ok)
    identity = "banner_strip" if killed else "top_bar"
    return {
        "w_px": w_px,
        "h_px": h_px,
        "R": R,
        "product": product,
        "ratio": ratio,
        "nz": nz,
        "scale_ok": scale_ok,
        "normal_ok": normal_ok,
        "killed": killed,
        "identity": identity,
        "d_star": D_STAR_BANNER if killed else D_STAR_BAR,
    }


def feature_from_corners(corners, img_h, img_w, identity: str):
    """Bar: top-edge mid. Banner/strip: bottom-edge mid of the detected quad
    (strip bottom ≈ banner bottom for flat banner-as-gate fits)."""
    pts = order_corners_tl_tr_br_bl(np.asarray(corners, float).reshape(-1, 2))
    if identity == "top_bar":
        a, b = pts[0], pts[1]
    else:
        a, b = pts[3], pts[2]  # bl, br — bottom of strip
    mid = 0.5 * (a + b)
    width_px = float(np.linalg.norm(b - a))
    if width_px < 1:
        return None
    cy0 = img_h / 2.0
    y_norm = (cy0 - float(mid[1])) / FX_NOM  # +UP
    span_norm = width_px / FX_NOM
    return y_norm, span_norm, mid, width_px


def collect_frames(vision: Path, t0: int, t_lo: float, t_hi: float):
    assembler = ChunkAssembler()
    frames = []
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        fid_f, sim_ns, jpeg = done
        t = (mono_ns - t0) / 1e9
        if t < t_lo:
            continue
        if t > t_hi:
            break
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            frames.append((t, fid_f, sim_ns, img))
    return frames


def nearest_frame(frames, t, tol=0.12):
    if not frames:
        return None
    fr = min(frames, key=lambda x: abs(x[0] - t))
    return fr if abs(fr[0] - t) <= tol else None


def score_bucket(errors, signed):
    errors = np.asarray(errors, float) if errors else np.array([])
    out = {
        "n_scored": int(len(errors)),
        "median_bias": float(np.median(errors)) if len(errors) else None,
        "p90_abs": float(np.percentile(np.abs(errors), 90)) if len(errors) else None,
        "sign_acc": float(np.mean(signed)) if signed else None,
        "n_sign_cases": len(signed),
        "release_bars": {
            "median_bias_lt_0.05": None,
            "p90_lt_0.15": None,
            "sign_acc_gt_0.99": None,
        },
    }
    if out["median_bias"] is not None:
        out["release_bars"]["median_bias_lt_0.05"] = abs(out["median_bias"]) < 0.05
        out["release_bars"]["p90_lt_0.15"] = out["p90_abs"] < 0.15
        out["release_bars"]["sign_acc_gt_0.99"] = (
            out["sign_acc"] is not None and out["sign_acc"] > 0.99
        )
    out["pass"] = all(
        v is True for v in out["release_bars"].values()
    ) if out["n_scored"] else False
    return out


# ---------------------------------------------------------------------------
# (f) Test A RERUN
# ---------------------------------------------------------------------------

def run_test_a_rerun(fid: str, t0, dets, max_samples: int = 100) -> dict:
    log, vision = flight_paths(fid)
    if not vision.exists():
        return {"error": f"no vision for {fid}", "path": str(vision)}

    # Trusted full-pose dets in 1.5–2.4 m that would SURVIVE scale gate as BAR
    # OR are killed as strip (still have corners for feature extract).
    band = [d for d in dets if 1.5 <= d["dist"] <= 2.4 and d.get("corners")]
    if not band:
        return {"error": "no dets in 1.5-2.4m band", "fid": fid}
    step = max(1, len(band) // max_samples)
    band = band[::step][:max_samples]

    want_ts = sorted(d["t"] for d in band)
    frames = collect_frames(vision, t0, want_ts[0] - 0.05, want_ts[-1] + 0.05)

    # Also redetect with HEAD scale-gate ON for kill labeling confirmation
    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    det = HsvGateDetector(params)

    by_id = {"top_bar": {"errors": [], "signed": []},
             "banner_strip": {"errors": [], "signed": []}}
    rows = []
    n_killed = 0
    n_bar = 0

    for d in band:
        fr = nearest_frame(frames, d["t"])
        if fr is None:
            continue
        _t, _fid, sim_ns, img = fr
        h, w = img.shape[:2]
        corners = np.asarray(d["corners"], float).reshape(-1, 2)
        lab = scale_gate_label(corners, _t_vec_from_det(d), d.get("normal"), w, h)
        identity = lab["identity"]
        if lab["killed"]:
            n_killed += 1
        else:
            n_bar += 1

        # Confirm with live detector on full frame when available
        det_live = det.detect(CameraFrame(frame_id=int(_fid), ts_ns=sim_ns, image=img))
        live_killed = None
        if det_live is not None:
            live_killed = det_live.rel_pose is None

        feat = feature_from_corners(corners, h, w, identity)
        if feat is None:
            continue
        y_norm, span_norm, mid, width_px = feat
        d_star = lab["d_star"]
        try:
            e_hat = top_bar_vertical_error(y_norm, span_norm, GATE_W, d_star)
        except ValueError:
            continue

        # Full-pose reference: opening-center vertical error +UP
        ref = -float(d["ty"])
        err = e_hat - ref
        by_id[identity]["errors"].append(err)
        if abs(ref) > 0.15:
            by_id[identity]["signed"].append(
                1.0 if np.sign(e_hat) == np.sign(ref) else 0.0
            )
        rows.append({
            "t": d["t"],
            "R": d["dist"],
            "identity": identity,
            "d_star": d_star,
            "ratio": lab["ratio"],
            "killed": lab["killed"],
            "live_killed": live_killed,
            "e_hat": e_hat,
            "ref": ref,
            "err": err,
            "ty": d["ty"],
        })

    all_err = by_id["top_bar"]["errors"] + by_id["banner_strip"]["errors"]
    all_sgn = by_id["top_bar"]["signed"] + by_id["banner_strip"]["signed"]
    out = {
        "fid": fid,
        "band": "1.5-2.4m",
        "d_star_bar": D_STAR_BAR,
        "d_star_banner": D_STAR_BANNER,
        "n_band": len(band),
        "n_bar_identity": n_bar,
        "n_banner_strip_identity": n_killed,
        "overall": score_bucket(all_err, all_sgn),
        "top_bar": score_bucket(by_id["top_bar"]["errors"], by_id["top_bar"]["signed"]),
        "banner_strip": score_bucket(
            by_id["banner_strip"]["errors"], by_id["banner_strip"]["signed"]
        ),
        "sample_rows": rows[:40],
    }
    return out


def _t_vec_from_det(d) -> list[float]:
    """Best available cam t for scale labeling."""
    if d.get("t_vec"):
        return list(d["t_vec"])
    # dets from load_log don't store t_vec — rebuild from ty,tz,dist
    ty = float(d["ty"])
    tz = float(d.get("tz", 0.0))
    # if tz missing/wrong, use slant remainder
    if abs(tz) < 0.05:
        tz = math.sqrt(max(1e-6, d["dist"] ** 2 - ty ** 2))
    tx = math.sqrt(max(0.0, d["dist"] ** 2 - ty ** 2 - tz ** 2))
    return [tx, ty, tz]


# ---------------------------------------------------------------------------
# (g) H3 census — visible-edge identity last 1.5 m
# ---------------------------------------------------------------------------

def red_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # washed red (repo detector bands approximate)
    m1 = cv2.inRange(hsv, (0, 80, 80), (12, 255, 255))
    m2 = cv2.inRange(hsv, (165, 80, 80), (180, 255, 255))
    return cv2.bitwise_or(m1, m2)


def project_gate_quad(t_cam, img_w=640, img_h=360, fx=FX_NOM):
    """Fronto-parallel gate corners tl,tr,br,bl in pixels from cam t (y-down)."""
    tx, ty, tz = (float(x) for x in t_cam)
    if tz < 0.2:
        return None
    hw, hh = GATE_W / 2.0, GATE_H / 2.0
    cx, cy = img_w / 2.0, img_h / 2.0
    corners3 = [
        (tx - hw, ty - hh, tz),
        (tx + hw, ty - hh, tz),
        (tx + hw, ty + hh, tz),
        (tx - hw, ty + hh, tz),
    ]
    px = []
    for x, y, z in corners3:
        if z < 0.1:
            return None
        px.append((cx + fx * x / z, cy + fx * y / z))
    return np.asarray(px, float)


def edge_visible(mask, p0, p1, search=8, min_frac=0.25) -> bool:
    h, w = mask.shape
    n = 16
    hits = 0
    for i in range(n):
        a = i / (n - 1)
        x = int(round(p0[0] * (1 - a) + p1[0] * a))
        y = int(round(p0[1] * (1 - a) + p1[1] * a))
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        y0, y1 = max(0, y - search), min(h, y + search + 1)
        x0, x1 = max(0, x - search), min(w, x + search + 1)
        if mask[y0:y1, x0:x1].any():
            hits += 1
    return (hits / n) >= min_frac


def banner_visible(mask, top_mid, top_span_px, search_up=None) -> bool:
    """Red mass above the projected top bar → banner."""
    h, w = mask.shape
    if search_up is None:
        search_up = max(12, int(0.35 * top_span_px))
    cx, cy = int(top_mid[0]), int(top_mid[1])
    half = max(8, int(0.35 * top_span_px))
    x0, x1 = max(0, cx - half), min(w, cx + half)
    y0, y1 = max(0, cy - search_up), max(0, cy - 2)
    if y1 <= y0 or x1 <= x0:
        return False
    region = mask[y0:y1, x0:x1]
    return float(np.count_nonzero(region)) / region.size > 0.04


def mask_structure_identity(mask) -> dict:
    """Border-touch + vertical mass split when projected edges are unreliable."""
    h, w = mask.shape
    ys, xs = np.where(mask > 0)
    if len(ys) == 0:
        return {k: False for k in ("left", "right", "top", "bottom", "banner")}
    touches = {
        "left": bool(mask[:, :4].any()),
        "right": bool(mask[:, -4:].any()),
        "top": bool(mask[:4, :].any()),
        "bottom": bool(mask[-4:, :].any()),
    }
    # Banner: substantial red in the upper 35% that is ABOVE the main blob mid
    mid_y = float(np.median(ys))
    upper = mask[: max(1, int(0.35 * h)), :]
    banner = float(np.count_nonzero(upper)) / upper.size > 0.02 and mid_y < 0.55 * h
    # Edge identity from bbox sides that touch red densely
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    band = 6
    vis = {
        "left": touches["left"] or (
            x0 < w * 0.25 and float(np.count_nonzero(mask[y0:y1 + 1, max(0, x0):min(w, x0 + band)])) > 20
        ),
        "right": touches["right"] or (
            x1 > w * 0.75 and float(np.count_nonzero(mask[y0:y1 + 1, max(0, x1 - band):x1 + 1])) > 20
        ),
        "top": touches["top"] or (
            y0 < h * 0.35 and float(np.count_nonzero(mask[max(0, y0):min(h, y0 + band), x0:x1 + 1])) > 20
        ),
        "bottom": touches["bottom"] or (
            y1 > h * 0.65 and float(np.count_nonzero(mask[max(0, y1 - band):y1 + 1, x0:x1 + 1])) > 20
        ),
        "banner": bool(banner or (touches["top"] and mid_y < 0.45 * h)),
    }
    return vis


def run_h3(fid: str, t0, states, dets) -> dict:
    log, vision = flight_paths(fid)
    if not vision.exists():
        return {"error": f"no vision for {fid}"}

    # Last 1.5 m: prefer STATE dist<=1.5; F2 never reaches that in STATE
    # (min ~2.0 m DR) so fall back to DET dist<=1.5, else closest 1.5 m of
    # STATE approach (min_dist .. min_dist+1.5).
    close = [s for s in states if s["dist"] <= 1.5 and s.get("t_vec")]
    range_source = "state_le_1.5"
    if not close:
        det_close = [d for d in dets if d["dist"] <= 1.5 and d.get("corners")]
        if det_close:
            range_source = "det_le_1.5"
            # Build pseudo-samples from dets, attach nearest state ty
            close = []
            for d in det_close:
                st = min(states, key=lambda s: abs(s["t"] - d["t"])) if states else None
                close.append({
                    "t": d["t"],
                    "dist": d["dist"],
                    "ty": st["ty"] if st else d["ty"],
                    "t_vec": _t_vec_from_det(d),
                    "_from_det": True,
                })
        else:
            range_source = "state_closest_span"
            if not states:
                return {"error": "no states", "fid": fid}
            dmin = min(s["dist"] for s in states)
            close = [s for s in states if s["dist"] <= dmin + 1.5 and s.get("t_vec")]

    if not close:
        return {"error": "no close samples for H3", "fid": fid}

    t_lo = min(s["t"] for s in close) - 0.05
    t_hi = max(s["t"] for s in close) + 0.05
    frames = collect_frames(vision, t0, t_lo, t_hi)
    if len(frames) < 5:
        for sl in sorted(FIX5.glob(f"{fid}*collision*.aigprec")) + sorted(
            FIX5.glob(f"{fid}*3m*.aigprec")
        ) + sorted(FIX5.glob(f"{fid}*.aigprec")):
            frames = collect_frames(sl, t0, t_lo, t_hi)
            if len(frames) >= 5:
                vision = sl
                break

    sampled = []
    last_t = -1e9
    for s in sorted(close, key=lambda x: x["t"]):
        if s["t"] - last_t >= 0.05:
            sampled.append(s)
            last_t = s["t"]

    census = []
    for s in sampled:
        fr = nearest_frame(frames, s["t"], tol=0.12)
        if fr is None:
            continue
        img = fr[3]
        h, w = img.shape[:2]
        mask = red_mask(img)
        if not mask.any():
            continue
        vis_mask = mask_structure_identity(mask)
        vis = dict(vis_mask)
        t_vec = s.get("t_vec")
        quad = project_gate_quad(t_vec, w, h) if t_vec else None
        if quad is not None:
            names = ["top", "right", "bottom", "left"]
            for i, name in enumerate(names):
                p0, p1 = quad[i], quad[(i + 1) % 4]
                # OR with projected-edge visibility
                if edge_visible(mask, p0, p1):
                    vis[name] = True
            top_mid = 0.5 * (quad[0] + quad[1])
            span = float(np.linalg.norm(quad[1] - quad[0]))
            if banner_visible(mask, top_mid, span):
                vis["banner"] = True
        border = {
            "touches_top": bool(mask[:3, :].any()),
            "touches_bottom": bool(mask[-3:, :].any()),
            "touches_left": bool(mask[:, :3].any()),
            "touches_right": bool(mask[:, -3:].any()),
        }
        census.append({
            "t": s["t"],
            "dist": s["dist"],
            "ty": s["ty"],
            **{f"vis_{k}": bool(v) for k, v in vis.items()},
            **border,
        })

    if not census:
        return {"error": "no H3 frames matched", "fid": fid, "n_frames": 0,
                "vision": str(vision), "range_source": range_source}

    by_dist = sorted(census, key=lambda r: -r["dist"])
    first_seen = {}
    for r in by_dist:
        for k in ("left", "right", "top", "bottom", "banner"):
            if r.get(f"vis_{k}") and k not in first_seen:
                first_seen[k] = {"dist": r["dist"], "t": r["t"]}

    closest = sorted(census, key=lambda r: r["dist"])[: max(1, len(census) // 5)]
    last_rates = {
        k: float(np.mean([1.0 if r.get(f"vis_{k}") else 0.0 for r in closest]))
        for k in ("left", "right", "top", "bottom", "banner")
    }
    # Prefer a structure that is actually present
    present = {k: v for k, v in last_rates.items() if v > 0}
    last_structure = max(present, key=present.get) if present else max(
        last_rates, key=last_rates.get
    )
    mean_ty_close = float(np.mean([r["ty"] for r in closest]))
    v2 = {
        "last_structure": last_structure,
        "last_rates": last_rates,
        "mean_ty_closest": mean_ty_close,
        "banner_last_implies_HIGH": last_structure == "banner",
        "state_says_HIGH": mean_ty_close > 0.1,
        "v2_consistent": (
            (last_structure == "banner" and mean_ty_close > 0.05)
            or (last_structure != "banner")
        ),
    }
    rates = {
        k: float(np.mean([1.0 if r.get(f"vis_{k}") else 0.0 for r in census]))
        for k in ("left", "right", "top", "bottom", "banner")
    }
    return {
        "fid": fid,
        "vision_used": str(vision),
        "range_source": range_source,
        "n_frames": len(census),
        "dist_span": [float(min(r["dist"] for r in census)),
                      float(max(r["dist"] for r in census))],
        "presence_rates": rates,
        "first_seen_as_range_decreases": first_seen,
        "transition_order_far_to_near": sorted(
            first_seen.keys(), key=lambda k: -first_seen[k]["dist"]
        ),
        "v2": v2,
        "rows": census,
    }


# ---------------------------------------------------------------------------
# (i) F2 ROW-CONSISTENCY
# ---------------------------------------------------------------------------

def run_row_consistency(fid: str, t0, dets, states) -> dict:
    """Believed ty=+0.31 at the F2 conflict predicts opening-center row vs mask.

    NOTE: STATE range at the conflict is ~2.78 m (DR); the 1.67 m figure is the
    DETECTION R. AGENTS' one-liner uses believed ty with that geometry.
    """
    log, vision = flight_paths(fid)
    # Focus: DET near 1.67 m with ty~-0.95, paired STATE ty~+0.31 at same t
    focus_dets = [
        d for d in dets
        if 1.55 <= d["dist"] <= 1.8 and d.get("corners") and d["ty"] < -0.5
    ]
    if not focus_dets:
        focus_dets = [d for d in dets if abs(d["dist"] - 1.67) < 0.15 and d.get("corners")]
    if not focus_dets:
        return {"error": "no focus det near 1.67m"}

    det = min(focus_dets, key=lambda d: abs(d["dist"] - 1.67))
    s = min(states, key=lambda x: abs(x["t"] - det["t"])) if states else None
    if s is None:
        return {"error": "no state near focus det"}

    t_vec = s.get("t_vec") or [0.0, s["ty"], math.sqrt(max(0.1, s["dist"] ** 2 - s["ty"] ** 2))]
    tx, ty, tz = (float(x) for x in t_vec)
    ty_det = float(det["ty"])
    tz_det = float(det.get("tz") or _t_vec_from_det(det)[2])

    frames = collect_frames(vision, t0, det["t"] - 0.25, det["t"] + 0.25)
    fr = nearest_frame(frames, det["t"], tol=0.15)
    if fr is None:
        for sl in sorted(FIX5.glob(f"{fid}*.aigprec")):
            frames = collect_frames(sl, t0, det["t"] - 0.3, det["t"] + 0.3)
            fr = nearest_frame(frames, det["t"], tol=0.2)
            if fr is not None:
                vision = sl
                break
    if fr is None:
        return {"error": "no frame at focus", "t": det["t"], "dist_det": det["dist"]}

    img = fr[3]
    h, w = img.shape[:2]
    cy = h / 2.0
    # (1) Believed STATE pose → opening-center row
    row_believed_state = cy + FX_NOM * (ty / max(tz, 0.1))
    # (2) AGENTS one-liner geometry: believed ty=+0.31 at DET R=1.67
    #     (use det's tz scale with believed ty)
    row_believed_at_1_67 = cy + FX_NOM * (ty / max(tz_det, 0.1))
    # (3) Counterfactual: detection ty at detection depth
    row_if_det = cy + FX_NOM * (ty_det / max(tz_det, 0.1))

    mask = red_mask(img)
    ys, xs = np.where(mask > 0)
    if len(ys) == 0:
        return {"error": "empty red mask at focus"}
    in_band = (xs > w * 0.15) & (xs < w * 0.85)
    ys_b = ys[in_band] if in_band.any() else ys
    row_mask_top = float(ys_b.min())
    row_mask_bottom = float(ys_b.max())
    row_mask_mid = 0.5 * (row_mask_top + row_mask_bottom)

    # Opening-center proxy: if det has corners, use their center row
    row_quad = None
    if det.get("corners"):
        pts = np.asarray(det["corners"], float).reshape(-1, 2)
        row_quad = float(pts[:, 1].mean())

    ref_row = row_quad if row_quad is not None else row_mask_mid
    disagree_believed = abs(ref_row - row_believed_at_1_67)
    disagree_state = abs(ref_row - row_believed_state)
    disagree_det = abs(ref_row - row_if_det)

    ann = img.copy()
    cv2.line(ann, (0, int(row_believed_at_1_67)), (w - 1, int(row_believed_at_1_67)),
             (0, 255, 255), 2)
    cv2.line(ann, (0, int(row_if_det)), (w - 1, int(row_if_det)), (255, 0, 255), 2)
    cv2.line(ann, (0, int(ref_row)), (w - 1, int(ref_row)), (0, 255, 0), 2)
    cv2.putText(ann, f"believed ty={ty:+.2f}@1.67 row={row_believed_at_1_67:.0f}",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(ann, f"det ty={ty_det:+.2f} row={row_if_det:.0f}",
                (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    cv2.putText(ann, f"mask/quad row={ref_row:.0f} dBel={disagree_believed:.0f}px",
                (10, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    out_img = OUT / "frames" / "f2_row_consistency.jpg"
    out_img.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_img), ann)

    verdict = (
        "BELIEVED_ROW_DISAGREES"
        if disagree_believed > 40
        else "BELIEVED_ROW_PLAUSIBLE"
    )
    better = "det_ty" if disagree_det + 15 < disagree_believed else (
        "believed_ty" if disagree_believed + 15 < disagree_det else "ambiguous"
    )

    return {
        "t": det["t"],
        "dist_det": det["dist"],
        "dist_state": s["dist"],
        "age_state": s.get("age"),
        "ty_believed": ty,
        "tz_believed_state": tz,
        "ty_det": ty_det,
        "tz_det": tz_det,
        "row_believed_at_det_depth": row_believed_at_1_67,
        "row_believed_state_pose": row_believed_state,
        "row_if_det_ty": row_if_det,
        "row_mask_mid": row_mask_mid,
        "row_quad_center": row_quad,
        "row_ref_used": ref_row,
        "disagree_px_believed_at_1_67": disagree_believed,
        "disagree_px_believed_state": disagree_state,
        "disagree_px_det": disagree_det,
        "better_match": better,
        "verdict": verdict,
        "frame": str(out_img.relative_to(OUT)),
        "vision": str(vision),
        "note": (
            "STATE at conflict is ~2.78m DR while det R=1.67m; believed ty=+0.31 "
            "at det depth predicts an opening-center row the actual mask/quad "
            "violently disagrees with if the image matches det ty=-0.95 "
            "(pairs with D5 product≪512)."
        ),
    }


# ---------------------------------------------------------------------------
# (h) T3 — F1 no-arm replay
# ---------------------------------------------------------------------------

def run_t3_f1(log_path: Path) -> dict:
    """Replay F1 setpoints through RacePlanner; confirm double-climb unreachable."""
    params = ParamSet.load(str(ROOT / "config" / "params_default.json"))
    planner = RacePlanner(params)
    events = []
    double_climb_hits = 0
    gap_entries = 0
    vetoes = 0
    arms = 0

    # Stream flight.jsonl chronologically; feed planner with reconstructed StateEstimate
    t0 = None
    last_phase = None
    in_gap = False
    vz_at_gap_entry = None
    gap_bias_at_entry = None

    with log_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            topic = rec["topic"]
            d = rec["data"]
            if topic != "state":
                continue
            gr = d.get("gate_rel")
            if not gr or gr.get("t") is None:
                continue
            t_vec = np.array([float(x) for x in gr["t"]], dtype=float)
            age = float(d.get("gate_rel_age_s") or 0.0)
            q = d.get("q_att") or [1, 0, 0, 0]
            center = d.get("gate_center_px")
            if center is None and d.get("gate_center"):
                center = d["gate_center"]
            # image size default
            state = StateEstimate(
                ts_ns=mono,
                q_att=np.array(q, dtype=float),
                omega=np.zeros(3),
                v_world=np.zeros(3),
                gate_rel=RelPose(t=t_vec, normal=np.array(
                    gr.get("normal") or [0.0, 0.0, -1.0], dtype=float
                )),
                gate_rel_age_s=age,
                gate_center_px=tuple(center) if center else (320.0, 180.0),
                image_size=(640, 360),
                healthy=True,
            )
            mode = "race"
            sp = planner.plan(mono, mode, state, None)
            if sp.phase != "commit":
                in_gap = False
                last_phase = sp.phase
                continue

            # Track gap entry
            seeing = age <= planner.blind_age_s
            if seeing:
                in_gap = False
                vz_at_gap_entry = None
            elif not in_gap:
                # first blind sample in this gap
                in_gap = True
                gap_entries += 1
                vz_at_gap_entry = float(sp.v_body[2])
                gap_bias_at_entry = planner._gap_bias
                if gap_bias_at_entry == 0.0:
                    vetoes += 1
                elif gap_bias_at_entry and gap_bias_at_entry > 0:
                    arms += 1
                events.append({
                    "t": t,
                    "age": age,
                    "dist": float(np.linalg.norm(t_vec)),
                    "ty": float(t_vec[1]),
                    "vz_cmd": vz_at_gap_entry,
                    "gap_bias": gap_bias_at_entry,
                    "event": "gap_entry",
                })
            else:
                # mid-gap: insurance must not newly add climb on top of climb
                if (
                    vz_at_gap_entry is not None
                    and vz_at_gap_entry < -0.05  # already climbing at entry
                    and planner._gap_bias
                    and planner._gap_bias > 0
                ):
                    # Would mean insurance armed while already climbing — forbidden
                    double_climb_hits += 1
                    events.append({
                        "t": t,
                        "age": age,
                        "vz_cmd": float(sp.v_body[2]),
                        "gap_bias": planner._gap_bias,
                        "event": "DOUBLE_CLIMB_VIOLATION",
                    })
                # Also: mid-gap re-arm (bias changing from 0 to >0) is forbidden
                if gap_bias_at_entry == 0.0 and planner._gap_bias and planner._gap_bias > 0:
                    double_climb_hits += 1
                    events.append({
                        "t": t,
                        "event": "REARM_VIOLATION",
                        "gap_bias": planner._gap_bias,
                    })

            last_phase = sp.phase

    return {
        "fid": F1_ID,
        "gap_entries": gap_entries,
        "vetoes_at_entry": vetoes,
        "arms_at_entry": arms,
        "double_climb_violations": double_climb_hits,
        "structurally_unreachable": double_climb_hits == 0,
        "blind_age_s": planner.blind_age_s,
        "blind_climb_bias": planner.blind_climb_bias,
        "events_sample": events[:30],
        "verdict": (
            "PASS — double climb structurally unreachable under no-arm rule"
            if double_climb_hits == 0
            else "FAIL — double-climb / re-arm observed"
        ),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(bundle: dict):
    lines = [
        "# Think-tank ROUND-3 UPDATE pack",
        "",
        "AGENTS.md DATA ANALYST item 5 (HEAD ≥ `84a9cdf`).",
        "Order: **(f) Test A RERUN** → **(g) H3** → **(i) row-consistency** → **(h) T3**.",
        "",
        "## Notes carried forward",
        "",
        "1. REAL_GATE_CONSISTENT band (product 272–308) still carried the ty conflict; "
        "HEAD `scale_min=0.65` (floor ≈333) rejects it — analyst agrees; no "
        "counterexample frame with product<333 and verified-true pose found.",
        "2. Prior Test A failure was d*=0.8 vs banner geometry; R4 d*_banner=0.15.",
        "",
        "## (f) Test A RERUN — bar vs banner, R4-calibrated d*",
        "",
        f"- d*_bar = {D_STAR_BAR} m · d*_banner = {D_STAR_BANNER} m (R4)",
        "- Band: **1.5–2.4 m**. Identity: HEAD scale-gate kill ⇒ `banner_strip`.",
        "",
    ]
    for fid, ta in (bundle.get("test_a") or {}).items():
        lines.append(f"### `{fid}`")
        if ta.get("error"):
            lines.append(f"- ERROR: {ta['error']}")
            continue
        lines += [
            f"- n_bar={ta.get('n_bar_identity')} n_banner_strip={ta.get('n_banner_strip_identity')}",
            "",
            "| bucket | n | median bias | P90 | sign acc | bars |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for name in ("overall", "top_bar", "banner_strip"):
            b = ta.get(name) or {}
            rb = b.get("release_bars") or {}
            bars = (
                f"med={rb.get('median_bias_lt_0.05')} "
                f"p90={rb.get('p90_lt_0.15')} "
                f"sign={rb.get('sign_acc_gt_0.99')}"
            )
            lines.append(
                f"| {name} | {b.get('n_scored')} | {b.get('median_bias')} | "
                f"{b.get('p90_abs')} | {b.get('sign_acc')} | {bars} |"
            )
        lines.append("")

    lines += ["", "## (g) H3 — visible-edge census (last 1.5 m)", ""]
    for fid, h3 in (bundle.get("h3") or {}).items():
        lines.append(f"### `{fid}`")
        if h3.get("error"):
            lines.append(f"- ERROR: {h3['error']}")
            continue
        lines += [
            f"- n_frames={h3.get('n_frames')} dist_span={h3.get('dist_span')}",
            f"- presence_rates={h3.get('presence_rates')}",
            f"- first_seen (as range decreases)={h3.get('first_seen_as_range_decreases')}",
            f"- range_source={h3.get('range_source')}",
            f"- transition_order_far_to_near={h3.get('transition_order_far_to_near')}",
            f"- V2={h3.get('v2')}",
            "",
        ]

    lines += ["", "## (i) F2 ROW-CONSISTENCY", "", f"{json.dumps(bundle.get('row_consistency'), indent=2)}", ""]
    lines += ["", "## (h) T3 — F1 no-arm replay", "", f"{json.dumps(bundle.get('t3'), indent=2)}", ""]
    lines += [
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`",
        "- `test_a_samples.csv`, `h3_f1.csv`, `h3_f2.csv`",
        "- `frames/f2_row_consistency.jpg`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frames").mkdir(exist_ok=True)

    # Patch load_log dets to keep tz
    # (already in run_round3_pack)

    bundle = {"test_a": {}, "h3": {}, "row_consistency": {}, "t3": {}}

    print("Loading F1/F2 logs…", flush=True)
    log1, vis1 = flight_paths(F1_ID)
    log2, vis2 = flight_paths(F2_ID)
    print(f"  F1 vision={vis1.exists()} {vis1}", flush=True)
    print(f"  F2 vision={vis2.exists()} {vis2}", flush=True)
    t0_1, states1, dets1, _, _, _ = load_log(log1)
    t0_2, states2, dets2, _, _, _ = load_log(log2)
    # Enrich dets with tz from rel_pose if missing — load_log already has tz
    for d in dets1 + dets2:
        if "t_vec" not in d:
            d["t_vec"] = _t_vec_from_det(d)

    print("=== (f) Test A RERUN ===", flush=True)
    for fid, t0, dets in ((F1_ID, t0_1, dets1), (F2_ID, t0_2, dets2)):
        print(f"  {fid}", flush=True)
        bundle["test_a"][fid] = run_test_a_rerun(fid, t0, dets)
        ta = bundle["test_a"][fid]
        if not ta.get("error"):
            o = ta["overall"]
            print(
                f"    overall n={o['n_scored']} med={o['median_bias']} "
                f"p90={o['p90_abs']} sign={o['sign_acc']} pass={o['pass']}",
                flush=True,
            )
            print(
                f"    bar n={ta['top_bar']['n_scored']} "
                f"banner n={ta['banner_strip']['n_scored']}",
                flush=True,
            )

    # CSV samples
    with (OUT / "test_a_samples.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "fid", "t", "R", "identity", "d_star", "ratio", "killed",
                "live_killed", "e_hat", "ref", "err", "ty",
            ],
        )
        w.writeheader()
        for fid, ta in bundle["test_a"].items():
            for r in ta.get("sample_rows") or []:
                w.writerow({"fid": fid, **r})

    print("=== (g) H3 census ===", flush=True)
    for fid, t0, states, dets in (
        (F1_ID, t0_1, states1, dets1),
        (F2_ID, t0_2, states2, dets2),
    ):
        print(f"  {fid}", flush=True)
        bundle["h3"][fid] = run_h3(fid, t0, states, dets)
        h3 = bundle["h3"][fid]
        print(f"    {h3.get('error') or h3.get('v2')}", flush=True)
        rows = h3.get("rows") or []
        if rows:
            csv_path = OUT / f"h3_{'f1' if '203450' in fid else 'f2'}.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)

    print("=== (i) F2 ROW-CONSISTENCY ===", flush=True)
    bundle["row_consistency"] = run_row_consistency(F2_ID, t0_2, dets2, states2)
    print(bundle["row_consistency"].get("verdict"), bundle["row_consistency"], flush=True)

    print("=== (h) T3 F1 no-arm replay ===", flush=True)
    bundle["t3"] = run_t3_f1(log1)
    print(bundle["t3"].get("verdict"), flush=True)

    # Agree note on scale threshold
    bundle["scale_threshold_note"] = {
        "agree_with_scale_min_0_65": True,
        "counterexample_product_lt_333_verified_true": None,
        "reason": (
            "F2 product 272-308 band shared the same ty conflict as narrower "
            "garbage; no verified-true pose found below product 333."
        ),
    }

    write_report(bundle)
    (OUT / "summary.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8"
    )
    print("Wrote", OUT / "report.md", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
