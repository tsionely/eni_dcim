"""Extended reflight for Phase 5 close-range perception study.

Corrects scripts/reflight.py's read_recording unpack bug and adds:
  - per-frame range binning from nearest preceding PnP fix
  - failure-mode classification on miss frames
  - annotated frame export
  - gate-size / scoring-volume reconciliation

Usage:
  python analysis/2026-07-16-phase5-closerange/run_phase5_study.py
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.core.messages import CameraFrame, ImuSample  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.state_estimator import StateEstimator  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402

BINS = [
    ("5-8m", 5.0, 8.0),
    ("3-5m", 3.0, 5.0),
    ("2-3m", 2.0, 3.0),
    ("<2m", 0.0, 2.0),
]
EDGE_PX = 8
BLUR_VAR_THRESH = 60.0
DARK_V = 40.0
BRIGHT_V = 220.0


@dataclass
class FrameRow:
    source: str
    t_s: float
    frame_id: int
    preceding_range_m: float | None
    bin_name: str | None
    detected: bool
    det_range_m: float | None
    reason: str  # ok | edge_clip | motion_blur | exposure_dark | exposure_bright |
    # partial_ring | too_large | no_red | area_reject | other_miss | no_preceding
    red_frac: float
    lap_var: float
    mean_v: float
    touches_edge: bool
    n_quads: int
    n_red_contours: int


@dataclass
class SourceSummary:
    source: str
    n_frames: int = 0
    n_fixes: int = 0
    min_fix_range: float | None = None
    by_bin: dict = field(default_factory=dict)


def load_imu(log_path: Path):
    imu = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["topic"] != "imu":
                continue
            m = d["data"]
            imu.append(
                (int(d["mono_ns"]), int(m["ts_ns"]), np.array(m["accel"], float), np.array(m["gyro"], float))
            )
    return imu


def load_frames(slice_path: Path, max_frames: int | None = None):
    """Correct unpack: read_recording yields (mono_ns, stream_id, data)."""
    frames = []
    asm = ChunkAssembler()
    for mono_ns, stream_id, payload in read_recording(str(slice_path)):
        if stream_id != STREAM_VISION:
            continue
        done = asm.feed(payload)
        if not done:
            continue
        frame_id, sim_ns, jpeg = done
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        frames.append((mono_ns, frame_id, sim_ns, img))
        if max_frames is not None and len(frames) >= max_frames:
            break
    return frames


def red_mask(img: np.ndarray, sat=60, val=50) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo = cv2.inRange(hsv, (0, sat, val), (12, 255, 255))
    hi = cv2.inRange(hsv, (168, sat, val), (180, 255, 255))
    return cv2.bitwise_or(lo, hi)


def classify_miss(img: np.ndarray, detector: HsvGateDetector) -> dict:
    """Why did the detector return None on this frame?"""
    h, w = img.shape[:2]
    area_img = float(h * w)
    mask = cv2.morphologyEx(red_mask(img), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    red_frac = float(cv2.countNonZero(mask)) / area_img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mean_v = float(hsv[:, :, 2].mean())

    # Edge touch: red pixels in border strip
    border = np.zeros_like(mask)
    border[:EDGE_PX, :] = 1
    border[-EDGE_PX:, :] = 1
    border[:, :EDGE_PX] = 1
    border[:, -EDGE_PX:] = 1
    touches_edge = int(cv2.countNonZero(cv2.bitwise_and(mask, border * 255))) > 30

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    n_red = 0
    n_quads = 0
    max_frac = 0.0
    has_nonquad_large = False
    for c in contours:
        a = cv2.contourArea(c)
        frac = a / area_img
        if frac < 0.001:
            continue
        n_red += 1
        max_frac = max(max_frac, frac)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            n_quads += 1
        elif frac > 0.01:
            has_nonquad_large = True

    reason = "other_miss"
    if red_frac < 0.0015:
        reason = "no_red"
    elif mean_v < DARK_V:
        reason = "exposure_dark"
    elif mean_v > BRIGHT_V:
        reason = "exposure_bright"
    elif lap_var < BLUR_VAR_THRESH and red_frac > 0.005:
        reason = "motion_blur"
    elif max_frac > float(detector.max_area_frac):
        reason = "too_large"
    elif touches_edge and (n_quads == 0 or max_frac > 0.05):
        reason = "edge_clip"
    elif has_nonquad_large or (n_red > 0 and n_quads == 0):
        reason = "partial_ring"
    elif n_quads > 0:
        reason = "area_reject"  # quads found but failed rectangularity/confidence/area

    return {
        "reason": reason,
        "red_frac": red_frac,
        "lap_var": lap_var,
        "mean_v": mean_v,
        "touches_edge": touches_edge,
        "n_quads": n_quads,
        "n_red_contours": n_red,
        "max_red_frac": max_frac,
    }


def bin_name_for_range(r: float | None) -> str | None:
    if r is None or not math.isfinite(r):
        return None
    for name, lo, hi in BINS:
        if lo <= r < hi:
            return name
    if r >= 8.0:
        return ">=8m"
    return None


def replay_source_v2(
    slice_path: Path,
    log_path: Path | None,
    params: ParamSet,
    source_id: str,
    max_frames: int | None = None,
) -> tuple[list[FrameRow], SourceSummary]:
    """Replay with correct preceding-range bookkeeping."""
    detector = HsvGateDetector(params)
    est = StateEstimator(params) if log_path is not None else None
    imu = load_imu(log_path) if log_path is not None else []
    frames = load_frames(slice_path, max_frames=max_frames)
    summary = SourceSummary(source=source_id, n_frames=len(frames))
    for name, _, _ in BINS:
        summary.by_bin[name] = {"frames": 0, "fixes": 0, "misses": 0, "reasons": {}}
    summary.by_bin[">=8m"] = {"frames": 0, "fixes": 0, "misses": 0, "reasons": {}}
    summary.by_bin["no_preceding"] = {"frames": 0, "fixes": 0, "misses": 0, "reasons": {}}

    if not frames:
        return [], summary

    events = [("imu", t, (ts, a, g)) for t, ts, a, g in imu] + [
        ("frame", t, (fid, sim_ns, img)) for t, fid, sim_ns, img in frames
    ]
    events.sort(key=lambda e: e[1])
    t0 = events[0][1]
    preceding_range: float | None = None
    rows: list[FrameRow] = []
    fix_ranges: list[float] = []

    for kind, mono, payload in events:
        if kind == "imu":
            if est is None:
                continue
            ts, a, g = payload
            est.predict(ImuSample(ts_ns=ts, accel=a, gyro=g))
            continue

        fid, sim_ns, img = payload
        t_s = (mono - t0) / 1e9
        prev_r = preceding_range
        bname = bin_name_for_range(prev_r) if prev_r is not None else "no_preceding"
        if bname is None:
            bname = ">=8m" if (prev_r is not None and prev_r >= 8.0) else "no_preceding"

        det = detector.detect(CameraFrame(frame_id=fid, ts_ns=sim_ns, image=img))
        detected = det is not None and det.rel_pose is not None
        det_range = float(np.linalg.norm(det.rel_pose.t)) if detected else None

        if detected:
            fix_ranges.append(det_range)  # type: ignore[arg-type]
            if est is not None:
                est.update_vision(det)
            mask = red_mask(img)
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cls = {
                "reason": "ok",
                "red_frac": float(cv2.countNonZero(mask)) / float(h * w),
                "lap_var": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                "mean_v": float(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2].mean()),
                "touches_edge": False,
                "n_quads": 1,
                "n_red_contours": 1,
            }
            border = np.zeros_like(mask)
            border[:EDGE_PX, :] = border[-EDGE_PX:, :] = 1
            border[:, :EDGE_PX] = border[:, -EDGE_PX:] = 1
            cls["touches_edge"] = int(cv2.countNonZero(cv2.bitwise_and(mask, border * 255))) > 30
            preceding_range = det_range
        else:
            cls = classify_miss(img, detector)

        bucket = summary.by_bin[bname]
        bucket["frames"] += 1
        if detected:
            bucket["fixes"] += 1
        else:
            bucket["misses"] += 1
            rsn = cls["reason"]
            bucket["reasons"][rsn] = bucket["reasons"].get(rsn, 0) + 1

        rows.append(
            FrameRow(
                source=source_id,
                t_s=t_s,
                frame_id=int(fid),
                preceding_range_m=prev_r,
                bin_name=bname,
                detected=detected,
                det_range_m=det_range,
                reason=cls["reason"],
                red_frac=float(cls["red_frac"]),
                lap_var=float(cls["lap_var"]),
                mean_v=float(cls["mean_v"]),
                touches_edge=bool(cls["touches_edge"]),
                n_quads=int(cls["n_quads"]),
                n_red_contours=int(cls["n_red_contours"]),
            )
        )

    summary.n_fixes = len(fix_ranges)
    summary.min_fix_range = float(min(fix_ranges)) if fix_ranges else None
    return rows, summary


def annotate_frame(img: np.ndarray, row: FrameRow, det_corners=None) -> np.ndarray:
    vis = img.copy()
    mask = red_mask(img)
    overlay = vis.copy()
    overlay[mask > 0] = (0, 0, 255)
    vis = cv2.addWeighted(overlay, 0.25, vis, 0.75, 0)
    if det_corners is not None:
        pts = np.asarray(det_corners, dtype=np.int32).reshape(-1, 2)
        cv2.polylines(vis, [pts], True, (0, 255, 255), 2)
    # edge guides
    h, w = vis.shape[:2]
    cv2.rectangle(vis, (EDGE_PX, EDGE_PX), (w - EDGE_PX, h - EDGE_PX), (255, 255, 0), 1)
    title = (
        f"{row.bin_name} prev={row.preceding_range_m} det={row.detected} "
        f"r={row.det_range_m} why={row.reason}"
    )
    cv2.putText(vis, title[:90], (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(
        vis,
        f"red={row.red_frac:.3f} lap={row.lap_var:.0f} V={row.mean_v:.0f} edge={row.touches_edge}",
        (6, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (200, 200, 200),
        1,
        cv2.LINE_AA,
    )
    if w > 900:
        vis = cv2.resize(vis, (900, int(h * 900 / w)))
    return vis


def discover_pairs() -> list[tuple[str, Path, Path | None]]:
    """(source_id, slice, log|None)"""
    pairs = []
    for fix in sorted((ROOT / "fixtures").glob("*phase3*")):
        for sl in sorted(fix.glob("*.aigprec")):
            # flight id: timestamp-hash before _r2
            stem = sl.stem
            fid = stem.split("_r2")[0].split("_slice")[0]
            log = fix / f"{fid}-flight.jsonl"
            if not log.exists():
                # search other fixtures
                cands = list((ROOT / "fixtures").glob(f"**/{fid}-flight.jsonl"))
                log = cands[0] if cands else None
            sid = f"{fix.name}/{sl.name}"
            pairs.append((sid, sl, log))
    # Local full vision for milestone pass (close-range gold)
    local = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260716T131137-2ca531c3\vision.aigprec")
    log = ROOT / "fixtures" / "20260716T132549-phase3j-r2training-rerun" / "20260716T131137-2ca531c3-flight.jsonl"
    if local.exists() and log.exists():
        pairs.append(("local_pass_vision/20260716T131137", local, log))
    return pairs
