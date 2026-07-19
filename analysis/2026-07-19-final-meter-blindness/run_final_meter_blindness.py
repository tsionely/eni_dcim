"""Final-meter blindness autopsy — phase6c F3 vs F1.

Reconstruct detector emissions + close-tracker attempts frame-by-frame
over the terminal dash window. Deliverable feeds the next-build choice:
tracker tuning vs terminal feature.
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
FIX = ROOT / "fixtures" / "20260719T121704-phase6c-true-vertical"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from aigp.core.messages import CameraFrame, ImuSample, RelPose  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.state_estimator import StateEstimator  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.close_tracker import GateCloseTracker  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector, order_corners  # noqa: E402
from reflight import load_frame_monos, load_frames, load_imu  # noqa: E402

F3 = {
    "id": "20260719T121637-f186c83e",
    "label": "F3",
    "window": (6.4, 8.4),
    "note": "geometric termination ~8.38s, age 1.25s, crossed believed z=-0.42",
}
F1 = {
    "id": "20260719T121141-f186c83e",
    "label": "F1",
    "window": (6.4, 8.4),
    "note": "retreat ~8.20s with age 0.00 — vision held; contrast case",
}


def load_log_timeline(path: Path):
    t0 = None
    takeoff_t = None
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            topic = rec["topic"]
            if topic == "setpoint" and d.get("phase") == "takeoff" and takeoff_t is None:
                takeoff_t = t
            if topic == "state":
                gr = d.get("gate_rel")
                tv = gr.get("t") if gr else None
                rows.append({
                    "t": t,
                    "topic": "state",
                    "dist": float(np.linalg.norm(tv)) if tv else None,
                    "t_vec": [float(x) for x in tv] if tv else None,
                    "age": float(d.get("gate_rel_age_s") or 0.0),
                    "phase": d.get("phase"),
                    "center_px": d.get("gate_center_px"),
                    "level_pitch": d.get("level_pitch"),
                })
            elif topic == "setpoint":
                rows.append({"t": t, "topic": "setpoint", "phase": d.get("phase"),
                             "v_body": d.get("v_body")})
            elif topic == "detection" and d.get("rel_pose"):
                tv = [float(x) for x in d["rel_pose"]["t"]]
                rows.append({
                    "t": t, "topic": "detection",
                    "dist": float(np.linalg.norm(tv)),
                    "ty": tv[1], "tz": tv[2],
                    "center": d.get("center_px"),
                    "corners": d.get("corners_px"),
                    "conf": d.get("confidence"),
                })
    return t0, takeoff_t, rows


def classify_fov(corners, center, w=640, h=360) -> dict:
    if corners is None and center is None:
        return {"fov": "unknown", "edge_clip": None, "partial": None}
    pts = None
    if corners is not None:
        pts = np.asarray(corners, float).reshape(-1, 2)
        cx, cy = float(pts[:, 0].mean()), float(pts[:, 1].mean())
    else:
        cx, cy = float(center[0]), float(center[1])
        pts = None
    margin = 8
    touches = []
    if pts is not None:
        if (pts[:, 0] < margin).any():
            touches.append("left")
        if (pts[:, 0] > w - 1 - margin).any():
            touches.append("right")
        if (pts[:, 1] < margin).any():
            touches.append("top")
        if (pts[:, 1] > h - 1 - margin).any():
            touches.append("bottom")
        # span vs image
        bw = float(pts[:, 0].max() - pts[:, 0].min())
        bh = float(pts[:, 1].max() - pts[:, 1].min())
        frac = max(bw / w, bh / h)
    else:
        touches = []
        frac = None
        if cx < margin:
            touches.append("left")
        if cx > w - 1 - margin:
            touches.append("right")
        if cy < margin:
            touches.append("top")
        if cy > h - 1 - margin:
            touches.append("bottom")
    # Bloom heuristic: washed red near center
    return {
        "center_px": [cx, cy],
        "touches_border": touches,
        "edge_clip": bool(touches),
        "partial": bool(touches) or (frac is not None and frac > 0.85),
        "quad_frac": frac,
    }


def bloom_score(img, center) -> dict:
    """Fraction of bright washed-red near gate center."""
    h, w = img.shape[:2]
    cx, cy = int(center[0]), int(center[1])
    r = 40
    x0, x1 = max(0, cx - r), min(w, cx + r)
    y0, y1 = max(0, cy - r), min(h, cy + r)
    patch = img[y0:y1, x0:x1]
    if patch.size == 0:
        return {"bloom_frac": 0.0}
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    washed = cv2.inRange(hsv, (150, 40, 200), (180, 255, 255))
    return {"bloom_frac": float(np.count_nonzero(washed)) / washed.size}


def diagnose_detector(detector: HsvGateDetector, img, prior_range) -> dict:
    """Run detect + explain pose drop (scale/normal/ty) or no-candidate."""
    h, w = img.shape[:2]
    cf = CameraFrame(frame_id=0, ts_ns=0, image=img)
    det = detector.detect(cf, prior_range)
    mask = detector.red_mask(img)
    red_frac = float(np.count_nonzero(mask)) / mask.size
    out = {
        "emitted": det is not None,
        "has_pose": det is not None and det.rel_pose is not None,
        "conf": float(det.confidence) if det else None,
        "center_px": list(det.center_px) if det else None,
        "corners": det.corners_px.tolist() if det is not None else None,
        "red_frac": red_frac,
        "reject_reason": None,
        "R": None,
        "ty": None,
        "nz": None,
        "scale_ratio": None,
        "cert_status": det.cert_status if det else None,
    }
    if det is None:
        out["reject_reason"] = "no_candidate" if red_frac < 0.002 else "no_quad_or_box"
        return out
    # Re-solve PnP to classify pose kill
    rel = detector.camera.solve_gate_pnp(
        det.corners_px, (w, h), detector.gate_w, detector.gate_h
    )
    if rel is None:
        out["reject_reason"] = "pnp_failed"
        return out
    corners = det.corners_px
    w_px = float(np.linalg.norm(corners[1] - corners[0]))
    h_px = float(np.linalg.norm(corners[3] - corners[0]))
    fx = detector.camera.matrix(w, h)[0, 0]
    R = float(np.linalg.norm(rel.t))
    ratio = R * max(w_px, h_px) / (fx * detector.gate_w)
    nz = abs(float(rel.normal[2]))
    ty = float(rel.t[1])
    out.update({"R": R, "ty": ty, "nz": nz, "scale_ratio": ratio,
                "w_px": w_px, "h_px": h_px})
    if det.rel_pose is not None:
        out["reject_reason"] = None
        out["accepted_by_detector"] = True
        return out
    # Pose dropped — which gate?
    reasons = []
    if ratio < detector.scale_min:
        reasons.append(f"scale_low({ratio:.2f}<{detector.scale_min})")
    elif ratio > detector.scale_max:
        reasons.append(f"scale_high({ratio:.2f}>{detector.scale_max})")
    if nz < 0.35:
        reasons.append(f"grazing_normal(|nz|={nz:.2f})")
    if abs(ty) > detector.ty_max:
        reasons.append(f"ty_max(|ty|={ty:.2f}>{detector.ty_max})")
    out["reject_reason"] = "+".join(reasons) if reasons else "pose_dropped_unknown"
    out["accepted_by_detector"] = False
    return out


def diagnose_tracker(tracker: GateCloseTracker, img, prior: RelPose, ts_ns: int) -> dict:
    """Attempt track; if None, report support counts from one measure pass."""
    cf = CameraFrame(frame_id=0, ts_ns=ts_ns, image=img)
    # Probe support without mutating prior heavily — call track, also measure
    h, w = img.shape[:2]
    k = tracker.camera.matrix(w, h)
    mask = tracker.detector.red_mask(img)
    t = np.asarray(prior.t, dtype=np.float64).copy()
    support = 0
    edges_hit = set()
    reason = None
    if not mask.any():
        return {"tracked": False, "support": 0, "edges": 0,
                "reject_reason": "empty_mask", "R": None}

    corners_derot = tracker._corners_derot(t)
    px, opt = tracker._project(corners_derot, k)
    if (opt[:, 2] <= 0.1).any():
        return {"tracked": False, "support": 0, "edges": 0,
                "reject_reason": "projection_behind", "R": float(np.linalg.norm(t))}

    center_px = px.mean(axis=0)
    for e in range(4):
        p0, p1 = px[e], px[(e + 1) % 4]
        edge = p1 - p0
        elen = float(np.linalg.norm(edge))
        if elen < 8.0:
            continue
        n2 = np.array([edge[1], -edge[0]]) / elen
        mid = (p0 + p1) / 2.0
        if float(np.dot(n2, mid - center_px)) < 0:
            n2 = -n2
        hits = 0
        for s in np.linspace(0.12, 0.88, tracker.samples_per_edge):
            sp = p0 + s * edge
            hit = tracker._edge_offset(mask, sp, n2, w, h)
            if hit is not None:
                hits += 1
                support += 1
        if hits > 0:
            edges_hit.add(e)

    need = tracker.min_support if t[2] > 2.5 else max(5, tracker.min_support // 2)
    if support < need or len(edges_hit) < 2:
        reason = f"low_support({support}<{need},edges={len(edges_hit)})"
    else:
        reason = None

    det = tracker.track(cf, prior)
    solo = None
    return {
        "tracked": det is not None and det.rel_pose is not None,
        "support": support,
        "edges": len(edges_hit),
        "need_support": need,
        "reject_reason": None if det is not None else (reason or "track_failed_solve_or_step"),
        "R": float(np.linalg.norm(det.rel_pose.t)) if det and det.rel_pose is not None
        else float(np.linalg.norm(t)),
        "center_px": list(det.center_px) if det else [float(center_px[0]), float(center_px[1])],
        "proj_quad": px.tolist(),
    }


def annotate(img, row: dict, title: str) -> np.ndarray:
    ann = img.copy()
    h, w = ann.shape[:2]
    if row.get("corners"):
        pts = np.asarray(row["corners"], np.int32).reshape(-1, 1, 2)
        color = (0, 255, 0) if row.get("lock_accepted") else (
            (0, 165, 255) if row.get("has_pose") else (0, 0, 255)
        )
        cv2.polylines(ann, [pts], True, color, 2)
    if row.get("tracker_proj"):
        pts = np.asarray(row["tracker_proj"], np.int32).reshape(-1, 1, 2)
        cv2.polylines(ann, [pts], True, (255, 255, 0), 1)
    if row.get("center_px"):
        c = (int(row["center_px"][0]), int(row["center_px"][1]))
        cv2.circle(ann, c, 5, (255, 0, 255), 2)
    lines = [
        title,
        f"t={row.get('t'):.3f} det={row.get('det_reason')} lock={row.get('lock_status')}",
        f"trk={row.get('trk_reason')} support={row.get('trk_support')} age={row.get('age')}",
        f"FOV={row.get('fov_tag')} bloom={row.get('bloom_frac')}",
    ]
    y = 18
    for ln in lines:
        cv2.putText(ann, ln[:90], (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (0, 255, 255), 1, cv2.LINE_AA)
        y += 16
    return ann


def run_window(meta: dict) -> dict:
    fid = meta["id"]
    log = FIX / f"{fid}-flight.jsonl"
    vision = FIX / f"{fid}_takeoff_to_end.aigprec"
    t0_log, takeoff_t, log_rows = load_log_timeline(log)
    t_lo, t_hi = meta["window"]

    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    # Use flight params if present
    pflight = FIX / f"{fid}-params.json"
    if pflight.exists():
        params = apply_patches(ParamSet.load(str(pflight)), [])

    detector = HsvGateDetector(params)
    est = StateEstimator(params)
    tracker = GateCloseTracker(params, detector)

    imu = load_imu(str(log))
    monos = load_frame_monos(str(log))
    frames = load_frames(str(vision), monos)
    if not frames:
        return {"error": "no frames", "fid": fid}

    # Align: mono_ns from frames vs log t0
    # frame t_log = (mono - t0_log)/1e9
    frame_events = []
    for mono, fid_f, sim_ns, img in frames:
        t = (mono - t0_log) / 1e9
        if t_lo - 0.5 <= t <= t_hi + 0.5:
            frame_events.append((mono, t, fid_f, sim_ns, img))

    # IMU warmup
    if frame_events:
        t_warm = frame_events[0][0] - int(3e9)
    else:
        return {"error": "no frames in window", "fid": fid}

    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", mono, (t, fid_f, sim_ns, img))
                 for mono, t, fid_f, sim_ns, img in frame_events])
    # Also feed frames before window for estimator warm-up (from slice start)
    pre = []
    for mono, fid_f, sim_ns, img in frames:
        t = (mono - t0_log) / 1e9
        if t < t_lo - 0.5:
            pre.append((mono, t, fid_f, sim_ns, img))
    # keep last 2s of pre
    pre = [p for p in pre if p[1] >= t_lo - 2.5]
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", mono, (t, fid_f, sim_ns, img))
                 for mono, t, fid_f, sim_ns, img in pre + frame_events])
    events.sort(key=lambda e: e[1])

    rows = []
    last_full_mono = None
    solo_timeouts = 0
    hard_candidates = []

    for kind, mono, payload in events:
        if kind == "imu":
            ts, a, g = payload
            est.predict(ImuSample(ts_ns=ts, accel=a, gyro=g))
            continue
        t, fid_f, sim_ns, img = payload
        in_win = t_lo <= t <= t_hi
        prior_r = None
        gr = est.state.gate_rel
        if gr is not None and est.state.gate_rel_age_s < 1.0:
            prior_r = float(np.linalg.norm(gr.t))

        ddiag = diagnose_detector(detector, img, prior_r)
        lock_status = "n/a"
        lock_accepted = False
        det_obj = None
        if ddiag["emitted"]:
            # Rebuild GateDetection for estimator
            from aigp.core.messages import GateDetection
            corners = np.asarray(ddiag["corners"], float)
            rel = None
            if ddiag["has_pose"]:
                # re-detect quickly for full object
                det_obj = detector.detect(
                    CameraFrame(frame_id=int(fid_f), ts_ns=sim_ns, image=img),
                    prior_r,
                )
            else:
                # center-only emission — still may update? estimator needs rel_pose
                det_obj = detector.detect(
                    CameraFrame(frame_id=int(fid_f), ts_ns=sim_ns, image=img),
                    prior_r,
                )
            if det_obj is not None and det_obj.rel_pose is not None:
                before = est._gate_rel_ts_ns
                # Check lock before update
                t_body = None
                from aigp.perception.camera import cam_to_body
                t_body = cam_to_body(det_obj.rel_pose.t)
                would = est._lock_accepts(t_body)
                est.update_vision(det_obj)
                lock_accepted = est._gate_rel_ts_ns != before
                if lock_accepted:
                    lock_status = "ACCEPTED"
                    last_full_mono = mono
                elif not would:
                    lock_status = "REJECT_lock"
                else:
                    lock_status = "REJECT_other"
            elif det_obj is not None:
                lock_status = "NO_POSE"
            else:
                lock_status = "NO_DET"

        # Tracker path when no accepted full fix
        trk = {"tracked": False, "support": None, "reject_reason": "no_prior",
               "edges": None}
        used_tracker = False
        if est.state.gate_rel is not None:
            # solo timeout check
            if last_full_mono is not None:
                solo_age = (mono - last_full_mono) / 1e9
            else:
                solo_age = 999.0
            if solo_age > tracker.max_solo_s:
                trk = {"tracked": False, "support": None, "edges": None,
                       "reject_reason": f"solo_timeout({solo_age:.2f}>{tracker.max_solo_s})",
                       "R": float(np.linalg.norm(est.state.gate_rel.t))}
                if in_win:
                    solo_timeouts += 1
            else:
                trk = diagnose_tracker(tracker, img, est.state.gate_rel, sim_ns)
                if trk["tracked"] and not lock_accepted:
                    # Feed tracker fix as reflight does
                    det_t = tracker.track(
                        CameraFrame(frame_id=int(fid_f), ts_ns=sim_ns, image=img),
                        est.state.gate_rel,
                    )
                    if det_t is not None and det_t.rel_pose is not None:
                        before = est._gate_rel_ts_ns
                        est.update_vision(det_t)
                        if est._gate_rel_ts_ns != before:
                            lock_status = "ACCEPTED_tracker"
                            lock_accepted = True
                            used_tracker = True

        age = float(est.state.gate_rel_age_s) if est.state.gate_rel is not None else None
        dist_b = float(np.linalg.norm(est.state.gate_rel.t)) if est.state.gate_rel is not None else None
        t_vec = est.state.gate_rel.t.tolist() if est.state.gate_rel is not None else None

        center = ddiag.get("center_px") or trk.get("center_px")
        fov = classify_fov(ddiag.get("corners"), center)
        bloom = bloom_score(img, center) if center else {"bloom_frac": 0.0}

        # FOV tag
        red_frac = float(ddiag.get("red_frac") or 0.0)
        if red_frac < 0.001:
            fov_tag = "no_red"
        elif fov.get("edge_clip"):
            fov_tag = "edge_clip:" + ",".join(fov["touches_border"] or [])
        elif bloom["bloom_frac"] > 0.15:
            fov_tag = "blooming"
        elif fov.get("partial"):
            fov_tag = "partial_large"
        else:
            fov_tag = "in_fov"

        det_reason = (
            "OK_pose" if ddiag.get("has_pose")
            else (ddiag.get("reject_reason") or "none")
        )
        trk_reason = (
            "OK" if trk.get("tracked")
            else (trk.get("reject_reason") or "n/a")
        )

        row = {
            "t": t,
            "frame_id": int(fid_f),
            "in_window": in_win,
            "det_reason": det_reason,
            "has_pose": ddiag.get("has_pose"),
            "conf": ddiag.get("conf"),
            "R_det": ddiag.get("R"),
            "ty": ddiag.get("ty"),
            "nz": ddiag.get("nz"),
            "scale_ratio": ddiag.get("scale_ratio"),
            "lock_status": lock_status,
            "lock_accepted": lock_accepted,
            "trk_reason": trk_reason,
            "trk_support": trk.get("support"),
            "trk_edges": trk.get("edges"),
            "trk_R": trk.get("R"),
            "used_tracker": used_tracker,
            "age": age,
            "believed_dist": dist_b,
            "believed_t": t_vec,
            "center_px": center,
            "corners": ddiag.get("corners"),
            "tracker_proj": trk.get("proj_quad"),
            "fov_tag": fov_tag,
            "bloom_frac": bloom.get("bloom_frac"),
            "red_frac": ddiag.get("red_frac"),
            "touches_border": fov.get("touches_border"),
        }

        if in_win:
            rows.append(row)
            # Hardness score: no accepted fix, close believed range, or reject
            hard = 0
            if not lock_accepted:
                hard += 2
            if det_reason not in ("OK_pose",):
                hard += 2
            if age is not None and age > 0.5:
                hard += 2
            if dist_b is not None and dist_b < 2.5:
                hard += 1
            if "edge_clip" in fov_tag or fov_tag == "blooming":
                hard += 2
            if "scale" in (det_reason or "") or "ty_max" in (det_reason or ""):
                hard += 2
            if "solo_timeout" in (trk_reason or "") or "low_support" in (trk_reason or ""):
                hard += 1
            hard_candidates.append((hard, t, img, row))

    # Log-side: last accepted detection time from flight.jsonl in window
    log_dets = [r for r in log_rows if r["topic"] == "detection"
                and t_lo <= r["t"] <= t_hi]
    log_states = [r for r in log_rows if r["topic"] == "state"
                  and t_lo <= r["t"] <= t_hi]
    setpoints = [r for r in log_rows if r["topic"] == "setpoint"]
    phase_in_win = []
    for r in setpoints:
        if t_lo - 1 <= r["t"] <= t_hi + 1:
            if not phase_in_win or phase_in_win[-1]["phase"] != r["phase"]:
                phase_in_win.append({"t": r["t"], "phase": r["phase"]})

    # Geometric termination: believed z (cam tz or body x) crossing
    cross = None
    prev = None
    for s in log_states:
        if s["t_vec"] is None:
            continue
        # cam z forward; plane cross when tz changes sign or body x
        tz = s["t_vec"][2]
        if prev is not None and prev["t_vec"][2] > 0 and tz <= 0:
            cross = {"t": s["t"], "t_vec": s["t_vec"], "age": s["age"],
                     "believed_z_cam": tz}
        prev = s
    # Also catch min |tz| near termination
    if log_states:
        close = min(
            (s for s in log_states if s["t_vec"] is not None),
            key=lambda s: abs(s["t_vec"][2]) if s["t"] >= t_lo else 1e9,
            default=None,
        )
    else:
        close = None

    # Save hardest frames
    hard_dir = OUT / "frames" / meta["label"]
    hard_dir.mkdir(parents=True, exist_ok=True)
    hard_candidates.sort(key=lambda x: (-x[0], x[1]))
    saved = []
    seen_t = set()
    for hard, t, img, row in hard_candidates:
        key = round(t, 2)
        if key in seen_t:
            continue
        seen_t.add(key)
        ann = annotate(img, row, f"{meta['label']} hard={hard}")
        # downscale for commit size
        small = cv2.resize(ann, (480, 270), interpolation=cv2.INTER_AREA)
        name = f"{meta['label']}_t{t:.2f}_h{hard}.jpg"
        cv2.imwrite(str(hard_dir / name), small, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        saved.append({"file": f"frames/{meta['label']}/{name}", "t": t,
                      "hard": hard, "det_reason": row["det_reason"],
                      "trk_reason": row["trk_reason"], "fov_tag": row["fov_tag"],
                      "age": row["age"], "believed_dist": row["believed_dist"]})
        if len(saved) >= 8:
            break

    # Summaries
    n = len(rows)
    n_pose = sum(1 for r in rows if r["has_pose"])
    n_lock = sum(1 for r in rows if r["lock_accepted"])
    n_trk_ok = sum(1 for r in rows if r["trk_reason"] == "OK" or r["used_tracker"])
    reasons = {}
    for r in rows:
        reasons[r["det_reason"]] = reasons.get(r["det_reason"], 0) + 1
    trk_reasons = {}
    for r in rows:
        trk_reasons[r["trk_reason"]] = trk_reasons.get(r["trk_reason"], 0) + 1
    fov_tags = {}
    for r in rows:
        fov_tags[r["fov_tag"]] = fov_tags.get(r["fov_tag"], 0) + 1

    ages = [r["age"] for r in rows if r["age"] is not None]
    return {
        "fid": fid,
        "label": meta["label"],
        "note": meta["note"],
        "takeoff_t": takeoff_t,
        "window": [t_lo, t_hi],
        "n_frames": n,
        "n_detector_pose": n_pose,
        "n_lock_accepted": n_lock,
        "n_tracker_ok": n_trk_ok,
        "solo_timeout_events": solo_timeouts,
        "det_reason_hist": reasons,
        "trk_reason_hist": trk_reasons,
        "fov_hist": fov_tags,
        "age_end": ages[-1] if ages else None,
        "age_max": max(ages) if ages else None,
        "phase_transitions": phase_in_win,
        "log_dets_in_window": len(log_dets),
        "plane_cross_log": cross,
        "closest_state_sample": {
            "t": close["t"], "t_vec": close["t_vec"], "age": close["age"],
            "dist": close["dist"],
        } if close else None,
        "hard_frames": saved,
        "rows": rows,
    }


def write_report(f3: dict, f1: dict):
    def brief(d):
        if d.get("error"):
            return f"ERROR: {d['error']}"
        return (
            f"frames={d['n_frames']} pose={d['n_detector_pose']} "
            f"lock_ok={d['n_lock_accepted']} trk_ok={d['n_tracker_ok']} "
            f"age_end={d['age_end']} age_max={d['age_max']}"
        )

    lines = [
        "# Final-meter blindness — phase6c F3 vs F1",
        "",
        "Fixture: `fixtures/20260719T121704-phase6c-true-vertical/`.",
        "F3 `20260719T121637` crossed the gate plane on attempt 1 with",
        "`gate_rel` age **1.25 s** (zero accepted fixes in the final ~1.25 s).",
        "This report reconstructs **t = 6.4–8.4 s** (log mono timebase) and",
        "contrasts F1 attempt 1 where vision held through retreat.",
        "",
        "## Requirement question",
        "",
        "What must close the last meter: **close-tracker tuning** (support,",
        "solo timeout, ROI) or a **terminal feature** that does not need a",
        "full certified pose (top-bar / banner row once identity is held)?",
        "",
        "## F3 — terminal dash (blind)",
        "",
        f"- {brief(f3)}",
        f"- note: {f3.get('note')}",
        f"- phase transitions near window: `{f3.get('phase_transitions')}`",
        f"- log detections in window: **{f3.get('log_dets_in_window')}**",
        f"- plane-cross (log): `{f3.get('plane_cross_log')}`",
        f"- closest state sample: `{f3.get('closest_state_sample')}`",
        "",
        "### Detector reject histogram",
        "",
        f"```json\n{json.dumps(f3.get('det_reason_hist'), indent=2)}\n```",
        "",
        "### Close-tracker reject histogram",
        "",
        f"```json\n{json.dumps(f3.get('trk_reason_hist'), indent=2)}\n```",
        "",
        "### FOV / bloom tags",
        "",
        f"```json\n{json.dumps(f3.get('fov_hist'), indent=2)}\n```",
        "",
        "### Hardest frames",
        "",
    ]
    for hf in f3.get("hard_frames") or []:
        lines.append(
            f"- `t={hf['t']:.2f}` hard={hf['hard']} det=`{hf['det_reason']}` "
            f"trk=`{hf['trk_reason']}` fov=`{hf['fov_tag']}` age={hf['age']} "
            f"R̂={hf['believed_dist']} → `{hf['file']}`"
        )
    lines += [
        "",
        "## F1 — contrast (vision held)",
        "",
        f"- {brief(f1)}",
        f"- note: {f1.get('note')}",
        f"- phase transitions near window: `{f1.get('phase_transitions')}`",
        f"- log detections in window: **{f1.get('log_dets_in_window')}**",
        f"- closest state sample: `{f1.get('closest_state_sample')}`",
        "",
        "### Detector reject histogram",
        "",
        f"```json\n{json.dumps(f1.get('det_reason_hist'), indent=2)}\n```",
        "",
        "### Close-tracker reject histogram",
        "",
        f"```json\n{json.dumps(f1.get('trk_reason_hist'), indent=2)}\n```",
        "",
        "### FOV / bloom tags",
        "",
        f"```json\n{json.dumps(f1.get('fov_hist'), indent=2)}\n```",
        "",
        "### Hardest frames",
        "",
    ]
    for hf in f1.get("hard_frames") or []:
        lines.append(
            f"- `t={hf['t']:.2f}` hard={hf['hard']} det=`{hf['det_reason']}` "
            f"trk=`{hf['trk_reason']}` fov=`{hf['fov_tag']}` age={hf['age']} "
            f"R̂={hf['believed_dist']} → `{hf['file']}`"
        )

    # Diff narrative
    lines += [
        "",
        "## What differed (F3 vs F1)",
        "",
    ]
    if not f3.get("error") and not f1.get("error"):
        lines += [
            f"| | F3 | F1 |",
            f"|---|---:|---:|",
            f"| frames in window | {f3['n_frames']} | {f1['n_frames']} |",
            f"| detector poses | {f3['n_detector_pose']} | {f1['n_detector_pose']} |",
            f"| lock accepts | {f3['n_lock_accepted']} | {f1['n_lock_accepted']} |",
            f"| tracker OK | {f3['n_tracker_ok']} | {f1['n_tracker_ok']} |",
            f"| age at window end | {f3['age_end']} | {f1['age_end']} |",
            f"| log dets in window | {f3['log_dets_in_window']} | {f1['log_dets_in_window']} |",
            "",
        ]

    lines += [
        "## Spec implication (next build)",
        "",
        "Read the histograms + hard frames before choosing:",
        "",
        "1. **If** rejects are dominated by `scale_low` / `ty_max` / `grazing_normal` "
        "while the ring is still visually present → the **full-pose detector is the "
        "wrong sensor** in the last meter; keep identity from an earlier certified "
        "fix and close with **tracker + terminal feature** (top-bar/banner row).",
        "2. **If** rejects are `low_support` / `solo_timeout` with edges still in "
        "FOV → **tracker tuning** (min_support, max_solo_s, search_px) can recover "
        "fixes without a new feature.",
        "3. **If** FOV is `edge_clip` / ring gone → neither detector nor edge "
        "tracker can invent geometry; need **border-exit / structure-identity** "
        "terminal channel or an earlier commit slowdown.",
        "4. F1 holding age≈0 through the same clock window means the pipeline "
        "*can* keep fixes at that geometry — F3's blindness is situational "
        "(approach geometry / bloom / clip), not a universal last-meter blackout.",
        "",
        "## Deliverables",
        "",
        "- `final-meter-blindness.md` (this file)",
        "- `summary.json`, `f3_timeline.csv`, `f1_timeline.csv`",
        "- `frames/F3/*.jpg`, `frames/F1/*.jpg` (hardest 6–8 each)",
        "",
    ]
    (OUT / "final-meter-blindness.md").write_text("\n".join(lines), encoding="utf-8")
    # Also top-level path user asked for
    (ROOT / "analysis" / "2026-07-19-final-meter-blindness.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def dump_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = [
        "t", "frame_id", "det_reason", "has_pose", "conf", "R_det", "ty", "nz",
        "scale_ratio", "lock_status", "lock_accepted", "trk_reason", "trk_support",
        "trk_edges", "age", "believed_dist", "fov_tag", "bloom_frac", "red_frac",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frames").mkdir(exist_ok=True)
    print("=== F3 window ===", flush=True)
    f3 = run_window(F3)
    print(
        f"  frames={f3.get('n_frames')} pose={f3.get('n_detector_pose')} "
        f"lock={f3.get('n_lock_accepted')} age_end={f3.get('age_end')}",
        flush=True,
    )
    print("  det", f3.get("det_reason_hist"), flush=True)
    print("  trk", f3.get("trk_reason_hist"), flush=True)

    print("=== F1 window ===", flush=True)
    f1 = run_window(F1)
    print(
        f"  frames={f1.get('n_frames')} pose={f1.get('n_detector_pose')} "
        f"lock={f1.get('n_lock_accepted')} age_end={f1.get('age_end')}",
        flush=True,
    )
    print("  det", f1.get("det_reason_hist"), flush=True)
    print("  trk", f1.get("trk_reason_hist"), flush=True)

    dump_csv(OUT / "f3_timeline.csv", f3.get("rows") or [])
    dump_csv(OUT / "f1_timeline.csv", f1.get("rows") or [])
    write_report(f3, f1)

    # Slim summary (no full rows)
    def slim(d):
        return {k: v for k, v in d.items() if k != "rows"}
    summary = {"f3": slim(f3), "f1": slim(f1)}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str),
                                      encoding="utf-8")
    print("Wrote", OUT / "final-meter-blindness.md", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
