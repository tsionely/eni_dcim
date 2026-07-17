"""ROUND-4 / advisory-4 pack — AGENTS.md DATA ANALYST item 6.

Priority: (A2/R1) cyan last-2m on all phase5c+5d takeoff→end slices,
then (A1) FA=0 adversarial manifest, (A4) bar width, (A5) min inter-gate spacing.
HEAD >= 0cbb682.
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
FIX = ROOT / "fixtures"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402

FX_NOM = 320.0
GATE_W = 1.6
IMG_H = 360

# Committed takeoff→end slices (phase5c + phase5d)
SLICES = [
    {
        "phase": "phase5c",
        "flight": "F1",
        "fid": "20260717T095722-a560c093",
        "fixture": "20260717T100347-phase5c-ownership",
        "slice": "20260717T095722-a560c093_takeoff_to_end.aigprec",
        "log": "20260717T095722-a560c093-flight.jsonl",
    },
    {
        "phase": "phase5c",
        "flight": "F2",
        "fid": "20260717T095851-a560c093",
        "fixture": "20260717T100347-phase5c-ownership",
        "slice": "20260717T095851-a560c093_takeoff_to_end_full.aigprec",
        "log": "20260717T095851-a560c093-flight.jsonl",
    },
    {
        "phase": "phase5c",
        "flight": "F3",
        "fid": "20260717T100017-a560c093",
        "fixture": "20260717T100347-phase5c-ownership",
        "slice": "20260717T100017-a560c093_takeoff_to_end_full.aigprec",
        "log": "20260717T100017-a560c093-flight.jsonl",
    },
    {
        "phase": "phase5d",
        "flight": "F1",
        "fid": "20260717T101837-7223cc0c",
        "fixture": "20260717T102447-phase5d-vertical",
        "slice": "20260717T101837-7223cc0c_takeoff_to_end.aigprec",
        "log": "20260717T101837-7223cc0c-flight.jsonl",
    },
    {
        "phase": "phase5d",
        "flight": "F2",
        "fid": "20260717T102007-7223cc0c",
        "fixture": "20260717T102447-phase5d-vertical",
        "slice": "20260717T102007-7223cc0c_takeoff_to_end.aigprec",
        "log": "20260717T102007-7223cc0c-flight.jsonl",
    },
    {
        "phase": "phase5d",
        "flight": "F3",
        "fid": "20260717T102132-7223cc0c",
        "fixture": "20260717T102447-phase5d-vertical",
        "slice": "20260717T102132-7223cc0c_takeoff_to_end.aigprec",
        "log": "20260717T102132-7223cc0c-flight.jsonl",
    },
]


def cyan_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (90, 120, 120), (98, 255, 255))


def pitch_from_q(q) -> float | None:
    if not q or len(q) < 4:
        return None
    w, x, y, z = (float(v) for v in q[:4])
    sinp = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    return math.asin(sinp)


def horizon_row(pitch_rad: float, h: int = IMG_H) -> float:
    # AGENTS: 180 + 320·tan(11°+pitch)
    horiz = 180.0 + 320.0 * math.tan(math.radians(11.0) + pitch_rad)
    return float(np.clip(horiz, 0, h - 1))


def load_log(log_path: Path):
    t0 = None
    states, dets, phases = [], [], []
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
                dist = None
                ty = None
                t_vec = None
                if gr and gr.get("t") is not None:
                    t_vec = [float(x) for x in gr["t"]]
                    dist = float(np.linalg.norm(t_vec))
                    ty = t_vec[1]
                states.append({
                    "t": t,
                    "mono_ns": mono,
                    "dist": dist,
                    "ty": ty,
                    "t_vec": t_vec,
                    "age": float(d.get("gate_rel_age_s") or 0.0),
                    "q": d.get("q_att"),
                    "phase": d.get("phase"),
                })
            elif topic == "detection" and d.get("rel_pose"):
                tx, ty, tz = (float(x) for x in d["rel_pose"]["t"])
                dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                dets.append({
                    "t": t,
                    "mono_ns": mono,
                    "dist": dist,
                    "ty": ty,
                    "tz": tz,
                    "corners": d.get("corners_px"),
                    "center": d.get("center_px"),
                    "normal": d.get("rel_pose", {}).get("normal"),
                    "ts_ns": d.get("ts_ns"),
                })
            elif topic == "setpoint":
                phases.append({"t": t, "phase": d.get("phase"), "mono_ns": mono})
            elif topic == "fsm" or (topic == "event" and "phase" in d):
                phases.append({"t": t, "phase": d.get("dst") or d.get("phase"), "mono_ns": mono})
    return t0, states, dets, phases


def decode_frames(vision: Path, dedupe: bool = True):
    """Yield (t_rel_from_first, frame_id, sim_ns, img, mono_ns) unique by frame_id."""
    assembler = ChunkAssembler()
    seen = set()
    t0 = None
    frames = []
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        frame_id, sim_ns, jpeg = done
        if dedupe and frame_id in seen:
            continue
        seen.add(frame_id)
        if t0 is None:
            t0 = mono_ns
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        t = (mono_ns - t0) / 1e9
        frames.append({
            "t_slice": t,
            "frame_id": int(frame_id),
            "sim_ns": int(sim_ns),
            "mono_ns": int(mono_ns),
            "img": img,
        })
    return frames, t0


def align_frame_times_to_log(frames, log_t0: int, slice_mono0: int | None):
    """Map slice frames onto flight-log time using mono_ns."""
    out = []
    for fr in frames:
        t_log = (fr["mono_ns"] - log_t0) / 1e9
        out.append({**fr, "t": t_log})
    return out


def nearest_pitch(states, t: float) -> float:
    pitch = 0.0
    best = 1e9
    for s in states:
        dt = abs(s["t"] - t)
        if dt < best and s.get("q"):
            best = dt
            p = pitch_from_q(s["q"])
            if p is not None:
                pitch = p
    return pitch


def last2m_times(states, dets) -> tuple[float, float] | None:
    times = [s["t"] for s in states if s.get("dist") is not None and s["dist"] < 2.0]
    times += [d["t"] for d in dets if d["dist"] < 2.0]
    # Also include closest approach window if never <2m (some DR stays >2)
    if not times:
        dists = [(s["t"], s["dist"]) for s in states if s.get("dist") is not None]
        if not dists:
            return None
        t_min, d_min = min(dists, key=lambda x: x[1])
        times = [
            s["t"] for s in states
            if s.get("dist") is not None and s["dist"] <= d_min + 2.0
        ]
        if not times:
            times = [t_min]
        return min(times) - 0.05, max(times) + 0.05
    return min(times) - 0.05, max(times) + 0.05


# ---------------------------------------------------------------------------
# (A2/R1)
# ---------------------------------------------------------------------------

def run_a2_r1(meta, t0, states, dets, frames) -> dict:
    window = last2m_times(states, dets)
    if window is None:
        return {
            "fid": meta["fid"],
            "phase": meta["phase"],
            "flight": meta["flight"],
            "n_frames_last2m": 0,
            "note": "no range samples for last-2m window",
        }
    t_lo, t_hi = window
    # Prefer STATE/DET dist<2; else flag fallback
    strict = [s for s in states if s.get("dist") is not None and s["dist"] < 2.0]
    strict += [d for d in dets if d["dist"] < 2.0]
    mode = "dist_lt_2m" if strict else "closest_span_fallback"

    offsets = []  # cyan_mean_row - horizon (negative => above horizon in image-up sense)
    # image y down: cyan ABOVE horizon row ⇒ mean_y < horiz ⇒ offset = mean_y - horiz < 0
    # Advisory predicts ribbon ~30px ABOVE horizon in LOW geometry ⇒ offset ≈ -30
    n = 0
    cyan_n = 0
    above = 0
    below = 0
    rows = []
    for fr in frames:
        t = fr["t"]
        if t < t_lo or t > t_hi:
            continue
        # If strict mode, also require nearby state/det <2m
        if mode == "dist_lt_2m":
            near = any(
                abs(s["t"] - t) < 0.08 and s.get("dist") is not None and s["dist"] < 2.0
                for s in states
            ) or any(abs(d["t"] - t) < 0.08 and d["dist"] < 2.0 for d in dets)
            if not near:
                continue
        n += 1
        img = fr["img"]
        h, w = img.shape[:2]
        pitch = nearest_pitch(states, t)
        horiz = horizon_row(pitch, h)
        m = cyan_mask(img)
        ys, xs = np.where(m > 0)
        if len(ys) < 20:
            rows.append({
                "t": t,
                "frame_id": fr["frame_id"],
                "cyan": False,
                "horizon": horiz,
                "pitch_deg": math.degrees(pitch),
            })
            continue
        cyan_n += 1
        mean_y = float(np.mean(ys))
        off = mean_y - horiz  # <0 ⇒ cyan above horizon row
        offsets.append(off)
        if mean_y < horiz:
            above += 1
        else:
            below += 1
        rows.append({
            "t": t,
            "frame_id": fr["frame_id"],
            "cyan": True,
            "cyan_mean_row": mean_y,
            "horizon": horiz,
            "offset_px": off,
            "pitch_deg": math.degrees(pitch),
        })

    offs = np.asarray(offsets, float) if offsets else np.array([])
    # LOW-geometry signature: ~+30px above horizon ⇒ offset ≈ -30
    low_sig = None
    if len(offs):
        med = float(np.median(offs))
        low_sig = {
            "median_offset_px": med,
            "matches_plus30_above_horizon": -45 <= med <= -15,
            "frac_above_horizon": above / cyan_n if cyan_n else 0.0,
        }

    return {
        "fid": meta["fid"],
        "phase": meta["phase"],
        "flight": meta["flight"],
        "mode": mode,
        "t_window": [t_lo, t_hi],
        "n_frames_last2m": n,
        "cyan_present_frames": cyan_n,
        "cyan_present_pct": 100.0 * cyan_n / n if n else 0.0,
        "cyan_above_horizon": above,
        "cyan_below_horizon": below,
        "above_horizon_pct_of_cyan": 100.0 * above / cyan_n if cyan_n else None,
        "offset_px": {
            "n": int(len(offs)),
            "mean": float(np.mean(offs)) if len(offs) else None,
            "median": float(np.median(offs)) if len(offs) else None,
            "std": float(np.std(offs)) if len(offs) else None,
            "p10": float(np.percentile(offs, 10)) if len(offs) else None,
            "p90": float(np.percentile(offs, 90)) if len(offs) else None,
        },
        "low_geometry_signature": low_sig,
        "v1_gate_bar_ge_60pct": (100.0 * cyan_n / n >= 60.0) if n else False,
        "sample_rows": rows[:: max(1, len(rows) // 40)][:40],
    }


# ---------------------------------------------------------------------------
# (A1) FA=0 adversarial manifest
# ---------------------------------------------------------------------------

def frames_in_log_window(frames, t_lo: float, t_hi: float):
    hit = [fr for fr in frames if t_lo <= fr["t"] <= t_hi]
    if not hit:
        return None
    return {
        "t_lo": t_lo,
        "t_hi": t_hi,
        "n_frames": len(hit),
        "frame_id_first": hit[0]["frame_id"],
        "frame_id_last": hit[-1]["frame_id"],
        "frame_ids": [fr["frame_id"] for fr in hit],
        "mono_ns_first": hit[0]["mono_ns"],
        "mono_ns_last": hit[-1]["mono_ns"],
    }


def find_retreat_window(phases, states, fallback_t=(3.0, 12.0)):
    """phase5d F2 post-retreat ceiling: first retreat → ~3s after."""
    retreat_ts = [p["t"] for p in phases if str(p.get("phase") or "").lower() == "retreat"]
    if not retreat_ts:
        # setpoint phase strings
        retreat_ts = [
            s["t"] for s in states
            if str(s.get("phase") or "").lower() == "retreat"
        ]
    if retreat_ts:
        t0 = min(retreat_ts)
        return t0, t0 + 3.0
    return fallback_t


def run_a1(bundle_frames: dict) -> dict:
    """Three standing FA=0 adversarial segments with frame-id ranges."""
    segments = []

    # 1) F2 banner-fiction t≈7.0-7.5 of 20260716T212408
    f2_old = FIX / "20260716T212744-phase5-closerange-frames"
    log_old = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260716T212408-2ca531c3\flight.jsonl")
    if not log_old.exists():
        # fixture may only have slices; still try phase1 log sibling of github
        cands = list(FIX.glob("**/20260716T212408*flight.jsonl"))
        log_old = cands[0] if cands else log_old
    vision_old = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260716T212408-2ca531c3\vision.aigprec")
    if not vision_old.exists():
        # use close_to_collision slice — covers terminal
        vision_old = f2_old / "20260716T212408-2ca531c3_close_to_collision.aigprec"
        if not vision_old.exists():
            vision_old = f2_old / "20260716T212408-2ca531c3_initial_to_5m.aigprec"

    seg1 = {
        "id": "A1-banner-fiction-F2",
        "description": "F2 banner-fiction / scale-inconsistent lock (D5 garbage)",
        "flight_id": "20260716T212408-2ca531c3",
        "t_range_s": [7.0, 7.5],
        "source_recording": str(vision_old),
        "why_adversarial": (
            "R·w_px ≪ 512; believed ty=+0.31 vs det ty≈−0.95; row-consistency fails"
        ),
        "fa0_expectation": "certificate / scale-gate must REJECT all poses in this window",
    }
    if log_old.exists() and vision_old.exists():
        t0, states, dets, _ = load_log(log_old)
        frames, _ = decode_frames(vision_old)
        frames = align_frame_times_to_log(frames, t0, None)
        # Slice mono may not match full-log mono — also try matching by
        # detection timestamps near 7.0-7.5 if frame t's are slice-relative only
        win = frames_in_log_window(frames, 7.0, 7.5)
        if win is None or win["n_frames"] == 0:
            # Remap: find dets in 7.0-7.5 and use their ts; scan all frames
            # If slice starts mid-flight, compute offset from first det overlap
            if dets and frames:
                # Use absolute mono from log dets vs frame mono
                det_monos = [d["mono_ns"] for d in dets if 7.0 <= d["t"] <= 7.5]
                if det_monos:
                    m_lo, m_hi = min(det_monos), max(det_monos)
                    hit = [fr for fr in frames if m_lo - 5e7 <= fr["mono_ns"] <= m_hi + 5e7]
                    if hit:
                        win = {
                            "t_lo": 7.0,
                            "t_hi": 7.5,
                            "n_frames": len(hit),
                            "frame_id_first": hit[0]["frame_id"],
                            "frame_id_last": hit[-1]["frame_id"],
                            "frame_ids": [fr["frame_id"] for fr in hit],
                            "mono_ns_first": hit[0]["mono_ns"],
                            "mono_ns_last": hit[-1]["mono_ns"],
                        }
        seg1["frame_range"] = win
        seg1["n_dets_in_window"] = sum(1 for d in dets if 7.0 <= d["t"] <= 7.5)
    else:
        seg1["frame_range"] = None
        seg1["error"] = f"missing log/vision: {log_old.exists()} {vision_old.exists()}"
    segments.append(seg1)

    # 2) phase5d F2 post-retreat ceiling view
    meta5d = next(s for s in SLICES if s["fid"] == "20260717T102007-7223cc0c")
    key5d = meta5d["fid"]
    fr5d = bundle_frames.get(key5d)
    log5d = FIX / meta5d["fixture"] / meta5d["log"]
    t0, states, dets, phases = load_log(log5d)
    # Also pull setpoints for retreat
    retreat_lo, retreat_hi = find_retreat_window(phases, states, (3.0, 8.0))
    # Enrich phases from setpoints by re-scan
    with log5d.open(encoding="utf-8") as f:
        retreat_ts = []
        for line in f:
            rec = json.loads(line)
            if t0 is None:
                t0 = int(rec["mono_ns"])
            t = (int(rec["mono_ns"]) - t0) / 1e9
            if rec["topic"] == "setpoint" and rec["data"].get("phase") == "retreat":
                retreat_ts.append(t)
    if retreat_ts:
        retreat_lo, retreat_hi = min(retreat_ts), min(retreat_ts) + 3.5

    seg2 = {
        "id": "A1-phase5d-F2-post-retreat-ceiling",
        "description": "phase5d F2 post-retreat ceiling / upper-truss view",
        "flight_id": "20260717T102007-7223cc0c",
        "t_range_s": [retreat_lo, retreat_hi],
        "source_recording": str(FIX / meta5d["fixture"] / meta5d["slice"]),
        "why_adversarial": (
            "Operator notes ceiling/upper-truss after retreat; false-accept risk "
            "on grid/lights as gate-like structure"
        ),
        "fa0_expectation": "no CERTIFIED gate pose while looking at ceiling",
    }
    if fr5d:
        seg2["frame_range"] = frames_in_log_window(fr5d, retreat_lo, retreat_hi)
    else:
        seg2["frame_range"] = None
    segments.append(seg2)

    # 3) phase5b F3 next-gate-steal t≈6.9-7.3 of 20260717T091239
    fix5b = FIX / "20260717T092008-phase5b-confirm"
    log5b = fix5b / "20260717T091239-debf3ec1-flight.jsonl"
    vis5b = fix5b / "20260717T091239-debf3ec1_takeoff_to_end.aigprec"
    seg3 = {
        "id": "A1-phase5b-F3-next-gate-steal",
        "description": "phase5b F3 next-gate-steal through near opening",
        "flight_id": "20260717T091239-debf3ec1",
        "t_range_s": [6.9, 7.3],
        "source_recording": str(vis5b),
        "why_adversarial": (
            "Terminal ownership failure class: far gate visible through near "
            "opening steals the candidate contest"
        ),
        "fa0_expectation": (
            "near-gate ownership / prediction-consistent boost must win; "
            "far-gate pose must not be CERTIFIED as the active target"
        ),
    }
    if log5b.exists() and vis5b.exists():
        t0b, _, _, _ = load_log(log5b)
        frames_b, _ = decode_frames(vis5b)
        frames_b = align_frame_times_to_log(frames_b, t0b, None)
        seg3["frame_range"] = frames_in_log_window(frames_b, 6.9, 7.3)
    else:
        seg3["frame_range"] = None
        seg3["error"] = "missing phase5b F3 slice/log"
    segments.append(seg3)

    return {
        "suite": "standing_false_accept_zero",
        "n_segments": len(segments),
        "segments": segments,
    }


# ---------------------------------------------------------------------------
# (A4) physical bar width
# ---------------------------------------------------------------------------

def order_corners(corners):
    pts = np.asarray(corners, float).reshape(-1, 2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl, br = pts[np.argmin(s)], pts[np.argmax(s)]
    tr, bl = pts[np.argmin(diff)], pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], float)


def run_a4(meta_list, loaded) -> dict:
    """Bar thickness in meters from a mid/far trusted fix.

    Prefer R in 5–12 m: at R≳20 m a true ~0.1 m tube is ≤2 px and the
    red-mask 'thickness' collapses into banner/bloom. Physical:
    w_bar = bar_px * R / fx.
    """
    candidates = []
    for meta in meta_list:
        fid = meta["fid"]
        t0, states, dets, _ = loaded[fid]["log"]
        frames = loaded[fid]["frames"]
        for d in dets:
            if not d.get("corners") or not (5.0 <= d["dist"] <= 14.0):
                continue
            pts = order_corners(d["corners"])
            w_px = float(np.linalg.norm(pts[1] - pts[0]))
            h_px = float(np.linalg.norm(pts[3] - pts[0]))
            product = d["dist"] * max(w_px, h_px)
            ratio = product / (FX_NOM * GATE_W)
            if not (0.65 <= ratio <= 1.5):
                continue
            if abs(h_px / max(w_px, 1e-6) - 1.0) > 0.45:
                continue  # reject flat strip / banner quads
            fr = min(frames, key=lambda f: abs(f["t"] - d["t"])) if frames else None
            if fr is None or abs(fr["t"] - d["t"]) > 0.15:
                continue
            img = fr["img"]
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            m1 = cv2.inRange(hsv, (0, 80, 80), (12, 255, 255))
            m2 = cv2.inRange(hsv, (165, 80, 80), (180, 255, 255))
            mask = cv2.bitwise_or(m1, m2)
            # Local thickness: at each top-edge sample, count contiguous red
            # along the inward normal (toward opening) only — max 0.25*h_px
            max_run = max(3, int(0.25 * h_px))
            thicknesses = []
            for a in np.linspace(0.25, 0.75, 9):
                p = pts[0] * (1 - a) + pts[1] * a
                # inward = toward bottom of quad
                inward = pts[3] - pts[0]
                inward = inward / (np.linalg.norm(inward) + 1e-9)
                run = 0
                for k in range(max_run):
                    xy = p + inward * k
                    x, y = int(round(xy[0])), int(round(xy[1]))
                    if x < 0 or y < 0 or y >= mask.shape[0] or x >= mask.shape[1]:
                        break
                    if mask[y, x] > 0:
                        run += 1
                    elif run > 0:
                        break
                if run >= 2:
                    thicknesses.append(run)
            if len(thicknesses) < 3:
                continue
            bar_px = float(np.median(thicknesses))
            # Sanity: tube should be << opening height
            if bar_px > 0.35 * h_px:
                continue
            w_bar_m = bar_px * d["dist"] / FX_NOM
            candidates.append({
                "fid": fid,
                "phase": meta["phase"],
                "flight": meta["flight"],
                "t": d["t"],
                "R": d["dist"],
                "ty": d["ty"],
                "quad_width_px": w_px,
                "quad_height_px": h_px,
                "scale_ratio": ratio,
                "bar_thickness_px": bar_px,
                "w_bar_m": w_bar_m,
                "method": "inward_normal_red_run_midrange",
                "frame_id": fr["frame_id"],
                "_fr": fr,
                "_pts": pts,
            })

    if not candidates:
        return {"error": "no mid-range trusted bar thickness", "n_tried": "see log"}

    # Prefer a tube-plausible pick near the cohort median (0.05-0.35 m).
    # R~8 + min bar_px alone still picks bloom-thick frames (~0.4 m).
    ws = [c["w_bar_m"] for c in candidates]
    med = float(__import__("numpy").median(ws))
    plausible = [c for c in candidates if 0.05 <= c["w_bar_m"] <= 0.35]
    pool = plausible if plausible else candidates
    best = min(pool, key=lambda c: (abs(c["w_bar_m"] - med), abs(c["R"] - 8.0), c["bar_thickness_px"]))
    fr = best.pop("_fr")
    pts = best.pop("_pts")
    ann = fr["img"].copy()
    cv2.polylines(ann, [pts.astype(np.int32)], True, (0, 255, 255), 2)
    cv2.putText(
        ann,
        f"w_bar={best['w_bar_m']:.3f}m px={best['bar_thickness_px']:.1f} R={best['R']:.1f}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )
    outp = OUT / "frames" / "a4_bar_width.jpg"
    outp.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(outp), ann)
    best["frame"] = str(outp.relative_to(OUT))
    best["n_candidates"] = len(candidates)
    best["candidate_w_bar_m"] = {
        "median": float(np.median([c["w_bar_m"] for c in candidates])),
        "p10": float(np.percentile([c["w_bar_m"] for c in candidates], 10)),
        "p90": float(np.percentile([c["w_bar_m"] for c in candidates], 90)),
        "n": len(candidates),
    }
    return best


# ---------------------------------------------------------------------------
# (A5) min inter-gate spacing
# ---------------------------------------------------------------------------

def run_a5(meta_list, loaded) -> dict:
    """Minimum inter-gate spacing from frames with two trusted fixes."""
    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    det = HsvGateDetector(params)
    spacings = []
    best_frame = None

    for meta in meta_list:
        fid = meta["fid"]
        frames = loaded[fid]["frames"]
        # Subsample ~every 5th unique frame in mid/far approach
        t0, states, dets, _ = loaded[fid]["log"]
        # Use logged dets: find times with two detections close in time from different centers
        # Better: redetect and look for second red blob / run detector on full image
        # HsvGateDetector returns one gate — use multi-contour fallback via red mask
        step = max(1, len(frames) // 80)
        for fr in frames[::step]:
            img = fr["img"]
            h, w = img.shape[:2]
            # Find multiple red quadrilaterals via contours (same bands as detector)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            m1 = cv2.inRange(hsv, (0, 80, 80), (12, 255, 255))
            m2 = cv2.inRange(hsv, (165, 80, 80), (180, 255, 255))
            mask = cv2.bitwise_or(m1, m2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            quads = []
            for c in cnts:
                area = cv2.contourArea(c)
                if area < 400:
                    continue
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                if len(approx) != 4:
                    rect = cv2.minAreaRect(c)
                    box = cv2.boxPoints(rect)
                    approx = box.reshape(-1, 1, 2)
                pts = approx.reshape(-1, 2).astype(float)
                if pts.shape[0] != 4:
                    continue
                # PnP via detector path
                ordered = order_corners(pts)
                # Use camera solve through a one-off detect on cropped? simpler: pinhole from width
                w_px = float(np.linalg.norm(ordered[1] - ordered[0]))
                if w_px < 25:
                    continue
                cx = float(ordered[:, 0].mean())
                cy = float(ordered[:, 1].mean())
                # Range from width: R = fx * GATE_W / w_px
                R = FX_NOM * GATE_W / w_px
                if not (3.0 <= R <= 45.0):
                    continue
                # Cam t approx: x=(u-cx)*R/fx, y=(v-cy)*R/fx, z≈R
                tx = (cx - w / 2) * R / FX_NOM
                ty = (cy - h / 2) * R / FX_NOM
                tz = R
                # Scale gate check
                h_px = float(np.linalg.norm(ordered[3] - ordered[0]))
                ratio = R * max(w_px, h_px) / (FX_NOM * GATE_W)
                if not (0.65 <= ratio <= 1.5):
                    continue
                quads.append({
                    "center_px": (cx, cy),
                    "R": R,
                    "t": np.array([tx, ty, tz]),
                    "w_px": w_px,
                    "ratio": ratio,
                })
            if len(quads) < 2:
                continue
            # Pairwise 3D spacing
            quads = sorted(quads, key=lambda q: q["R"])
            for i in range(len(quads)):
                for j in range(i + 1, len(quads)):
                    # Require centers separated in image
                    du = abs(quads[i]["center_px"][0] - quads[j]["center_px"][0])
                    if du < 40:
                        continue
                    delta = quads[i]["t"] - quads[j]["t"]
                    spacing = float(np.linalg.norm(delta))
                    if spacing < 2.0 or spacing > 80.0:
                        continue
                    spacings.append({
                        "fid": fid,
                        "phase": meta["phase"],
                        "flight": meta["flight"],
                        "t": fr["t"],
                        "frame_id": fr["frame_id"],
                        "spacing_m": spacing,
                        "R1": quads[i]["R"],
                        "R2": quads[j]["R"],
                        "du_px": du,
                    })
                    if best_frame is None or spacing < best_frame["spacing_m"]:
                        best_frame = spacings[-1]
                        ann = img.copy()
                        for q in quads[:2]:
                            cv2.circle(
                                ann,
                                (int(q["center_px"][0]), int(q["center_px"][1])),
                                6,
                                (0, 255, 0),
                                2,
                            )
                        cv2.putText(
                            ann,
                            f"spacing={spacing:.2f}m",
                            (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                        outp = OUT / "frames" / "a5_intergate_spacing.jpg"
                        outp.parent.mkdir(parents=True, exist_ok=True)
                        cv2.imwrite(str(outp), ann)
                        best_frame["frame"] = str(outp.relative_to(OUT))

    if not spacings:
        return {"error": "no two-gate frames found", "n": 0}
    spacings_sorted = sorted(spacings, key=lambda s: s["spacing_m"])
    vals = [s["spacing_m"] for s in spacings_sorted]
    return {
        "n_pairs": len(vals),
        "min_spacing_m": float(min(vals)),
        "p10_spacing_m": float(np.percentile(vals, 10)),
        "median_spacing_m": float(np.median(vals)),
        "best": best_frame,
        "top5_smallest": spacings_sorted[:5],
    }


# ---------------------------------------------------------------------------
# Report + main
# ---------------------------------------------------------------------------

def write_report(bundle: dict):
    lines = [
        "# ROUND-4 / advisory-4 measurement pack",
        "",
        "AGENTS.md DATA ANALYST item 6 (HEAD ≥ `0cbb682`).",
        "Priority: **(A2/R1)** → (A1) → (A4) → (A5).",
        "",
        "## (A2/R1) Cyan-ribbon availability in last 2 m",
        "",
        "Horizon row = `180 + 320·tan(11°+pitch)`. Offset = cyan_mean_row − horizon "
        "(negative ⇒ cyan ABOVE horizon in the image). LOW-geometry prediction: "
        "≈ −30 px.",
        "",
        "| phase | flight | n | cyan% | above% | med offset px | ~+30 above? | V1≥60% |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for r in bundle.get("a2_r1") or []:
        if r.get("n_frames_last2m", 0) == 0:
            lines.append(
                f"| {r.get('phase')} | {r.get('flight')} | 0 | — | — | — | — | — |"
            )
            continue
        off = (r.get("offset_px") or {}).get("median")
        sig = r.get("low_geometry_signature") or {}
        lines.append(
            f"| {r.get('phase')} | {r.get('flight')} | {r.get('n_frames_last2m')} | "
            f"{r.get('cyan_present_pct'):.1f} | {r.get('above_horizon_pct_of_cyan')} | "
            f"{off} | {sig.get('matches_plus30_above_horizon')} | "
            f"{r.get('v1_gate_bar_ge_60pct')} |"
        )
    # Aggregate
    pcts = [r["cyan_present_pct"] for r in bundle.get("a2_r1") or [] if r.get("n_frames_last2m")]
    lines += [
        "",
        f"**Aggregate cyan presence (per-flight mean):** "
        f"{float(np.mean(pcts)) if pcts else None:.1f}% over {len(pcts)} flights.",
        f"**Flights clearing V1 ≥60% bar:** "
        f"{sum(1 for r in bundle.get('a2_r1') or [] if r.get('v1_gate_bar_ge_60pct'))}/{len(pcts)}.",
        "",
        "## (A1) Standing FA=0 adversarial suite",
        "",
    ]
    a1 = bundle.get("a1") or {}
    for seg in a1.get("segments") or []:
        fr = seg.get("frame_range") or {}
        lines += [
            f"### {seg.get('id')}",
            f"- {seg.get('description')}",
            f"- flight: `{seg.get('flight_id')}`",
            f"- t_range_s: {seg.get('t_range_s')}",
            f"- source: `{seg.get('source_recording')}`",
            f"- frame_id range: {fr.get('frame_id_first')} … {fr.get('frame_id_last')} "
            f"(n={fr.get('n_frames')})",
            f"- FA=0 expectation: {seg.get('fa0_expectation')}",
            "",
        ]
    lines += ["## (A4) Physical bar width `w_bar`", "", f"```json\n{json.dumps(bundle.get('a4'), indent=2)}\n```", ""]
    lines += ["## (A5) Minimum inter-gate spacing", "", f"```json\n{json.dumps(bundle.get('a5'), indent=2)}\n```", ""]
    lines += [
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`, `a1_fa0_manifest.json`",
        "- `a2_r1.csv`, `frames/a4_bar_width.jpg`, `frames/a5_intergate_spacing.jpg`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frames").mkdir(exist_ok=True)

    bundle = {"a2_r1": [], "a1": {}, "a4": {}, "a5": {}}
    loaded = {}
    bundle_frames = {}

    print("=== Loading phase5c+5d slices ===", flush=True)
    for meta in SLICES:
        fixdir = FIX / meta["fixture"]
        log_path = fixdir / meta["log"]
        vis_path = fixdir / meta["slice"]
        print(f"  {meta['phase']} {meta['flight']}: {vis_path.name}", flush=True)
        t0, states, dets, phases = load_log(log_path)
        frames, slice_t0 = decode_frames(vis_path)
        frames = align_frame_times_to_log(frames, t0, slice_t0)
        loaded[meta["fid"]] = {"log": (t0, states, dets, phases), "frames": frames, "meta": meta}
        bundle_frames[meta["fid"]] = frames
        print(f"    frames={len(frames)} dets={len(dets)} states={len(states)}", flush=True)

    print("=== (A2/R1) cyan last 2m ===", flush=True)
    for meta in SLICES:
        t0, states, dets, _ = loaded[meta["fid"]]["log"]
        frames = loaded[meta["fid"]]["frames"]
        r = run_a2_r1(meta, t0, states, dets, frames)
        bundle["a2_r1"].append(r)
        print(
            f"  {meta['phase']} {meta['flight']}: n={r.get('n_frames_last2m')} "
            f"cyan%={r.get('cyan_present_pct')} med_off={((r.get('offset_px') or {}).get('median'))} "
            f"V1={r.get('v1_gate_bar_ge_60pct')}",
            flush=True,
        )

    with (OUT / "a2_r1.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "phase", "flight", "fid", "mode", "n_frames_last2m", "cyan_present_pct",
                "above_horizon_pct_of_cyan", "median_offset_px", "v1_gate_bar_ge_60pct",
            ],
        )
        w.writeheader()
        for r in bundle["a2_r1"]:
            w.writerow({
                "phase": r.get("phase"),
                "flight": r.get("flight"),
                "fid": r.get("fid"),
                "mode": r.get("mode"),
                "n_frames_last2m": r.get("n_frames_last2m"),
                "cyan_present_pct": r.get("cyan_present_pct"),
                "above_horizon_pct_of_cyan": r.get("above_horizon_pct_of_cyan"),
                "median_offset_px": (r.get("offset_px") or {}).get("median"),
                "v1_gate_bar_ge_60pct": r.get("v1_gate_bar_ge_60pct"),
            })

    print("=== (A1) FA=0 manifest ===", flush=True)
    bundle["a1"] = run_a1(bundle_frames)
    for seg in bundle["a1"]["segments"]:
        fr = seg.get("frame_range") or {}
        print(
            f"  {seg['id']}: frames {fr.get('frame_id_first')}..{fr.get('frame_id_last')} "
            f"n={fr.get('n_frames')}",
            flush=True,
        )
    (OUT / "a1_fa0_manifest.json").write_text(
        json.dumps(bundle["a1"], indent=2, default=str), encoding="utf-8"
    )

    print("=== (A4) bar width ===", flush=True)
    bundle["a4"] = run_a4(SLICES, loaded)
    print(bundle["a4"], flush=True)

    print("=== (A5) inter-gate spacing ===", flush=True)
    bundle["a5"] = run_a5(SLICES, loaded)
    print(
        f"  min={bundle['a5'].get('min_spacing_m')} n={bundle['a5'].get('n_pairs')}",
        flush=True,
    )

    write_report(bundle)
    # Strip heavy sample rows from summary
    summary = json.loads(json.dumps(bundle, default=str))
    for r in summary.get("a2_r1") or []:
        r.pop("sample_rows", None)
    for seg in (summary.get("a1") or {}).get("segments") or []:
        fr = seg.get("frame_range")
        if fr and "frame_ids" in fr:
            fr["frame_ids_head"] = fr["frame_ids"][:20]
            fr["frame_ids_tail"] = fr["frame_ids"][-20:]
            fr["n_frame_ids"] = len(fr["frame_ids"])
            del fr["frame_ids"]
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote", OUT / "report.md", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
