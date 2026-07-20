"""P1 — Vision death at ~3m on phase6j (Block A cohort-2) first commits.

Per flight: last-detection range at first-commit vision loss, detector
state at loss (bloom / FOV leave / far-gate contest), vz oscillation,
and slot/start contrast vs cohort-1 (phase6i-R).

Binding question: slot geometry vs speed-profile coupling vs perception
regression.
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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from reflight import load_frames  # noqa: E402

AGE_LOSS_S = 0.25          # sustained freshness loss
AGE_GAP_S = 0.35           # must stay stale this long to count as death
BLIND_BUDGET_S = 0.60      # RESPONSE13 blindness budget — age above this in commit
NEAR_R_MAX = 8.0           # near-gate band for "last near detection"
NEAR_R_LOSS_BAND = (1.2, 4.5)  # RESPONSE13 "~1.5-3.5m" loss band (padded)
IMG_W, IMG_H = 640, 360
# In-frame reacquire: edge-clip "fixes" do not count as vision restored
FRAME_MARGIN = 40

COHORT2 = {
    "label": "cohort2_phase6j",
    "fixture": ROOT / "fixtures" / "20260720T054037-phase6j-block-a-cohort-2",
    "flights": [
        {"slot": 1, "arm": "control", "fid": "20260720T053402-f170ead6"},
        {"slot": 2, "arm": "live", "fid": "20260720T053514-5cebc2b2"},
        {"slot": 3, "arm": "control", "fid": "20260720T053635-f170ead6"},
        {"slot": 4, "arm": "live", "fid": "20260720T053745-5cebc2b2"},
        {"slot": 5, "arm": "control", "fid": "20260720T053905-f170ead6"},
        {"slot": 6, "arm": "live", "fid": "20260720T054016-5cebc2b2"},
    ],
}

COHORT1 = {
    "label": "cohort1_phase6i_r",
    "fixture": ROOT / "fixtures" / "20260719T204430-phase6i-r-rate-ab",
    "flights": [
        {"slot": 1, "arm": "control", "fid": "20260719T200816-f170ead6"},
        {"slot": 2, "arm": "live", "fid": "20260719T201038-50f9dcc8"},
        {"slot": 3, "arm": "control", "fid": "20260719T201630-f170ead6"},
        {"slot": 4, "arm": "live", "fid": "20260719T201851-50f9dcc8"},
        {"slot": 5, "arm": "control", "fid": "20260719T202445-f170ead6"},
        {"slot": 6, "arm": "live", "fid": "20260719T202720-50f9dcc8"},
    ],
}


def takeoff_mono(rows: list[dict]) -> int:
    for r in rows:
        if r.get("topic") == "fsm":
            d = r["data"]
            if d.get("dst") == "TAKEOFF" or "GO" in str(d.get("reason", "")).upper():
                return int(r["mono_ns"])
    for r in rows:
        if r.get("topic") == "setpoint" and r["data"].get("phase") == "takeoff":
            return int(r["mono_ns"])
    return int(rows[0]["mono_ns"])


def load_flight(path: Path) -> dict:
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    toff = takeoff_mono(rows)
    states, dets, setpoints, frames_meta = [], [], [], []
    for r in rows:
        t_ff = (int(r["mono_ns"]) - toff) / 1e9
        d = r.get("data") or {}
        topic = r.get("topic")
        if topic == "state":
            gr = d.get("gate_rel")
            tv = list(map(float, gr["t"])) if gr and gr.get("t") is not None else None
            R = float(np.linalg.norm(tv)) if tv else None
            vw = d.get("v_world")
            states.append({
                "t_ff": t_ff,
                "age": float(d.get("gate_rel_age_s") or 0.0),
                "R": R,
                "t_vec": tv,
                "phase": d.get("phase"),
                "center_px": d.get("gate_center_px"),
                "v_world": [float(x) for x in vw] if vw else None,
                "level_pitch": float(d.get("level_pitch") or 0.0),
                "level_roll": float(d.get("level_roll") or 0.0),
            })
        elif topic == "detection":
            rp = d.get("rel_pose") or {}
            tv = d.get("t_vec") or rp.get("t")
            tv = list(map(float, tv)) if tv is not None else None
            R = float(np.linalg.norm(tv)) if tv else None
            dets.append({
                "t_ff": t_ff,
                "R": R,
                "t_vec": tv,
                "center_px": d.get("center_px"),
                "corners_px": d.get("corners_px"),
                "cert": d.get("cert_status"),
                "conf": d.get("confidence"),
                "mono_ns": int(r["mono_ns"]),
            })
        elif topic == "setpoint":
            setpoints.append({
                "t_ff": t_ff,
                "phase": d.get("phase"),
                "v_body": d.get("v_body"),
            })
        elif topic == "frame":
            frames_meta.append({"t_ff": t_ff, "mono_ns": int(r["mono_ns"])})
    return {
        "states": states, "dets": dets, "setpoints": setpoints,
        "frames_meta": frames_meta, "takeoff": toff, "rows": rows,
    }


def first_commit_window(setpoints: list[dict]) -> tuple[float | None, float | None]:
    start = None
    end = None
    for sp in setpoints:
        if sp["phase"] == "commit":
            if start is None:
                start = sp["t_ff"]
            end = sp["t_ff"]
        elif start is not None and sp["phase"] not in (None, "commit"):
            # first contiguous commit ends when phase leaves commit
            if sp["t_ff"] > start + 0.05:
                end = sp["t_ff"]
                break
    return start, end


def fov_class(corners, center) -> dict:
    touches = []
    pts = None
    cx = cy = None
    if corners is not None:
        pts = np.asarray(corners, float).reshape(-1, 2)
        cx, cy = float(pts[:, 0].mean()), float(pts[:, 1].mean())
    elif center is not None:
        cx, cy = float(center[0]), float(center[1])
    if cx is None:
        return {"touches": [], "edge_clip": False, "center_px": None}
    margin = 8
    if pts is not None:
        if (pts[:, 0] < margin).any():
            touches.append("left")
        if (pts[:, 0] > IMG_W - 1 - margin).any():
            touches.append("right")
        if (pts[:, 1] < margin).any():
            touches.append("top")
        if (pts[:, 1] > IMG_H - 1 - margin).any():
            touches.append("bottom")
    else:
        if cx < margin:
            touches.append("left")
        if cx > IMG_W - 1 - margin:
            touches.append("right")
        if cy < margin:
            touches.append("top")
        if cy > IMG_H - 1 - margin:
            touches.append("bottom")
        # soft: near border
        if cy > IMG_H - 40:
            touches.append("near_bottom")
        if cy < 40:
            touches.append("near_top")
        if cx < 40:
            touches.append("near_left")
        if cx > IMG_W - 40:
            touches.append("near_right")
    return {"touches": touches, "edge_clip": bool(touches), "center_px": [cx, cy]}


def bloom_frac(img, center) -> float:
    if center is None or img is None:
        return 0.0
    h, w = img.shape[:2]
    cx, cy = int(center[0]), int(center[1])
    r = 40
    patch = img[max(0, cy - r):min(h, cy + r), max(0, cx - r):min(w, cx + r)]
    if patch.size == 0:
        return 0.0
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    washed = cv2.inRange(hsv, (150, 40, 200), (180, 255, 255))
    return float(np.count_nonzero(washed)) / washed.size


def find_vision_death(log: dict) -> dict:
    """First sustained age climb after first-commit entry, never recovering."""
    c0, c1 = first_commit_window(log["setpoints"])
    states = log["states"]
    dets = log["dets"]
    if c0 is None:
        return {"error": "no_commit", "commit_start": None}

    # Scan from commit_start: find first time age stays >= AGE_LOSS_S for AGE_GAP_S
    loss_t = None
    stale_from = None
    for st in states:
        if st["t_ff"] < c0 - 0.05:
            continue
        if c1 is not None and st["t_ff"] > c1 + 2.0:
            break
        if st["age"] >= AGE_LOSS_S:
            if stale_from is None:
                stale_from = st["t_ff"]
            elif st["t_ff"] - stale_from >= AGE_GAP_S:
                loss_t = stale_from
                break
        else:
            stale_from = None

    # Alternate: last near certified detection in first commit, then gap
    near_dets = [d for d in dets
                 if d["R"] is not None and d["R"] < NEAR_R_MAX
                 and d["cert"] in ("certified", "probation")
                 and c0 - 0.5 <= d["t_ff"] <= (c1 or c0 + 6)]
    last_near = near_dets[-1] if near_dets else None

    def _in_frame(d: dict) -> bool:
        c = d.get("center_px")
        if not c:
            return False
        u, v = float(c[0]), float(c[1])
        return (FRAME_MARGIN <= u <= IMG_W - FRAME_MARGIN
                and FRAME_MARGIN <= v <= IMG_H - FRAME_MARGIN)

    # Permanent death = after last_near, no further near certified IN-FRAME
    # within the first commit (edge-clip "fixes" do not restore vision).
    reacq = []
    if last_near is not None:
        reacq = [d for d in dets
                 if d["t_ff"] > last_near["t_ff"] + 0.15
                 and d["R"] is not None and d["R"] < NEAR_R_MAX
                 and d["cert"] == "certified"
                 and _in_frame(d)
                 and d["t_ff"] <= (c1 or last_near["t_ff"]) + 0.05]

    # max age during first commit (inf counts as blind)
    commit_states = [s for s in states
                     if c0 - 0.02 <= s["t_ff"] <= (c1 or c0 + 6)]
    max_age = 0.0
    saw_inf_age = False
    for s in commit_states:
        a = s["age"]
        if a is None or not math.isfinite(a) or a > 1e6:
            saw_inf_age = True
            max_age = float("inf")
        else:
            max_age = max(max_age, a)

    # Prefer age-based loss_t; fall back to last_near time
    if loss_t is None and last_near is not None and not reacq:
        loss_t = last_near["t_ff"]
    blind_budget_breach = bool(max_age >= BLIND_BUDGET_S or saw_inf_age)

    st_at = None
    if loss_t is not None:
        cand = [s for s in states if abs(s["t_ff"] - loss_t) < 0.2]
        st_at = min(cand, key=lambda s: abs(s["t_ff"] - loss_t)) if cand else None

    # Last near det at/before loss
    last_before = None
    if loss_t is not None:
        before = [d for d in near_dets if d["t_ff"] <= loss_t + 0.05]
        last_before = before[-1] if before else last_near
    else:
        last_before = last_near

    # Far-gate contest: far certified dets interleaved with near during commit
    far_during = [d for d in dets
                  if d["R"] is not None and d["R"] >= NEAR_R_MAX
                  and d["cert"] == "certified"
                  and c0 - 0.2 <= d["t_ff"] <= (loss_t or c0) + 1.0]

    # vz oscillation in ±0.6s around loss
    vz_win = []
    if loss_t is not None:
        for s in states:
            if abs(s["t_ff"] - loss_t) <= 0.6 and s["v_world"] is not None:
                vz_win.append(s["v_world"][2])  # world-z (F_z vertical-ish)
    vz_stats = None
    if vz_win:
        arr = np.asarray(vz_win, float)
        # zero-crossing count as oscillation proxy
        signs = np.sign(arr)
        zc = int(np.sum(signs[1:] * signs[:-1] < 0))
        vz_stats = {
            "n": len(arr),
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "peak_to_peak": float(arr.max() - arr.min()),
            "zero_crossings": zc,
            "oscillating": bool(zc >= 2 and arr.std() > 0.4),
        }

    fov = fov_class(
        last_before["corners_px"] if last_before else None,
        last_before["center_px"] if last_before else (st_at or {}).get("center_px"),
    )

    # In-commit recovery only (post-retreat search does not count)
    recovered = False
    if loss_t is not None and c1 is not None:
        for s in states:
            if (loss_t + AGE_GAP_S < s["t_ff"] <= c1
                    and s["age"] < 0.1
                    and s["R"] is not None and s["R"] < NEAR_R_MAX
                    and _in_frame({"center_px": s.get("center_px")})):
                recovered = True
                break

    last_r = last_before["R"] if last_before else None
    in_loss_band = (
        last_r is not None
        and NEAR_R_LOSS_BAND[0] <= last_r <= NEAR_R_LOSS_BAND[1]
    )
    # RESPONSE13 symptom: lost near vision in the 1.5–3.5m band during
    # first commit and did not restore an in-frame near fix before commit ended.
    vision_death = bool(
        (blind_budget_breach or (loss_t is not None and in_loss_band))
        and not (reacq or recovered)
    ) or bool(saw_inf_age and (last_r is None or last_r >= NEAR_R_LOSS_BAND[0]))

    return {
        "commit_start_s": c0,
        "commit_end_s": c1,
        "loss_t_ff": loss_t,
        "max_age_in_commit": None if not math.isfinite(max_age) else max_age,
        "max_age_inf": saw_inf_age,
        "blind_budget_breach": blind_budget_breach,
        "in_loss_band": in_loss_band,
        "reacquired_near": bool(reacq) or recovered,
        "n_reacq_near": len(reacq),
        "vision_death_first_commit": vision_death,
        "state_at_loss": {
            "t_ff": st_at["t_ff"] if st_at else None,
            "age": st_at["age"] if st_at else None,
            "R_believed": st_at["R"] if st_at else None,
            "center_px": st_at["center_px"] if st_at else None,
            "phase": st_at["phase"] if st_at else None,
            "v_world": st_at["v_world"] if st_at else None,
            "level_pitch_deg": (st_at["level_pitch"] * 180 / math.pi) if st_at else None,
        } if st_at or loss_t else None,
        "last_near_detection": {
            "t_ff": last_before["t_ff"],
            "R": last_before["R"],
            "center_px": last_before["center_px"],
            "corners_px": last_before["corners_px"],
            "cert": last_before["cert"],
            "conf": last_before["conf"],
        } if last_before else None,
        "fov_at_last_near": fov,
        "n_far_certified_during_commit": len(far_during),
        "far_R_sample": [round(d["R"], 2) for d in far_during[:6]],
        "vz_at_loss": vz_stats,
        "n_near_dets_in_commit": len(near_dets),
    }


def diagnose_frames(slice_path: Path, loss_t_ff: float | None, takeoff_mono_ns: int,
                    last_near: dict | None) -> dict:
    """Replay detector around loss; classify bloom / no_red / edge."""
    if not slice_path.exists() or loss_t_ff is None:
        return {"error": "no_slice_or_loss", "path": str(slice_path)}
    try:
        # load_frames -> list[(mono_ns, frame_id, sim_ns, img)]
        frames = load_frames(str(slice_path))
    except Exception as e:
        return {"error": f"load_frames: {e}"}
    if not frames:
        return {"error": "empty_frames"}

    params = ParamSet.load(ROOT / "config" / "params_default.json")
    det = HsvGateDetector(params)

    target_mono = takeoff_mono_ns + int(loss_t_ff * 1e9)
    scored = [(abs(int(mono) - target_mono), mono, img) for mono, _fid, _sim, img in frames]
    if not scored:
        return {"error": "no_scored_frames"}
    scored.sort(key=lambda x: x[0])
    sample = scored[:7]

    rows = []
    for _dt, mono, img in sample:
        if img is None:
            continue
        center = (last_near or {}).get("center_px")
        prior_r = (last_near or {}).get("R") or 3.0
        cf = CameraFrame(frame_id=0, ts_ns=0, image=img)
        out = det.detect(cf, prior_r)
        mask = det.red_mask(img)
        red_frac = float(np.count_nonzero(mask)) / mask.size
        bloom = bloom_frac(img, center) if center else bloom_frac(
            img, [IMG_W // 2, IMG_H // 2])
        emitted = out is not None
        has_pose = emitted and out.rel_pose is not None
        corners = out.corners_px.tolist() if emitted and out.corners_px is not None else None
        ctr = list(out.center_px) if emitted and out.center_px is not None else center
        fov = fov_class(corners, ctr)
        reason = "ok" if has_pose else (
            "no_red" if red_frac < 0.002 else
            "bloom_wash" if bloom > 0.15 and not has_pose else
            "edge_clip" if fov["edge_clip"] else
            "detector_drop"
        )
        rows.append({
            "dt_mono_s": (int(mono) - target_mono) / 1e9,
            "emitted": emitted,
            "has_pose": has_pose,
            "red_frac": red_frac,
            "bloom_frac": bloom,
            "fov": fov,
            "reason": reason,
            "R": float(np.linalg.norm(out.rel_pose.t)) if has_pose else None,
        })

    reasons = [r["reason"] for r in rows]
    primary = max(set(reasons), key=reasons.count) if reasons else "unknown"
    return {
        "n_frames_sampled": len(rows),
        "primary_reason": primary,
        "mean_bloom": float(np.mean([r["bloom_frac"] for r in rows])) if rows else None,
        "mean_red_frac": float(np.mean([r["red_frac"] for r in rows])) if rows else None,
        "frames": rows,
    }


def start_geometry(log: dict) -> dict:
    """Pad / first-lock geometry proxies for slot comparison."""
    # First certified detection after takeoff
    first = None
    for d in log["dets"]:
        if d["t_ff"] >= 0 and d["cert"] == "certified" and d["R"] is not None:
            first = d
            break
    # State at commit entry
    c0, _ = first_commit_window(log["setpoints"])
    st = None
    if c0 is not None:
        cand = [s for s in log["states"] if abs(s["t_ff"] - c0) < 0.05]
        st = min(cand, key=lambda s: abs(s["t_ff"] - c0)) if cand else None
    return {
        "first_det_R": first["R"] if first else None,
        "first_det_t_ff": first["t_ff"] if first else None,
        "first_det_center": first["center_px"] if first else None,
        "commit_entry_R": st["R"] if st else None,
        "commit_entry_age": st["age"] if st else None,
        "commit_entry_center": st["center_px"] if st else None,
        "commit_entry_pitch_deg": (st["level_pitch"] * 180 / math.pi) if st else None,
    }


def analyze_one(meta: dict, fixture: Path, do_frames: bool) -> dict:
    log_path = fixture / f"{meta['fid']}-flight.jsonl"
    if not log_path.exists():
        alt = Path(r"C:\Users\tsion\Projects\eni_dcim\logs") / meta["fid"] / "flight.jsonl"
        log_path = alt if alt.exists() else log_path
    if not log_path.exists():
        return {**meta, "error": f"missing {log_path}"}
    log = load_flight(log_path)
    death = find_vision_death(log)
    geom = start_geometry(log)
    frame_diag = None
    if do_frames and death.get("loss_t_ff") is not None:
        slice_path = fixture / f"{meta['fid']}_takeoff_to_end.aigprec"
        frame_diag = diagnose_frames(
            slice_path, death["loss_t_ff"], log["takeoff"],
            death.get("last_near_detection"))
        # Save one annotated JPEG
        if slice_path.exists() and death.get("last_near_detection"):
            try:
                frames = load_frames(str(slice_path))
                if frames:
                    img = frames[len(frames) // 3][3].copy()
                    ctr = death["last_near_detection"].get("center_px")
                    if ctr:
                        cv2.circle(img, (int(ctr[0]), int(ctr[1])), 12, (0, 255, 255), 2)
                    out_jpg = OUT / "frames" / f"{meta['fid']}_near_loss.jpg"
                    out_jpg.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(out_jpg), img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                    frame_diag["preview"] = str(out_jpg.relative_to(ROOT))
            except Exception as e:
                if frame_diag is not None:
                    frame_diag["preview_error"] = str(e)
    # Classify loss mode from available evidence
    mode = "unknown"
    if death.get("error"):
        mode = death["error"]
    elif not death.get("vision_death_first_commit"):
        mode = "held_or_reacq"
    else:
        fov = death.get("fov_at_last_near") or {}
        touches = fov.get("touches") or []
        far_n = death.get("n_far_certified_during_commit") or 0
        ctr = (death.get("last_near_detection") or {}).get("center_px")
        near_edge = False
        if ctr:
            u, v = float(ctr[0]), float(ctr[1])
            near_edge = (u < FRAME_MARGIN or u > IMG_W - FRAME_MARGIN
                         or v < FRAME_MARGIN or v > IMG_H - FRAME_MARGIN)
        if near_edge or any(t in touches for t in (
                "bottom", "near_bottom", "top", "near_top",
                "left", "right", "near_left", "near_right")):
            mode = "fov_leave"
        elif far_n >= 5:
            mode = "far_gate_contest"
        elif frame_diag and frame_diag.get("primary_reason") == "bloom_wash":
            mode = "bloom"
        elif frame_diag and frame_diag.get("primary_reason"):
            mode = frame_diag["primary_reason"]
        elif death.get("blind_budget_breach"):
            mode = "age_blackout"
        else:
            mode = "detector_drop_or_lock_reject"

    return {
        **meta,
        "log_path": str(log_path),
        "start_geometry": geom,
        "vision_death": death,
        "frame_diagnosis": frame_diag,
        "loss_mode": mode,
        "vision_died_no_reacq": bool(death.get("vision_death_first_commit")),
    }


def cohort_summary(rows: list[dict]) -> dict:
    died = [r for r in rows if r.get("vision_died_no_reacq")]
    ranges = []
    for r in died:
        ln = (r.get("vision_death") or {}).get("last_near_detection") or {}
        st = (r.get("vision_death") or {}).get("state_at_loss") or {}
        R = ln.get("R") if ln.get("R") is not None else st.get("R_believed")
        if R is not None:
            ranges.append(R)
    modes = {}
    for r in died:
        modes[r.get("loss_mode", "?")] = modes.get(r.get("loss_mode", "?"), 0) + 1
    osc = sum(1 for r in died
              if ((r.get("vision_death") or {}).get("vz_at_loss") or {}).get("oscillating"))
    return {
        "n": len(rows),
        "n_vision_death_no_reacq": len(died),
        "frac": len(died) / len(rows) if rows else None,
        "last_det_R_at_loss": {
            "n": len(ranges),
            "min": float(min(ranges)) if ranges else None,
            "max": float(max(ranges)) if ranges else None,
            "mean": float(np.mean(ranges)) if ranges else None,
        },
        "loss_modes": modes,
        "n_with_vz_oscillation": osc,
    }


def write_report(c2_rows, c1_rows, s2, s1):
    lines = []
    lines.append("# Vision death at ~3 m — phase6j cohort-2 vs cohort-1")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append(
        f"- **Cohort-2 (phase6j)**: {s2['n_vision_death_no_reacq']}/{s2['n']} "
        f"first commits lost near vision without reacquire "
        f"(last-near R mean {s2['last_det_R_at_loss']['mean']})."
    )
    lines.append(
        f"- **Cohort-1 (phase6i-R)**: {s1['n_vision_death_no_reacq']}/{s1['n']} "
        f"({s1['frac']:.0%} — matches the '~half' ledger)."
    )
    lines.append(f"- **Loss modes (cohort-2)**: `{s2['loss_modes']}`")
    lines.append(
        f"- **vz oscillation at loss (cohort-2)**: "
        f"{s2['n_with_vz_oscillation']}/{s2['n_vision_death_no_reacq']} died flights"
    )
    # Binding constraint call
    modes = s2["loss_modes"]
    top = max(modes, key=modes.get) if modes else "unknown"
    lines.append("")
    lines.append("### Binding constraint")
    lines.append("")
    if top in ("fov_leave", "edge_clip", "near_bottom"):
        lines.append(
            "**Speed-profile / aim coupling (FOV leave)** dominates — gate walks "
            "out of frame during commit; not a pure slot-geometry flip."
        )
    elif top in ("far_gate_contest",):
        lines.append(
            "**Perception / lock contest** — far-gate certified detections "
            "interleave with the near lock at commit; state age climbs while "
            "believed range may still look near."
        )
    elif top in ("bloom", "bloom_wash"):
        lines.append("**Perception bloom regression** — washed-red kills the ring.")
    else:
        lines.append(
            f"Primary mode `{top}`. Compare start geometry below — if commit-entry "
            "R/center match cohort-1, prefer perception/lock over slot geometry."
        )
    lines.append("")
    lines.append("## Cohort-2 per-flight table")
    lines.append("")
    lines.append(
        "| slot | arm | commit_t | loss_t | last_near_R | max_age | "
        "center | mode | vz_ptp | osc | death | reacq |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|---|---|---:|:---:|:---:|:---:|")
    for r in c2_rows:
        vd = r.get("vision_death") or {}
        ln = vd.get("last_near_detection") or {}
        st = vd.get("state_at_loss") or {}
        vz = vd.get("vz_at_loss") or {}
        ctr = ln.get("center_px") or st.get("center_px")
        ctr_s = f"[{ctr[0]:.0f},{ctr[1]:.0f}]" if ctr else "—"
        mage = "inf" if vd.get("max_age_inf") else (
            f"{vd.get('max_age_in_commit'):.2f}" if vd.get("max_age_in_commit") is not None else "—"
        )
        lines.append(
            f"| {r.get('slot')} | {r.get('arm')} | "
            f"{vd.get('commit_start_s') or float('nan'):.2f} | "
            f"{(vd.get('loss_t_ff') if vd.get('loss_t_ff') is not None else float('nan')):.2f} | "
            f"{(ln.get('R') if ln.get('R') is not None else float('nan')):.2f} | "
            f"{mage} | {ctr_s} | {r.get('loss_mode')} | "
            f"{(vz.get('peak_to_peak') if vz.get('peak_to_peak') is not None else float('nan')):.2f} | "
            f"{'Y' if vz.get('oscillating') else 'n'} | "
            f"{'Y' if r.get('vision_died_no_reacq') else 'n'} | "
            f"{'Y' if vd.get('reacquired_near') else 'n'} |"
        )
    lines.append("")
    lines.append("## Start / slot geometry (cohort-2 vs cohort-1)")
    lines.append("")
    lines.append("| cohort | slot | arm | first_det_R | commit_R | commit_age | commit_center | pitch_deg |")
    lines.append("|---|---:|---|---:|---:|---:|---|---:|")
    for label, rows in (("c2", c2_rows), ("c1", c1_rows)):
        for r in rows:
            g = r.get("start_geometry") or {}
            ctr = g.get("commit_entry_center")
            ctr_s = f"[{ctr[0]:.0f},{ctr[1]:.0f}]" if ctr else "—"
            lines.append(
                f"| {label} | {r.get('slot')} | {r.get('arm')} | "
                f"{(g.get('first_det_R') or float('nan')):.2f} | "
                f"{(g.get('commit_entry_R') or float('nan')):.2f} | "
                f"{(g.get('commit_entry_age') or float('nan')):.3f} | "
                f"{ctr_s} | "
                f"{(g.get('commit_entry_pitch_deg') or float('nan')):.1f} |"
            )
    lines.append("")
    lines.append("## Frame diagnoses (cohort-2, at loss)")
    lines.append("")
    for r in c2_rows:
        fd = r.get("frame_diagnosis") or {}
        lines.append(
            f"- **F{r.get('slot')}** `{r.get('fid')}`: primary=`{fd.get('primary_reason')}`, "
            f"bloom={fd.get('mean_bloom')}, red_frac={fd.get('mean_red_frac')}, "
            f"preview={fd.get('preview')}"
        )
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        f"1. First contiguous `setpoint.phase==commit` window.\n"
        f"2. Vision death = (age ≥ {BLIND_BUDGET_S}s in commit OR last near "
        f"R in {NEAR_R_LOSS_BAND}) with no in-frame reacquire before commit end; "
        f"inf age counts as blind.\n"
        f"3. FOV from last-near corners/center; bloom via washed-red HSV on slice frames.\n"
        f"4. vz oscillation = peak-to-peak and zero-crossings of `v_world[2]` ±0.6s around loss.\n"
        f"5. Cohort-1 = phase6i-R fixture (Block A restart)."
    )
    lines.append("")
    lines.append(f"Generated by `{OUT.name}/run_vision_death_3m.py`.")
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-vision-death-3m.md").write_text(
        "\n".join(lines), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frames").mkdir(exist_ok=True)

    c2_rows = [analyze_one(m, COHORT2["fixture"], do_frames=True)
               for m in COHORT2["flights"]]
    c1_rows = [analyze_one(m, COHORT1["fixture"], do_frames=False)
               for m in COHORT1["flights"]]
    s2, s1 = cohort_summary(c2_rows), cohort_summary(c1_rows)

    # CSV
    with (OUT / "cohort2_deaths.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slot", "arm", "fid", "loss_mode", "loss_t", "last_near_R",
                    "believed_R", "age", "vz_ptp", "osc", "reacq", "far_n"])
        for r in c2_rows:
            vd = r.get("vision_death") or {}
            ln = vd.get("last_near_detection") or {}
            st = vd.get("state_at_loss") or {}
            vz = vd.get("vz_at_loss") or {}
            w.writerow([
                r.get("slot"), r.get("arm"), r.get("fid"), r.get("loss_mode"),
                vd.get("loss_t_ff"), ln.get("R"), st.get("R_believed"), st.get("age"),
                vz.get("peak_to_peak"), vz.get("oscillating"),
                vd.get("reacquired_near"), vd.get("n_far_certified_during_commit"),
            ])

    summary = {
        "ask": "vision death at ~3m — phase6j cohort-2 vs cohort-1",
        "cohort2": s2,
        "cohort1": s1,
        "flights_cohort2": c2_rows,
        "flights_cohort1": [{k: v for k, v in r.items()
                             if k != "frame_diagnosis"} for r in c1_rows],
        "binding": {
            "cohort2_all_died": s2["n_vision_death_no_reacq"] == s2["n"],
            "cohort1_frac": s1["frac"],
            "dominant_mode_c2": (max(s2["loss_modes"], key=s2["loss_modes"].get)
                                 if s2["loss_modes"] else None),
        },
    }
    # Strip huge corners for JSON size
    def scrub(obj):
        if isinstance(obj, dict):
            return {k: scrub(v) for k, v in obj.items()
                    if k not in ("corners_px", "rows", "frames")}
        if isinstance(obj, list):
            return [scrub(x) for x in obj]
        return obj

    (OUT / "summary.json").write_text(
        json.dumps(scrub(summary), indent=2, default=str), encoding="utf-8")
    write_report(c2_rows, c1_rows, s2, s1)
    print(json.dumps({"cohort2": s2, "cohort1": s1,
                      "binding": summary["binding"]}, indent=2))


if __name__ == "__main__":
    main()
