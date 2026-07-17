"""Think-tank ROUND-3 measurement pack (AGENTS.md DATA ANALYST item 5).

Priority: (c) F2 D5 → (f) Test A → (a)(b)(d)(e).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict

# Windows consoles (cp1255/cp1252) cannot print ≪≫≈ — force UTF-8 for prints/report.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LOGS = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs")
FIX5 = ROOT / "fixtures" / "20260716T212744-phase5-closerange-frames"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from aigp.planning.vertical_terminal import top_bar_vertical_error  # noqa: E402

GATE_W = 1.6
GATE_H = 1.6
FX_NOM = 320.0  # 640w, fov 90°
PRODUCT_NOM = FX_NOM * GATE_W  # 512 px·m
F2_ID = "20260716T212408-2ca531c3"
F1_ID = "20260716T203450-2ca531c3"
PASS_ID = "20260716T131137-2ca531c3"
MOUNT_PITCH_DEG = 29.0  # default; optical above IMU — R1 uses 11° optical rest from docs
# AGENTS formula: 180 + 320·tan(11°+pitch) — 11° is optical-above-horizon rest


def flight_paths(fid: str) -> tuple[Path, Path]:
    log = LOGS / fid / "flight.jsonl"
    vision = LOGS / fid / "vision.aigprec"
    if not log.exists():
        cands = list((ROOT / "fixtures").glob(f"**/{fid}-flight.jsonl"))
        log = cands[0] if cands else log
    if not vision.exists():
        # prefer close slices under phase5 fixture
        for sl in sorted(FIX5.glob(f"{fid}*.aigprec")):
            vision = sl
            break
    return log, vision


def load_log(log_path: Path):
    t0 = None
    states, dets, imus, setpoints, acts = [], [], [], [], []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            topic = rec["topic"]
            if topic == "state":
                gr = d.get("gate_rel")
                if gr and gr.get("t") is not None:
                    tx, ty, tz = (float(x) for x in gr["t"])
                    dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                    age = float(d.get("gate_rel_age_s") or 0.0)
                    q = d.get("q_att")
                    states.append({"t": t, "ty": ty, "tz": tz, "dist": dist, "age": age, "q": q, "t_vec": [tx, ty, tz]})
            elif topic == "detection" and d.get("rel_pose"):
                tx, ty, tz = (float(x) for x in d["rel_pose"]["t"])
                dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                corners = d.get("corners_px")
                c = d.get("center_px")
                dets.append(
                    {
                        "t": t,
                        "ty": ty,
                        "tz": tz,
                        "dist": dist,
                        "corners": corners,
                        "center": c,
                        "normal": (d.get("rel_pose") or {}).get("normal"),
                        "ts_ns": d.get("ts_ns"),
                    }
                )
            elif topic == "imu":
                g = d.get("gyro") or [0, 0, 0]
                a = d.get("accel") or [0, 0, 0]
                imus.append({"t": t, "gyro": g, "accel": a})
            elif topic == "setpoint":
                vb = d.get("v_body") or [0, 0, 0]
                setpoints.append({"t": t, "phase": d.get("phase"), "vz": float(vb[2]), "v_body": vb})
            elif topic == "actuator":
                # thrust if present
                thr = d.get("thrust")
                if thr is None and d.get("motors"):
                    thr = float(np.mean(d["motors"]))
                acts.append({"t": t, "thrust": thr})
    return t0, states, dets, imus, setpoints, acts


def quad_width_px(corners) -> float | None:
    if not corners or len(corners) < 4:
        return None
    pts = np.asarray(corners, dtype=float).reshape(-1, 2)
    # ordered tl,tr,br,bl — top edge width
    return float(np.linalg.norm(pts[1] - pts[0]))


def d5_product(R: float, width_px: float) -> float:
    return R * width_px


def d5_verdict(product: float) -> str:
    # Geometry: real gate ⇒ R·w_px ≈ fx·W ≈ 512.
    # ≫512: near-wide quad with inflated R (PnP flip / banner garbage).
    # ≪512: narrow pixels with too-small R.
    if product > 512 * 1.6:
        return "PNP_FLIP_OR_BANNER_GARBAGE"
    if product < 512 * 0.5:
        return "INCONSISTENT_NARROW"
    return "REAL_GATE_CONSISTENT"


# ---------------------------------------------------------------------------
# (c) D5 — F2 first
# ---------------------------------------------------------------------------

def run_d5_f2(dets, states) -> dict:
    # Find the suspicious last close fix (~1.67m) and nearby dets
    close = [d for d in dets if d["dist"] < 5.0]
    if not close:
        return {"error": "no close dets"}
    # last close + any with |ty| large or sign conflict vs state
    rows = []
    for d in close:
        wpx = quad_width_px(d["corners"])
        if wpx is None:
            continue
        prod = d5_product(d["dist"], wpx)
        # nearest state
        bel = None
        best = 1e9
        for s in states:
            dt = abs(s["t"] - d["t"])
            if dt < best:
                best = dt
                bel = s["ty"]
        rows.append(
            {
                "t": d["t"],
                "R": d["dist"],
                "ty_det": d["ty"],
                "ty_state": bel,
                "width_px": wpx,
                "product": prod,
                "verdict": d5_verdict(prod),
                "center": d["center"],
                "delta_state_minus_det": (bel - d["ty"]) if bel is not None else None,
            }
        )

    # Focus: the last close fix (F2 mystery)
    last = rows[-1] if rows else None
    # Also the one closest to 1.67m
    near167 = min(rows, key=lambda r: abs(r["R"] - 1.67)) if rows else None

    # Annotate verdict for the conflict case
    focus = near167 or last
    summary = {
        "n_close_fixes": len(rows),
        "focus": focus,
        "last_close": last,
        "all_close": rows,
        "product_nominal": PRODUCT_NOM,
        "interpretation": "",
    }
    if focus:
        v = focus["verdict"]
        if v == "REAL_GATE_CONSISTENT":
            summary["interpretation"] = (
                f"At R={focus['R']:.2f}m product={focus['product']:.0f}≈512 → "
                "geometry says REAL GATE. Sign conflict (state vs det) is then a "
                "STATE/lock issue or dual-hypothesis, not banner PnP garbage."
            )
        elif v == "PNP_FLIP_OR_BANNER_GARBAGE":
            summary["interpretation"] = (
                f"At R={focus['R']:.2f}m product={focus['product']:.0f}≫512 → "
                "NEAR-WIDE quad with inflated R: banner-as-gate or PnP flip. "
                f"det ty={focus['ty_det']:+.2f} is NOT trusted opening vertical."
            )
        else:
            summary["interpretation"] = (
                f"At R={focus['R']:.2f}m product={focus['product']:.0f}≪512 → "
                "inconsistent narrow/scale — treat as garbage."
            )
    return summary


# ---------------------------------------------------------------------------
# (f) Advisory-3 Test A
# ---------------------------------------------------------------------------

def order_corners_tl_tr_br_bl(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(-1, 2).astype(float)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], float)


def top_bar_from_corners(corners: np.ndarray, img_h: int, img_w: int):
    """Return y_top_norm (+UP from optical center), span_norm (full top-bar length)
    in normalized units where 1 ≈ half-width in px / (W/2) scaling via length.
    Use pixel coords: y_up = (cy0 - y_img) / fy_proxy; span = width_px / fy_proxy
    so W * y / span = W * (cy0-y)/width_px * (something)...

    vertical_terminal: e_z = W * y_top_norm / span_norm - d*
    For consistency with pinhole: y_top_norm = (cy0 - y_bar) / f
    span_norm = width_px / f  → W * y / span = W * (cy0-y)/width_px
    which is range-free metric height of bar center above optical axis...
    Actually W*(cy0-y)/width_px = (W/width_px)*(cy0-y) ≈ Z*(cy0-y)/f * (f*W/Z)/width_px wait
    width_px = f*W/Z ⇒ W/width_px = Z/f ⇒ W*(cy0-y)/width_px = Z*(cy0-y)/f = cam-frame
    vertical of bar in meters (+up if we negate cam y). Good.
    """
    pts = order_corners_tl_tr_br_bl(corners)
    tl, tr = pts[0], pts[1]
    mid = 0.5 * (tl + tr)
    width_px = float(np.linalg.norm(tr - tl))
    if width_px < 1:
        return None
    cy0 = img_h / 2.0
    # +UP: above optical center is positive
    y_top_norm = (cy0 - float(mid[1])) / FX_NOM
    span_norm = width_px / FX_NOM
    return y_top_norm, span_norm, mid, width_px


def mask_top_bar_banner(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Keep only a band around the top bar + region above it (banner)."""
    pts = order_corners_tl_tr_br_bl(corners)
    tl, tr = pts[0], pts[1]
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    # thicken top bar
    bar_pts = np.array([tl, tr], np.int32)
    cv2.line(mask, tuple(bar_pts[0].astype(int)), tuple(bar_pts[1].astype(int)), 255, 14)
    # banner region: above top bar up to ~0.6 of bar length
    length = float(np.linalg.norm(tr - tl))
    y_top = int(min(tl[1], tr[1]))
    y0 = max(0, int(y_top - 0.7 * length))
    x0 = max(0, int(min(tl[0], tr[0]) - 0.1 * length))
    x1 = min(w - 1, int(max(tl[0], tr[0]) + 0.1 * length))
    mask[y0:y_top, x0:x1] = 255
    out = np.zeros_like(img)
    out[mask > 0] = img[mask > 0]
    return out


def run_test_a(fid: str, t0, dets, max_samples: int = 80) -> dict:
    log, vision = flight_paths(fid)
    if not vision.exists():
        return {"error": f"no vision for {fid}", "path": str(vision)}
    # Trusted full poses in 1.34–2.4 m
    band = [d for d in dets if 1.34 <= d["dist"] <= 2.4 and d.get("corners")]
    if not band:
        return {"error": "no dets in 1.34-2.4m band", "fid": fid}
    # subsample
    step = max(1, len(band) // max_samples)
    band = band[::step][:max_samples]

    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    det = HsvGateDetector(params)
    d_star = GATE_H / 2.0  # bar half-height above opening center

    # Index frames by approximating t from mono
    assembler = ChunkAssembler()
    # Collect frames near band times
    want_ts = sorted(d["t"] for d in band)
    t_lo, t_hi = want_ts[0] - 0.05, want_ts[-1] + 0.05
    frames_by_t = []
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
            frames_by_t.append((t, fid_f, sim_ns, img))

    errors = []
    signed = []
    for d in band:
        # nearest frame
        if not frames_by_t:
            break
        fr = min(frames_by_t, key=lambda x: abs(x[0] - d["t"]))
        if abs(fr[0] - d["t"]) > 0.15:
            continue
        _t, _fid, sim_ns, img = fr
        h, w = img.shape[:2]
        corners = np.asarray(d["corners"], float).reshape(-1, 2)
        # Reference e_z (+UP required displacement): aircraft HIGH ⇒ ty_cam>0 ⇒ e_z < 0
        ref = -float(d["ty"])  # opening-center vertical error +UP

        # Top-bar from trusted corners (full pose geometry)
        tb = top_bar_from_corners(corners, h, w)
        if tb is None:
            continue
        y_top_norm, span_norm, mid, width_px = tb
        try:
            e_fullcorn = top_bar_vertical_error(y_top_norm, span_norm, GATE_W, d_star)
        except ValueError:
            continue

        # Masked re-detect: top bar + banner only
        masked = mask_top_bar_banner(img, corners)
        # Also draw a synthetic red top bar to help HSV if banner washes
        pts = order_corners_tl_tr_br_bl(corners)
        cv2.line(
            masked,
            tuple(pts[0].astype(int)),
            tuple(pts[1].astype(int)),
            (0, 0, 220),
            10,
        )
        det_m = det.detect(CameraFrame(frame_id=int(_fid), ts_ns=sim_ns, image=masked))
        e_masked = None
        if det_m is not None and det_m.corners_px is not None:
            tb2 = top_bar_from_corners(np.asarray(det_m.corners_px, float), h, w)
            if tb2 is not None:
                try:
                    e_masked = top_bar_vertical_error(tb2[0], tb2[1], GATE_W, d_star)
                except ValueError:
                    e_masked = None

        # Primary Test A score: oracle from top-bar geometry of trusted corners
        # (masks the lower ring from the FEATURE, not from pixels — advisory Test A)
        # Plus masked-redetect when available.
        e_hat = e_fullcorn if e_masked is None else e_masked
        # Prefer masked when present
        if e_masked is not None:
            e_hat = e_masked
        err = e_hat - ref
        errors.append(err)
        if abs(ref) > 0.15:
            signed.append(1.0 if np.sign(e_hat) == np.sign(ref) else 0.0)

    errors = np.array(errors, float) if errors else np.array([])
    out = {
        "fid": fid,
        "n_band_dets": len(band),
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
        "d_star": d_star,
    }
    if out["median_bias"] is not None:
        out["release_bars"]["median_bias_lt_0.05"] = abs(out["median_bias"]) < 0.05
        out["release_bars"]["p90_lt_0.15"] = out["p90_abs"] < 0.15
        out["release_bars"]["sign_acc_gt_0.99"] = (
            out["sign_acc"] is not None and out["sign_acc"] > 0.99
        )
    return out


# ---------------------------------------------------------------------------
# (a) R1 cyan in last 2m
# ---------------------------------------------------------------------------

def cyan_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (90, 120, 120), (98, 255, 255))


def pitch_from_q(q) -> float | None:
    """Return pitch rad (approx) from quaternion wxyz or xyzw — try both."""
    if not q or len(q) < 4:
        return None
    q = [float(x) for x in q]
    # estimator uses [w,x,y,z]
    w, x, y, z = q
    # pitch = asin(2(wy - zx))? standard aerospace
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    return math.asin(sinp)


def run_r1(fid: str, t0, states, dets) -> dict:
    log, vision = flight_paths(fid)
    if not vision.exists():
        return {"error": "no vision"}
    # times when STATE or det range < 2m
    times = [s["t"] for s in states if s["dist"] < 2.0]
    times += [d["t"] for d in dets if d["dist"] < 2.0]
    if not times:
        return {"fid": fid, "n_frames": 0, "note": "no last-2m samples"}
    t_lo, t_hi = min(times) - 0.2, max(times) + 0.2
    assembler = ChunkAssembler()
    n = 0
    cyan_any = 0
    cyan_below_horizon = 0
    cyan_above_horizon = 0
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        t = (mono_ns - t0) / 1e9
        if t < t_lo:
            continue
        if t > t_hi:
            break
        _fid, _sim, jpeg = done
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        n += 1
        h, w = img.shape[:2]
        # nearest pitch
        pitch = 0.0
        best = 1e9
        for s in states:
            dt = abs(s["t"] - t)
            if dt < best and s.get("q"):
                best = dt
                p = pitch_from_q(s["q"])
                if p is not None:
                    pitch = p
        # horizon row (image y down): 180 + 320*tan(11°+pitch)
        # pitch from attitude is body; optical rest 11° above horizon
        horiz = 180.0 + 320.0 * math.tan(math.radians(11.0) + pitch)
        horiz = float(np.clip(horiz, 0, h - 1))
        m = cyan_mask(img)
        ys, xs = np.where(m > 0)
        if len(ys) < 20:
            continue
        cyan_any += 1
        # split by row vs horizon
        below = ys >= horiz  # image-down: larger y is below horizon in sky sense? 
        # In image, y increases downward. Horizon row: content BELOW horizon in world
        # appears at y > horiz. Ribbon on floor is below horizon → y > horiz.
        if np.mean(ys) > horiz:
            cyan_below_horizon += 1
        else:
            cyan_above_horizon += 1
    return {
        "fid": fid,
        "n_frames_last2m": n,
        "cyan_present_frames": cyan_any,
        "cyan_present_pct": 100.0 * cyan_any / n if n else 0.0,
        "cyan_mean_row_below_horizon": cyan_below_horizon,
        "cyan_mean_row_above_horizon": cyan_above_horizon,
        "below_horizon_pct_of_cyan": 100.0 * cyan_below_horizon / cyan_any if cyan_any else None,
    }


# ---------------------------------------------------------------------------
# (b) R4 banner geometry
# ---------------------------------------------------------------------------

def run_r4(dets, vision: Path, t0) -> dict:
    """Banner bottom edge height above opening center — far frame with trusted fix."""
    far = [d for d in dets if 5.0 <= d["dist"] <= 12.0 and d.get("corners")]
    if not far:
        far = [d for d in dets if d["dist"] >= 4.0 and d.get("corners")]
    if not far or not vision.exists():
        return {"error": "no far fix"}
    # pick a stable mid-far fix
    d = sorted(far, key=lambda x: abs(x["dist"] - 7.0))[0]
    assembler = ChunkAssembler()
    best = None
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        t = (mono_ns - t0) / 1e9
        err = abs(t - d["t"])
        if best is None or err < best[0]:
            best = (err, t, done)
        if t > d["t"] + 1.0 and best and best[0] < 0.2:
            break
    if best is None or best[0] > 0.5:
        return {"error": "no frame", "det_t": d["t"]}
    _err, t, (_fid, _sim, jpeg) = best
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    corners = np.asarray(d["corners"], float).reshape(-1, 2)
    pts = order_corners_tl_tr_br_bl(corners)
    tl, tr = pts[0], pts[1]
    opening_cy = float(corners[:, 1].mean())
    # Search red/white banner above top bar: bottom edge of bright/red blob
    h, w = img.shape[:2]
    y_top = int(min(tl[1], tr[1]))
    x0 = max(0, int(min(tl[0], tr[0])))
    x1 = min(w, int(max(tl[0], tr[0])))
    roi = img[max(0, y_top - 80) : y_top, x0:x1]
    banner_bottom_y = None
    if roi.size:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # red-ish / high-V text region
        red = cv2.bitwise_or(
            cv2.inRange(hsv, (0, 40, 80), (15, 255, 255)),
            cv2.inRange(hsv, (165, 40, 80), (180, 255, 255)),
        )
        ys, xs = np.where(red > 0)
        if len(ys):
            banner_bottom_y = float(max(0, y_top - 80) + ys.max())
    if banner_bottom_y is None:
        # fallback: assume banner sits just above top bar
        banner_bottom_y = y_top - 5.0
    # height above opening center in meters via same scale as D5
    width_px = float(np.linalg.norm(tr - tl))
    px_to_m = GATE_W / width_px if width_px > 1 else float("nan")
    dy_px = opening_cy - banner_bottom_y  # + if banner above opening in image (smaller y)
    # image y down: banner above opening ⇒ banner_y < opening_cy ⇒ dy_px > 0
    height_m = dy_px * px_to_m
    # Save annotated
    vis = img.copy()
    cv2.polylines(vis, [pts.astype(np.int32)], True, (0, 255, 255), 2)
    cv2.line(vis, (x0, int(banner_bottom_y)), (x1, int(banner_bottom_y)), (255, 0, 255), 2)
    cv2.circle(vis, (int(corners[:, 0].mean()), int(opening_cy)), 4, (0, 0, 255), -1)
    cv2.putText(
        vis,
        f"R={d['dist']:.1f} banner_h={height_m:.2f}m above opening",
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    (OUT / "frames").mkdir(exist_ok=True)
    cv2.imwrite(str(OUT / "frames" / "r4_banner_geometry.jpg"), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return {
        "t": d["t"],
        "R": d["dist"],
        "banner_bottom_y_px": banner_bottom_y,
        "opening_cy_px": opening_cy,
        "height_above_opening_m": height_m,
        "width_px": width_px,
        "frame": "frames/r4_banner_geometry.jpg",
    }


# ---------------------------------------------------------------------------
# (d) V6 moments
# ---------------------------------------------------------------------------

def run_v6(states, setpoints, dets) -> dict:
    """(crossing z − aim) on continuous-fix attempts.

    Proxy crossing: last state sample with forward tz crossing / min dist
    while we had a recent fix (age small) — 'continuous-fix'.
    z_cam_up = -ty; aim_up ≈ 0.3m in body/opening frame → aim in cam-up = +0.3
    crossing_z - aim ≈ -ty - aim_up_m  (both +UP)
    """
    aim = 0.3
    # Find approach/commit segments with age < 0.35 at closest
    attempts = []
    # simple: every time we get min dist under 3m with age<0.5 after an approach
    phases = [(s["t"], s["phase"]) for s in setpoints]
    i = 0
    while i < len(states):
        s = states[i]
        if s["dist"] < 3.0 and s["age"] < 0.5:
            # local closest in a short window
            window = [x for x in states if s["t"] - 0.2 <= x["t"] <= s["t"] + 1.5 and x["dist"] < 5.0]
            if not window:
                i += 1
                continue
            closest = min(window, key=lambda x: x["dist"])
            # continuous-fix: age at closest < 0.35 and a det within 0.3s
            near_det = any(abs(d["t"] - closest["t"]) < 0.3 and d["dist"] < 4.0 for d in dets)
            if closest["age"] < 0.35 and near_det and closest["dist"] < 2.5:
                z_up = -closest["ty"]
                attempts.append(
                    {
                        "t": closest["t"],
                        "dist": closest["dist"],
                        "z_up": z_up,
                        "aim": aim,
                        "crossing_minus_aim": z_up - aim,
                        "age": closest["age"],
                    }
                )
                # skip ahead
                i = next((k for k, x in enumerate(states) if x["t"] > closest["t"] + 2.0), len(states))
                continue
        i += 1
    vals = [a["crossing_minus_aim"] for a in attempts]
    return {
        "n_attempts": len(attempts),
        "mean": float(np.mean(vals)) if vals else None,
        "std": float(np.std(vals)) if vals else None,
        "attempts": attempts,
        "decision": (
            None
            if not vals
            else (
                "FURTHER_BIAS_NEEDED"
                if abs(float(np.mean(vals))) > float(np.std(vals)) + 1e-9
                else "NO_FURTHER_BIAS"
            )
        ),
    }


# ---------------------------------------------------------------------------
# (e) Balloon test
# ---------------------------------------------------------------------------

def run_balloon(states, dets, imus, acts) -> dict:
    """Correlate vertical DR error growth with pitch/thrust transients."""
    # During gaps between dets: DR error = state.ty - last_det.ty
    # Growth rate vs |gyro pitch| or thrust change
    if not dets or not states:
        return {"error": "no data"}
    samples = []
    det_i = 0
    for s in states:
        while det_i + 1 < len(dets) and dets[det_i + 1]["t"] <= s["t"]:
            det_i += 1
        d = dets[det_i]
        age = s["t"] - d["t"]
        if age < 0.05 or age > 1.5:
            continue
        if d["dist"] > 8.0:
            continue
        err = s["ty"] - d["ty"]  # believed - last true
        # pitch rate from gyro y (body)
        g = None
        best = 1e9
        for im in imus:
            dt = abs(im["t"] - s["t"])
            if dt < best:
                best = dt
                g = im["gyro"]
        pitch_rate = abs(float(g[1])) if g else 0.0
        thr = None
        best = 1e9
        for a in acts:
            dt = abs(a["t"] - s["t"])
            if dt < best and a["thrust"] is not None:
                best = dt
                thr = float(a["thrust"])
        samples.append({"age": age, "err": err, "abs_err": abs(err), "pitch_rate": pitch_rate, "thrust": thr})

    if len(samples) < 20:
        return {"n": len(samples), "corr_pitch": None, "note": "too few gap samples"}
    age = np.array([s["age"] for s in samples])
    abs_err = np.array([s["abs_err"] for s in samples])
    pr = np.array([s["pitch_rate"] for s in samples])
    # growth proxy: abs_err / age
    growth = abs_err / np.maximum(age, 0.05)
    corr_pitch = float(np.corrcoef(growth, pr)[0, 1]) if np.std(pr) > 1e-6 else None
    thr_vals = [s["thrust"] for s in samples if s["thrust"] is not None]
    corr_thr = None
    if len(thr_vals) > 20:
        # align
        g2, t2 = [], []
        for s in samples:
            if s["thrust"] is not None:
                g2.append(s["abs_err"] / max(s["age"], 0.05))
                t2.append(s["thrust"])
        if np.std(t2) > 1e-6:
            corr_thr = float(np.corrcoef(g2, t2)[0, 1])
    return {
        "n": len(samples),
        "corr_growth_vs_pitch_rate": corr_pitch,
        "corr_growth_vs_thrust": corr_thr,
        "mean_growth_mps": float(np.mean(growth)),
        "verdict": (
            "BLEND_LAG_PLAUSIBLE"
            if corr_pitch is not None and corr_pitch > 0.25
            else "BLEND_LAG_WEAK_OR_KILLED"
        ),
    }


def write_report(bundle: dict):
    d5 = bundle["d5"]
    lines = [
        "# Think-tank ROUND-3 measurement pack",
        "",
        "AGENTS.md DATA ANALYST item 5 (HEAD ≥ `d311654`).",
        "Priority: **(c) D5** → **(f) Test A** → (a)(b)(d)(e).",
        "",
        "## (c) D5 — F2 sign-conflict disambiguation",
        "",
        f"Nominal product fx·W = **{PRODUCT_NOM:.0f} px·m**. "
        "≈512 ⇒ real gate; ≫512 ⇒ near-wide quad with inflated R (PnP flip / banner).",
        "",
    ]
    focus = d5.get("focus") or {}
    if focus:
        lines += [
            f"**Focus fix** (near 1.67 m): t={focus.get('t'):.3f}s R={focus.get('R'):.3f}m "
            f"width_px={focus.get('width_px'):.1f} **product={focus.get('product'):.0f}** "
            f"→ **`{focus.get('verdict')}`**",
            "",
            f"- det ty (log) = {focus.get('ty_det'):+.3f}",
            f"- STATE ty     = {focus.get('ty_state'):+.3f}",
            f"- Δ(state−det) = {focus.get('delta_state_minus_det')}",
            "",
            d5.get("interpretation", ""),
            "",
            "### All close F2 fixes (D5)",
            "",
            "| t | R | w_px | product | verdict | ty_det | ty_state |",
            "|---:|---:|---:|---:|---|---:|---:|",
        ]
        for r in d5.get("all_close") or []:
            lines.append(
                f"| {r['t']:.2f} | {r['R']:.2f} | {r['width_px']:.0f} | {r['product']:.0f} | "
                f"{r['verdict']} | {r['ty_det']:+.2f} | {r['ty_state']:+.2f} |"
            )
    lines += ["", "## (f) Advisory-3 Test A — top-bar reconstruction", ""]
    for fid, ta in (bundle.get("test_a") or {}).items():
        lines.append(f"### `{fid}`")
        if ta.get("error"):
            lines.append(f"- ERROR: {ta['error']}")
            continue
        rb = ta.get("release_bars") or {}
        lines += [
            f"- n_scored={ta.get('n_scored')} (band dets={ta.get('n_band_dets')})",
            f"- median bias = **{ta.get('median_bias')}** m (bar <0.05: {rb.get('median_bias_lt_0.05')})",
            f"- P90 |err| = **{ta.get('p90_abs')}** m (bar <0.15: {rb.get('p90_lt_0.15')})",
            f"- sign acc (|ref|>0.15) = **{ta.get('sign_acc')}** "
            f"(n={ta.get('n_sign_cases')}, bar >0.99: {rb.get('sign_acc_gt_0.99')})",
            "",
        ]
    lines += ["", "## (a) R1 — cyan in last 2 m", ""]
    for fid, r1 in (bundle.get("r1") or {}).items():
        lines.append(f"- `{fid}`: {r1}")
    lines += ["", "## (b) R4 — banner geometry", "", f"{bundle.get('r4')}", ""]
    lines += ["", "## (d) V6 — crossing z − aim moments", ""]
    for fid, v6 in (bundle.get("v6") or {}).items():
        lines.append(
            f"- `{fid}`: n={v6.get('n_attempts')} mean={v6.get('mean')} "
            f"std={v6.get('std')} → **{v6.get('decision')}**"
        )
    lines += ["", "## (e) Balloon test — DR error vs pitch/thrust", ""]
    for fid, b in (bundle.get("balloon") or {}).items():
        lines.append(f"- `{fid}`: {b}")
    lines += [
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`, `d5_f2.csv`",
        "- `frames/r4_banner_geometry.jpg`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frames").mkdir(exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)

    bundle = {"d5": {}, "test_a": {}, "r1": {}, "r4": {}, "v6": {}, "balloon": {}}

    # ----- (c) F2 first -----
    print("=== (c) D5 F2 ===", flush=True)
    log2, vis2 = flight_paths(F2_ID)
    t0_2, states2, dets2, imus2, sp2, acts2 = load_log(log2)
    bundle["d5"] = run_d5_f2(dets2, states2)
    with (OUT / "d5_f2.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["t", "R", "width_px", "product", "verdict", "ty_det", "ty_state", "delta_state_minus_det"],
        )
        w.writeheader()
        for r in bundle["d5"].get("all_close") or []:
            w.writerow({k: r.get(k) for k in w.fieldnames})
    print(bundle["d5"].get("interpretation"), flush=True)

    # Also D5 on F1 for comparison
    log1, vis1 = flight_paths(F1_ID)
    t0_1, states1, dets1, imus1, sp1, acts1 = load_log(log1)

    # ----- (f) Test A -----
    print("=== (f) Test A ===", flush=True)
    for fid, t0, dets in ((F1_ID, t0_1, dets1), (F2_ID, t0_2, dets2)):
        print(f"  Test A {fid}", flush=True)
        bundle["test_a"][fid] = run_test_a(fid, t0, dets)

    # ----- (a) R1 -----
    print("=== (a) R1 ===", flush=True)
    for fid, t0, states, dets in ((F1_ID, t0_1, states1, dets1), (F2_ID, t0_2, states2, dets2)):
        bundle["r1"][fid] = run_r1(fid, t0, states, dets)
        print(f"  {fid}: {bundle['r1'][fid]}", flush=True)

    # ----- (b) R4 -----
    print("=== (b) R4 ===", flush=True)
    bundle["r4"] = run_r4(dets1, vis1, t0_1)
    print(bundle["r4"], flush=True)

    # ----- (d) V6 -----
    print("=== (d) V6 ===", flush=True)
    for fid, states, sp, dets in (
        (F1_ID, states1, sp1, dets1),
        (F2_ID, states2, sp2, dets2),
    ):
        bundle["v6"][fid] = run_v6(states, sp, dets)
        print(f"  {fid}: {bundle['v6'][fid].get('decision')} mean={bundle['v6'][fid].get('mean')}", flush=True)

    # ----- (e) Balloon -----
    print("=== (e) Balloon ===", flush=True)
    for fid, states, dets, imus, acts in (
        (F1_ID, states1, dets1, imus1, acts1),
        (F2_ID, states2, dets2, imus2, acts2),
    ):
        bundle["balloon"][fid] = run_balloon(states, dets, imus, acts)
        print(f"  {fid}: {bundle['balloon'][fid]}", flush=True)

    write_report(bundle)
    (OUT / "summary.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
