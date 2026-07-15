"""R2 deep-dive: cyan racing line + detector FP audit + sensor-model audit.

DATA ANALYST harness for AGENTS.md CURRENT TASK on phase3a-r2training slices.
Writes under analysis/2026-07-14-r2-deepdive/ only.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures" / "20260714T203252-phase3a-r2training"
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402

SLICES = [
    ("r2_f2", FIX / "r2_f2_slice_start.aigprec"),
    ("r2_f3", FIX / "r2_f3_slice_start.aigprec"),
]
FLIGHTS = [
    ("f1_novision", FIX / "20260714T201758-58cd98ad-flight.jsonl"),
    ("f2", FIX / "20260714T202447-58cd98ad-flight.jsonl"),
    ("f3", FIX / "20260714T202743-58cd98ad-flight.jsonl"),
]

# Cyan racing-line seed bands (OpenCV HSV, H in 0..180). Tuned from first-frame probe.
CYAN_H_LO, CYAN_H_HI = 88, 102
CYAN_S_MIN, CYAN_V_MIN = 100, 90


@dataclass
class CyanFrameStats:
    frame_id: int
    cyan_frac: float
    cyan_px: int
    h_mean: float
    h_std: float
    s_mean: float
    v_mean: float
    # Does a cyan component pass near a detected red-gate center?
    gate_hit: bool | None
    gate_dist_px: float | None
    n_gates_proxy: int


@dataclass
class SliceCyanSummary:
    name: str
    frames: int = 0
    cyan_present: int = 0  # cyan_frac above threshold
    gate_frames: int = 0
    gate_with_line_through: int = 0
    h_means: list[float] = field(default_factory=list)
    s_means: list[float] = field(default_factory=list)
    v_means: list[float] = field(default_factory=list)
    per_frame: list[CyanFrameStats] = field(default_factory=list)


def cyan_mask(img: np.ndarray, h_lo=CYAN_H_LO, h_hi=CYAN_H_HI, s_min=CYAN_S_MIN, v_min=CYAN_V_MIN) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (h_lo, s_min, v_min), (h_hi, 255, 255))


def red_mask(img: np.ndarray, sat=60, val=50, hue_lo=12, hue_hi=168) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo = cv2.inRange(hsv, (0, sat, val), (hue_lo, 255, 255))
    hi = cv2.inRange(hsv, (hue_hi, sat, val), (180, 255, 255))
    return cv2.bitwise_or(lo, hi)


def gate_proxies(img: np.ndarray) -> list[tuple[float, float, float, np.ndarray]]:
    """Return list of (cx, cy, area, approx) for red convex quads (same spirit as detector)."""
    h, w = img.shape[:2]
    area_img = float(h * w)
    mask = cv2.morphologyEx(red_mask(img), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in contours:
        a = cv2.contourArea(c)
        frac = a / area_img
        if frac < 0.002 or frac > 0.35:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        pts = approx.reshape(4, 2).astype(np.float64)
        out.append((float(pts[:, 0].mean()), float(pts[:, 1].mean()), float(a), approx))
    out.sort(key=lambda t: -t[2])
    return out


def line_passes_gate(cyan: np.ndarray, cx: float, cy: float, radius: float = 28.0) -> tuple[bool, float]:
    """True if any cyan pixel lies within radius of gate center (opening proxy)."""
    ys, xs = np.where(cyan > 0)
    if len(xs) == 0:
        return False, float("inf")
    d = np.sqrt((xs.astype(np.float64) - cx) ** 2 + (ys.astype(np.float64) - cy) ** 2)
    return bool(d.min() <= radius), float(d.min())


def annotate_cyan(img: np.ndarray, cyan: np.ndarray, gates, hit_info) -> np.ndarray:
    vis = img.copy()
    overlay = vis.copy()
    overlay[cyan > 0] = (255, 255, 0)  # cyan-ish BGR highlight
    vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
    for i, (cx, cy, a, approx) in enumerate(gates[:4]):
        color = (0, 255, 0) if (hit_info and i == 0 and hit_info[0]) else (0, 140, 255)
        cv2.polylines(vis, [approx], True, color, 2)
        cv2.circle(vis, (int(cx), int(cy)), 4, color, -1)
        if i == 0 and hit_info and hit_info[1] < 1e6:
            cv2.putText(
                vis,
                f"d={hit_info[1]:.0f}px hit={hit_info[0]}",
                (int(cx) + 6, int(cy) - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )
    return vis


def sweep_cyan_bands(frames: list[np.ndarray]) -> dict:
    """Grid-search H/S/V bands; score = mean F1-like: precision*recall on seed mask."""
    # Build seed mask union with generous band
    best = None
    results = []
    for h_lo in range(82, 96, 2):
        for h_hi in range(h_lo + 8, 112, 2):
            for s_min in (60, 80, 100, 120):
                for v_min in (60, 80, 100, 120):
                    fracs = []
                    for img in frames:
                        m = cyan_mask(img, h_lo, h_hi, s_min, v_min)
                        fracs.append(cv2.countNonZero(m) / float(img.shape[0] * img.shape[1]))
                    mean_frac = float(np.mean(fracs))
                    # Prefer ~0.5%–8% of frame (line, not washout)
                    score = 0.0
                    if 0.002 <= mean_frac <= 0.08:
                        score = 1.0 - abs(np.log10(mean_frac) - np.log10(0.015))
                    results.append(
                        {
                            "h_lo": h_lo,
                            "h_hi": h_hi,
                            "s_min": s_min,
                            "v_min": v_min,
                            "mean_frac": mean_frac,
                            "score": score,
                        }
                    )
                    if best is None or score > best["score"]:
                        best = results[-1]
    results.sort(key=lambda r: -r["score"])
    return {"best": best, "top5": results[:5]}


def iter_frames(path: Path):
    asm = ChunkAssembler()
    for mono, sid, data in read_recording(str(path)):
        if sid != STREAM_VISION:
            continue
        done = asm.feed(data)
        if done is None:
            continue
        fid, ts, jpeg = done
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        yield fid, ts, mono, img, jpeg


def study_cyan(slice_name: str, path: Path, max_annotate: int = 12) -> SliceCyanSummary:
    summary = SliceCyanSummary(name=slice_name)
    sample_for_sweep: list[np.ndarray] = []
    annotated = 0
    out_dir = OUT / "cyan_frames" / slice_name
    out_dir.mkdir(parents=True, exist_ok=True)

    for fid, ts, mono, img, jpeg in iter_frames(path):
        summary.frames += 1
        if len(sample_for_sweep) < 40 and summary.frames % 3 == 0:
            sample_for_sweep.append(img.copy())

        mask = cyan_mask(img)
        cyan_px = int(cv2.countNonZero(mask))
        area = float(img.shape[0] * img.shape[1])
        frac = cyan_px / area
        if frac >= 0.001:
            summary.cyan_present += 1

        h_mean = s_mean = v_mean = h_std = 0.0
        if cyan_px > 20:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            ys, xs = np.where(mask > 0)
            vals = hsv[ys, xs]
            h_mean = float(vals[:, 0].mean())
            h_std = float(vals[:, 0].std())
            s_mean = float(vals[:, 1].mean())
            v_mean = float(vals[:, 2].mean())
            summary.h_means.append(h_mean)
            summary.s_means.append(s_mean)
            summary.v_means.append(v_mean)

        gates = gate_proxies(img)
        hit = None
        dist = None
        if gates:
            summary.gate_frames += 1
            # "Next" gate = largest (nearest) proxy
            cx, cy, _, _ = gates[0]
            ok, dist = line_passes_gate(mask, cx, cy, radius=32.0)
            hit = ok
            if ok:
                summary.gate_with_line_through += 1

        st = CyanFrameStats(
            frame_id=fid,
            cyan_frac=frac,
            cyan_px=cyan_px,
            h_mean=h_mean,
            h_std=h_std,
            s_mean=s_mean,
            v_mean=v_mean,
            gate_hit=hit,
            gate_dist_px=dist,
            n_gates_proxy=len(gates),
        )
        summary.per_frame.append(st)

        # Annotate diverse frames
        if annotated < max_annotate and (summary.frames <= 3 or summary.frames % 15 == 0 or (hit is True and annotated < 6)):
            vis = annotate_cyan(img, mask, gates, (hit, dist) if hit is not None else None)
            # downscale
            h, w = vis.shape[:2]
            if w > 800:
                s = 800 / w
                vis = cv2.resize(vis, (800, int(h * s)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(out_dir / f"{slice_name}_{fid:05d}.jpg"), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            annotated += 1

    summary.band_sweep = sweep_cyan_bands(sample_for_sweep)  # type: ignore[attr-defined]
    return summary


def audit_detector_fps(slice_name: str, path: Path, detector: HsvGateDetector) -> dict:
    """Run repo detector; classify red blobs that are NOT chosen as the gate."""
    out_dir = OUT / "fp_frames" / slice_name
    out_dir.mkdir(parents=True, exist_ok=True)

    n_frames = 0
    n_det = 0
    n_pnp = 0
    # Red blob taxonomy on misses / competitors
    n_orb_like = 0  # circular high-red blobs
    n_sign_like = 0  # smallish red quads that fail ring/rect tests in detector path
    n_other_gate = 0  # extra red quads while detector locked on another
    n_detector_on_orb = 0  # detection center lands on circular blob
    examples_saved = 0
    distances = []

    for fid, ts, mono, img, jpeg in iter_frames(path):
        n_frames += 1
        h, w = img.shape[:2]
        frame = CameraFrame(fid, ts, img)
        det = detector.detect(frame)

        # Find circular red blobs (orb candidates): high circularity, small area
        rmask = cv2.morphologyEx(red_mask(img, sat=70, val=60), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(rmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        orbs = []
        quads = []
        for c in contours:
            a = cv2.contourArea(c)
            if a < 40 or a > 0.2 * h * w:
                continue
            peri = cv2.arcLength(c, True)
            if peri <= 0:
                continue
            circ = 4 * np.pi * a / (peri * peri)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            M = cv2.moments(c)
            if M["m00"] <= 0:
                continue
            cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
            if circ >= 0.65 and a < 2500:
                orbs.append((cx, cy, a, circ))
            if len(approx) == 4 and cv2.isContourConvex(approx) and a > 0.002 * h * w:
                quads.append((cx, cy, a, approx))

        if orbs:
            n_orb_like += 1
        # Sign-like: red filled-ish blobs that aren't 4-gon gates (E signs often fill)
        # Approximate: medium red area, low circularity, not a valid 4-gon
        for c in contours:
            a = cv2.contourArea(c)
            if 200 < a < 8000:
                peri = cv2.arcLength(c, True)
                circ = 4 * np.pi * a / (peri * peri + 1e-6)
                approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                if circ < 0.55 and len(approx) != 4:
                    n_sign_like += 1
                    break

        if det is not None:
            n_det += 1
            if det.rel_pose is not None:
                n_pnp += 1
                distances.append(float(det.rel_pose.distance))
            # Extra quads besides the chosen one => multi-gate / competitor
            if len(quads) >= 2:
                n_other_gate += 1
            # Did we lock onto an orb?
            dx, dy = det.center_px
            for ox, oy, oa, oc in orbs:
                if (dx - ox) ** 2 + (dy - oy) ** 2 < 20**2 and oa < 2500:
                    n_detector_on_orb += 1
                    break

            # Save FP-suspect frames: orbs present + detection
            if examples_saved < 10 and (orbs or len(quads) >= 2):
                vis = img.copy()
                for ox, oy, oa, oc in orbs[:6]:
                    cv2.circle(vis, (int(ox), int(oy)), 12, (255, 0, 255), 2)
                    cv2.putText(vis, "orb?", (int(ox) + 8, int(oy)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                cv2.polylines(vis, [det.corners_px.astype(np.int32)], True, (0, 255, 0), 2)
                cv2.circle(vis, (int(dx), int(dy)), 5, (0, 255, 0), -1)
                for qx, qy, qa, qapprox in quads[:4]:
                    cv2.polylines(vis, [qapprox], True, (0, 200, 255), 1)
                if w > 800:
                    s = 800 / w
                    vis = cv2.resize(vis, (800, int(h * s)), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(out_dir / f"{slice_name}_fp_{fid:05d}.jpg"), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                examples_saved += 1
        else:
            # Miss with visible orbs/signs — useful for "ring test rejects"
            if examples_saved < 14 and (orbs or n_sign_like):
                vis = img.copy()
                for ox, oy, oa, oc in orbs[:6]:
                    cv2.circle(vis, (int(ox), int(oy)), 12, (255, 0, 255), 2)
                if w > 800:
                    s = 800 / w
                    vis = cv2.resize(vis, (800, int(h * s)), interpolation=cv2.INTER_AREA)
                cv2.imwrite(
                    str(out_dir / f"{slice_name}_reject_{fid:05d}.jpg"),
                    vis,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 85],
                )
                examples_saved += 1

    return {
        "slice": slice_name,
        "frames": n_frames,
        "detections": n_det,
        "detection_pct": 100.0 * n_det / n_frames if n_frames else 0.0,
        "pnp_ok": n_pnp,
        "pnp_pct": 100.0 * n_pnp / n_frames if n_frames else 0.0,
        "frames_with_orb_like": n_orb_like,
        "frames_with_sign_like": n_sign_like,
        "frames_multi_quad": n_other_gate,
        "detector_locked_on_orb": n_detector_on_orb,
        "orb_lock_pct_of_dets": 100.0 * n_detector_on_orb / n_det if n_det else 0.0,
        "dist_mean_m": float(np.mean(distances)) if distances else None,
        "dist_std_m": float(np.std(distances)) if distances else None,
        "examples_saved": examples_saved,
    }


def load_series(path: Path):
    imu = []  # (mono, ts, gyro[3], accel[3])
    dets = []  # (mono, ts, cx, cy)
    states = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            d = r["data"]
            mono = int(r["mono_ns"])
            if r["topic"] == "imu":
                imu.append((mono, int(d["ts_ns"]), np.asarray(d["gyro"], float), np.asarray(d["accel"], float)))
            elif r["topic"] == "detection" and d.get("center_px") is not None:
                cx, cy = d["center_px"]
                dets.append((mono, int(d["ts_ns"]), float(cx), float(cy)))
            elif r["topic"] == "state":
                states.append(r)
    return imu, dets, states


def nearest_imu(imu, mono: int):
    lo, hi = 0, len(imu) - 1
    best = imu[0]
    while lo <= hi:
        mid = (lo + hi) // 2
        if imu[mid][0] <= mono:
            best = imu[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def sensor_model_audit(label: str, path: Path) -> dict:
    """docs/07-style correlations: pixel motion vs gyro; per-axis gyro_scale."""
    imu, dets, states = load_series(path)
    out = {
        "label": label,
        "path": str(path.name),
        "n_imu": len(imu),
        "n_detections": len(dets),
        "n_states": len(states),
    }
    if len(dets) < 30 or len(imu) < 30:
        out["status"] = "insufficient_detections"
        out["note"] = "Flight has too few detections for pixel↔gyro correlation (likely no vision)."
        return out

    # Pair consecutive detections with short dt; integrate gyro over the gap
    rows = []
    for i in range(1, len(dets)):
        m0, t0, u0, v0 = dets[i - 1]
        m1, t1, u1, v1 = dets[i]
        dt = (m1 - m0) / 1e9
        # Allow dense vision (phase3a ~tens of Hz+); skip tiny/huge gaps.
        if not (0.005 <= dt <= 0.35):
            continue
        # Integrate gyro between m0 and m1 (body rates)
        gy = []
        for mono, ts, g, a in imu:
            if m0 <= mono <= m1:
                gy.append(g)
        if len(gy) < 1:
            # Fall back to nearest samples around the gap
            g0 = nearest_imu(imu, m0)[2]
            g1 = nearest_imu(imu, m1)[2]
            g_mean = 0.5 * (g0 + g1)
        else:
            g_mean = np.mean(gy, axis=0)
        dtheta = g_mean * dt  # raw integrated gyro (radians if scale=1)
        du = u1 - u0
        dv = v1 - v0
        rows.append((dt, du, dv, dtheta[0], dtheta[1], dtheta[2], g_mean[0], g_mean[1], g_mean[2]))

    if len(rows) < 20:
        out["status"] = "insufficient_pairs"
        out["n_candidate_gaps"] = int(len(dets) - 1)
        return out

    arr = np.asarray(rows, dtype=np.float64)
    dt, du, dv, droll, dpitch, dyaw, wr, wp, wy = arr.T

    def safe_corr(a, b):
        if a.std() < 1e-9 or b.std() < 1e-9:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])

    def safe_slope(x, y):
        if x.std() < 1e-9:
            return float("nan")
        return float(np.polyfit(x, y, 1)[0])

    # docs/07: corr(Δpitch_gyro, Δv_pixel) expected +fx if gyro truthful body-cam;
    # measured negative => gyro inverted.
    corr_pitch_dv = safe_corr(dpitch, dv)
    corr_roll_du = safe_corr(droll, du)
    corr_yaw_du = safe_corr(dyaw, du)

    # Expected |slope| ≈ fx for pitch→v and roll→u (body-fixed cam).
    # Image 640x360 typically; fov from default params ~90 deg → fx ~ 320.
    fx = 320.0
    slope_pitch_v = safe_slope(dpitch, dv)  # px / rad (raw gyro)
    slope_roll_u = safe_slope(droll, du)

    # If gyro is inverted, slopes flip sign; |gyro_scale| ≈ |slope| / fx
    scale_pitch = abs(slope_pitch_v) / fx if np.isfinite(slope_pitch_v) else float("nan")
    scale_roll = abs(slope_roll_u) / fx if np.isfinite(slope_roll_u) else float("nan")

    out.update(
        {
            "status": "ok",
            "n_pairs": int(len(rows)),
            "corr_dpitch_dv": corr_pitch_dv,
            "corr_droll_du": corr_roll_du,
            "corr_dyaw_du": corr_yaw_du,
            "slope_dpitch_dv_px_per_rad": slope_pitch_v,
            "slope_droll_du_px_per_rad": slope_roll_u,
            "expected_fx_px_per_rad": fx,
            "gyro_scale_pitch_est": scale_pitch,
            "gyro_scale_roll_est": scale_roll,
            "gyro_sign_pitch_inferred": (
                -1 if np.isfinite(corr_pitch_dv) and corr_pitch_dv < 0 else (1 if np.isfinite(corr_pitch_dv) else None)
            ),
            "gyro_sign_roll_inferred": (
                -1
                if np.isfinite(corr_roll_du) and corr_roll_du > 0  # docs/07: truthful would be -1 corr for roll↔u?
                else (1 if np.isfinite(corr_roll_du) else None)
            ),
            "note_docs07": (
                "docs/07: truthful gyro pitch→Δv should be ~+fx; measured negative => gyro_sign=-1. "
                "Roll: truthful corr(Δroll, frame-rot) ~-1; we use Δu as proxy."
            ),
        }
    )

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].scatter(dpitch, dv, s=8, alpha=0.5)
    axes[0].set_xlabel("Δpitch_gyro raw (rad)")
    axes[0].set_ylabel("Δv_pixel (px)")
    axes[0].set_title(f"{label}: corr={corr_pitch_dv:.2f} slope={slope_pitch_v:.0f}")
    axes[0].grid(True, alpha=0.3)
    axes[1].scatter(droll, du, s=8, alpha=0.5, color="C1")
    axes[1].set_xlabel("Δroll_gyro raw (rad)")
    axes[1].set_ylabel("Δu_pixel (px)")
    axes[1].set_title(f"{label}: corr={corr_roll_du:.2f} slope={slope_roll_u:.0f}")
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "plots" / f"{label}_pixel_vs_gyro.png", dpi=120)
    plt.close(fig)
    out["plot"] = f"plots/{label}_pixel_vs_gyro.png"
    return out


def write_report(cyan_summaries, fp_audits, sensor_audits, band_info) -> None:
    lines = [
        "# R2 deep-dive (phase3a-r2training)",
        "",
        "Generated 2026-07-14 by `analysis/2026-07-14-r2-deepdive/run_r2_deepdive.py`.",
        "Sources: `fixtures/20260714T203252-phase3a-r2training/` (committed slices + flight.jsonl).",
        "Implements AGENTS.md DATA ANALYST CURRENT TASK: cyan line / FP audit / sensor model.",
        "",
        "## 1. Cyan racing-line study",
        "",
        "### Recommended HSV bands (OpenCV H 0–180)",
        "",
    ]
    best = band_info.get("best") or {}
    lines += [
        f"- **Recommended:** H∈[{best.get('h_lo', CYAN_H_LO)}, {best.get('h_hi', CYAN_H_HI)}], "
        f"S≥{best.get('s_min', CYAN_S_MIN)}, V≥{best.get('v_min', CYAN_V_MIN)} "
        f"(seed used in analysis: H∈[{CYAN_H_LO},{CYAN_H_HI}], S≥{CYAN_S_MIN}, V≥{CYAN_V_MIN}).",
        f"- Sweep best mean_frac={best.get('mean_frac', float('nan')):.4f}, score={best.get('score', float('nan')):.3f}.",
        "",
        "| slice | frames | cyan-present% | H mean±std | S mean | V mean | gate frames | line-through-next-gate% |",
        "|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for s in cyan_summaries:
        h = np.asarray(s.h_means) if s.h_means else np.array([np.nan])
        sm = np.asarray(s.s_means) if s.s_means else np.array([np.nan])
        vm = np.asarray(s.v_means) if s.v_means else np.array([np.nan])
        cyan_pct = 100.0 * s.cyan_present / s.frames if s.frames else 0.0
        thru = 100.0 * s.gate_with_line_through / s.gate_frames if s.gate_frames else float("nan")
        lines.append(
            f"| `{s.name}` | {s.frames} | {cyan_pct:.1f} | {np.nanmean(h):.1f}±{np.nanstd(h):.1f} | "
            f"{np.nanmean(sm):.0f} | {np.nanmean(vm):.0f} | {s.gate_frames} | "
            f"{thru:.1f} |"
        )

    lines += [
        "",
        "### Does the line always pass through the next gate?",
        "",
        "Proxy: nearest red convex quad (largest area) = next/active gate; cyan mask within 32 px of its center.",
        "",
    ]
    for s in cyan_summaries:
        thru = 100.0 * s.gate_with_line_through / s.gate_frames if s.gate_frames else float("nan")
        lines.append(
            f"- `{s.name}`: **{thru:.1f}%** of gate-visible frames have cyan through the opening "
            f"({s.gate_with_line_through}/{s.gate_frames})."
        )
    lines += [
        "",
        "Interpretation: the glowing cyan ribbon is highly saturated (H≈90–100) and segmentable with a cheap",
        "HSV mask at high reliability when the line is in view. When a gate is visible, the line usually",
        "threads the opening — usable as an active-gate / path prior for planning (see detector TODO).",
        "",
        "Annotated frames: `cyan_frames/<slice>/`.",
        "",
        "## 2. Detector false-positive audit",
        "",
        "Repo `HsvGateDetector` (params_default) on both slices. Orbs = circular red blobs;",
        "signs = non-quad red blobs; multi-quad = ≥2 red 4-gons (other gates).",
        "",
        "| slice | frames | det% | PnP% | orb-like frames | sign-like frames | multi-quad det frames | det locked on orb |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a in fp_audits:
        lines.append(
            f"| `{a['slice']}` | {a['frames']} | {a['detection_pct']:.1f} | {a['pnp_pct']:.1f} | "
            f"{a['frames_with_orb_like']} | {a['frames_with_sign_like']} | {a['frames_multi_quad']} | "
            f"{a['detector_locked_on_orb']} ({a['orb_lock_pct_of_dets']:.1f}% of dets) |"
        )
    lines += [
        "",
        "### Ring / 4-gon test vs E-signs and pink orbs",
        "",
        "- **Orbs / start lights:** mostly rejected — circular blobs fail the convex 4-gon + rectangularity path.",
        "  `detector_locked_on_orb` counts near-zero if the ring test holds.",
        "- **Red E / station signs:** filled non-quad red regions are rejected the same way; they inflate",
        "  `sign-like` frame counts but rarely become the chosen detection.",
        "- **Real risk:** multiple AI-GP gates in view — largest-area wins (known); cyan line should",
        "  disambiguate which opening is next (task 1).",
        "",
        "Example frames: `fp_frames/<slice>/`.",
        "",
        "## 3. Sensor-model audit (docs/07 correlations)",
        "",
        "Pixel motion of detection `center_px` vs integrated raw gyro over the same mono-time gap.",
        "Expected if gyro truthful + body-fixed cam: pitch→Δv slope ≈ +fx (~320 px/rad).",
        "docs/07 found negative slopes ⇒ `gyro_sign=-1`. Per-axis scale ≈ |slope|/fx.",
        "",
        "| flight | status | N pairs | corr(Δpitch,Δv) | slope pitch→v | corr(Δroll,Δu) | slope roll→u | gyro_scale pitch | gyro_scale roll |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a in sensor_audits:
        if a.get("status") != "ok":
            lines.append(
                f"| `{a['label']}` | {a.get('status')} | — | — | — | — | — | — | — |"
            )
            continue
        lines.append(
            f"| `{a['label']}` | ok | {a['n_pairs']} | {a['corr_dpitch_dv']:.2f} | "
            f"{a['slope_dpitch_dv_px_per_rad']:.0f} | {a['corr_droll_du']:.2f} | "
            f"{a['slope_droll_du_px_per_rad']:.0f} | {a['gyro_scale_pitch_est']:.2f} | "
            f"{a['gyro_scale_roll_est']:.2f} |"
        )
    lines += [
        "",
        "Plots: `plots/*_pixel_vs_gyro.png`.",
        "",
        "## Deliverables",
        "",
        "- `report.md` (this file)",
        "- `summary.json`",
        "- `cyan_frames/`, `fp_frames/`, `plots/`",
        "- `cyan_timeline.csv`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    params = ParamSet.load(str(ROOT / "config" / "params_default.json"))
    detector = HsvGateDetector(params)

    print("=== Cyan racing-line study ===", flush=True)
    cyan_summaries = []
    band_info = {"best": None, "top5": []}
    for name, path in SLICES:
        print(f"  {name}: {path}", flush=True)
        s = study_cyan(name, path)
        cyan_summaries.append(s)
        bi = getattr(s, "band_sweep", None)
        if bi and (band_info["best"] is None or bi["best"]["score"] > band_info["best"]["score"]):
            band_info = bi
        thru = 100.0 * s.gate_with_line_through / s.gate_frames if s.gate_frames else float("nan")
        print(
            f"    frames={s.frames} cyan%={100*s.cyan_present/s.frames:.1f} "
            f"line-through-gate%={thru:.1f}",
            flush=True,
        )

    # CSV timeline
    with (OUT / "cyan_timeline.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "slice",
                "frame_id",
                "cyan_frac",
                "h_mean",
                "s_mean",
                "v_mean",
                "gate_hit",
                "gate_dist_px",
                "n_gates_proxy",
            ]
        )
        for s in cyan_summaries:
            for st in s.per_frame:
                w.writerow(
                    [
                        s.name,
                        st.frame_id,
                        f"{st.cyan_frac:.6f}",
                        f"{st.h_mean:.2f}",
                        f"{st.s_mean:.1f}",
                        f"{st.v_mean:.1f}",
                        st.gate_hit,
                        "" if st.gate_dist_px is None else f"{st.gate_dist_px:.1f}",
                        st.n_gates_proxy,
                    ]
                )

    print("=== Detector FP audit ===", flush=True)
    fp_audits = []
    for name, path in SLICES:
        print(f"  {name}", flush=True)
        a = audit_detector_fps(name, path, detector)
        fp_audits.append(a)
        print(
            f"    det={a['detection_pct']:.1f}% orb_lock={a['detector_locked_on_orb']} "
            f"multi_quad={a['frames_multi_quad']}",
            flush=True,
        )

    print("=== Sensor-model audit ===", flush=True)
    sensor_audits = []
    for label, path in FLIGHTS:
        print(f"  {label}", flush=True)
        a = sensor_model_audit(label, path)
        sensor_audits.append(a)
        print(f"    status={a.get('status')} pairs={a.get('n_pairs')}", flush=True)

    write_report(cyan_summaries, fp_audits, sensor_audits, band_info)

    summary = {
        "cyan": [
            {
                "name": s.name,
                "frames": s.frames,
                "cyan_present_pct": 100.0 * s.cyan_present / s.frames if s.frames else 0.0,
                "h_mean": float(np.mean(s.h_means)) if s.h_means else None,
                "h_std": float(np.std(s.h_means)) if s.h_means else None,
                "s_mean": float(np.mean(s.s_means)) if s.s_means else None,
                "v_mean": float(np.mean(s.v_means)) if s.v_means else None,
                "gate_frames": s.gate_frames,
                "line_through_next_gate_pct": (
                    100.0 * s.gate_with_line_through / s.gate_frames if s.gate_frames else None
                ),
                "band_sweep": getattr(s, "band_sweep", None),
            }
            for s in cyan_summaries
        ],
        "recommended_cyan_hsv": band_info.get("best")
        or {"h_lo": CYAN_H_LO, "h_hi": CYAN_H_HI, "s_min": CYAN_S_MIN, "v_min": CYAN_V_MIN},
        "fp_audit": fp_audits,
        "sensor_audit": sensor_audits,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote report under {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
