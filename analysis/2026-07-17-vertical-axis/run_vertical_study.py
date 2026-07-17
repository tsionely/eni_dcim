"""Phase 5b P0: vertical believed-vs-true + old/new detector on full recordings.

Convention (camera / STATE gate_rel.t):
  t_y > 0  => gate BELOW optical center => aircraft HIGH vs opening
  t_y < 0  => gate ABOVE optical center => aircraft LOW vs opening
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import types
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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402

# Flights with full local vision for this study
FLIGHTS = [
    "20260716T203450-2ca531c3",  # F1 — HIGH overfly, state said LOW
    "20260716T212408-2ca531c3",  # F2 phase5
    "20260716T164931-2ca531c3",  # phase4c
    "20260716T165306-2ca531c3",
    "20260716T165535-2ca531c3",
    "20260716T131137-2ca531c3",  # milestone PASS
]


@dataclass
class LastFixVert:
    flight_id: str
    t_last_fix_s: float
    range_m: float
    true_ty_m: float          # PnP cam y (+ HIGH)
    believed_ty_m: float      # STATE cam y at same time
    delta_believed_minus_true_m: float
    img_ty_m: float | None    # from center_px using Z=range
    center_v_px: float | None
    age_s: float
    # After last fix — believed at closest STATE
    t_closest_s: float | None
    believed_at_closest_ty: float | None
    closest_dist_m: float | None
    runaway_believed_minus_true_m: float | None  # closest believed - frozen true
    # Attribution hints
    mean_vz_cmd_after: float | None
    frac_blind_climb_active: float | None
    mean_state_ty_after: float | None
    note: str


def load_old_detector(params: ParamSet):
    """Load pre-bloom detector from sibling module without polluting package."""
    path = OUT / "gate_detector_hsv_old.py"
    # The old file imports from aigp.* — ensure package path works.
    # Rename class load via exec in a unique module name.
    spec = importlib.util.spec_from_file_location("gate_detector_hsv_old", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Old module name was gate_detector_hsv — it may use relative-unaware imports
    sys.modules["gate_detector_hsv_old"] = mod
    spec.loader.exec_module(mod)
    return mod.HsvGateDetector(params)


def fy_px(width: int, fov_deg: float = 90.0) -> float:
    return (width / 2.0) / math.tan(math.radians(fov_deg) / 2.0)


def img_ty_from_center(cy: float, height: int, width: int, range_m: float, fov_deg: float = 90.0) -> float:
    """Approximate cam-frame t_y from image v and range Z≈range."""
    fy = fy_px(width, fov_deg)
    cy0 = height / 2.0
    # y_cam / Z = (cy - cy0) / fy  => y = Z * (cy-cy0)/fy
    return float(range_m * (cy - cy0) / fy)


def load_log_series(log_path: Path):
    t0 = None
    states = []  # (t, ty, tz, dist, age, vz_world)
    dets = []    # (t, ty, tz, dist, cx, cy)
    setpoints = []  # (t, phase, vz_body)
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            topic = rec["topic"]
            d = rec["data"]
            if topic == "state":
                gr = d.get("gate_rel")
                if gr and gr.get("t") is not None:
                    tx, ty, tz = (float(x) for x in gr["t"])
                    dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                    age = float(d.get("gate_rel_age_s") or 0.0)
                    vw = d.get("v_world") or [0, 0, 0]
                    states.append((t, ty, tz, dist, age, float(vw[2])))
            elif topic == "detection" and d.get("rel_pose"):
                tx, ty, tz = (float(x) for x in d["rel_pose"]["t"])
                dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                c = d.get("center_px") or [None, None]
                dets.append((t, ty, tz, dist, c[0], c[1]))
            elif topic == "setpoint":
                vb = d.get("v_body") or [0, 0, 0]
                setpoints.append((t, d.get("phase"), float(vb[2])))
    return t0, states, dets, setpoints


def nearest_state(states, t, max_dt=0.05):
    best = None
    for s in states:
        dt = abs(s[0] - t)
        if best is None or dt < best[0]:
            best = (dt, s)
    if best is None or best[0] > max_dt:
        return None
    return best[1]


def analyze_flight_vertical(flight_id: str) -> LastFixVert | None:
    log = LOGS / flight_id / "flight.jsonl"
    if not log.exists():
        # fixture fallback
        cands = list((ROOT / "fixtures").glob(f"**/{flight_id}-flight.jsonl"))
        if not cands:
            return None
        log = cands[0]
    t0, states, dets, setpoints = load_log_series(log)
    if not dets:
        return LastFixVert(
            flight_id=flight_id,
            t_last_fix_s=float("nan"),
            range_m=float("nan"),
            true_ty_m=float("nan"),
            believed_ty_m=float("nan"),
            delta_believed_minus_true_m=float("nan"),
            img_ty_m=None,
            center_v_px=None,
            age_s=float("nan"),
            t_closest_s=None,
            believed_at_closest_ty=None,
            closest_dist_m=None,
            runaway_believed_minus_true_m=None,
            mean_vz_cmd_after=None,
            frac_blind_climb_active=None,
            mean_state_ty_after=None,
            note="no detections in log",
        )

    # Last CLOSE fix on the first approach — not a post-retreat far re-lock.
    # Prefer min-range detection under 5m; else last det under 8m before any
    # gap where range jumps back above 12m.
    close = [d for d in dets if d[3] < 5.0]
    if close:
        # last close fix (time-ordered); also keep the closest-range one if later far locks exist
        last_close = close[-1]
        closest_det = min(close, key=lambda d: d[3])
        # Use the later of {closest_det, last_close} only if still <5m — prefer last_close
        last = last_close
        # If a much closer fix exists within 1s, prefer that (banner/overfly moment)
        if closest_det[3] < last_close[3] - 0.3 and abs(closest_det[0] - last_close[0]) < 2.0:
            last = closest_det
    else:
        mid = [d for d in dets if d[3] < 8.0]
        last = mid[-1] if mid else dets[-1]
    t_lf, ty_true, tz, rng, cx, cy = last
    st = nearest_state(states, t_lf, max_dt=0.1)
    if st is None:
        believed = float("nan")
        age = float("nan")
    else:
        believed = st[1]
        age = st[4]

    img_ty = None
    if cy is not None and rng > 0.1:
        # assume 640x360 if unknown — refine from vision later
        img_ty = img_ty_from_center(float(cy), 360, 640, rng)

    # Closest STATE after last fix (or overall closest after t_lf - 0.5)
    after = [s for s in states if s[0] >= t_lf - 0.05]
    closest = min(after, key=lambda s: s[3]) if after else None
    runaway = None
    if closest is not None and math.isfinite(ty_true):
        runaway = closest[1] - ty_true

    # Setpoint vz after last fix during commit/approach
    sps = [s for s in setpoints if s[0] >= t_lf and s[0] <= t_lf + 5.0]
    vz_cmds = [s[2] for s in sps if s[1] in ("approach", "commit", "retreat")]
    mean_vz = float(np.mean(vz_cmds)) if vz_cmds else None

    # Blind climb active proxy: age>0.4 during commit after last fix
    commit_windows = [(s[0], s[1]) for s in setpoints if s[1] == "commit"]
    blind_flags = []
    for s in after:
        if s[0] > t_lf + 4.0:
            break
        in_commit = any(abs(s[0] - ct) < 0.05 for ct, _ in commit_windows) or any(
            sp[1] == "commit" and abs(sp[0] - s[0]) < 0.08 for sp in setpoints
        )
        # simpler: any setpoint within 0.1s is commit
        phase = None
        best_dt = 1e9
        for sp in setpoints:
            dt = abs(sp[0] - s[0])
            if dt < best_dt:
                best_dt = dt
                phase = sp[1]
        if phase == "commit" and s[4] > 0.4:
            blind_flags.append(1)
        elif phase == "commit":
            blind_flags.append(0)
    frac_blind = float(np.mean(blind_flags)) if blind_flags else None
    mean_ty_after = float(np.mean([s[1] for s in after[:50]])) if after else None

    note = ""
    if ty_true > 0.2 and believed < -0.05:
        note = "TRUE_HIGH believed_LOW (sign conflict at last fix)"
    elif ty_true < -0.2 and believed > 0.05:
        note = "TRUE_LOW believed_HIGH (sign conflict at last fix)"
    elif runaway is not None and (ty_true > 0) and (closest[1] < 0):
        note = "at last fix ok-ish; BELIEVED flipped LOW while coasting (runaway)"
    elif runaway is not None and abs(runaway) > 0.5:
        note = f"runaway |Δ|={abs(runaway):.2f}m after last fix"

    return LastFixVert(
        flight_id=flight_id,
        t_last_fix_s=t_lf,
        range_m=rng,
        true_ty_m=ty_true,
        believed_ty_m=believed,
        delta_believed_minus_true_m=believed - ty_true if math.isfinite(believed) else float("nan"),
        img_ty_m=img_ty,
        center_v_px=float(cy) if cy is not None else None,
        age_s=age if math.isfinite(age) else float("nan"),
        t_closest_s=closest[0] if closest else None,
        believed_at_closest_ty=closest[1] if closest else None,
        closest_dist_m=closest[3] if closest else None,
        runaway_believed_minus_true_m=runaway,
        mean_vz_cmd_after=mean_vz,
        frac_blind_climb_active=frac_blind,
        mean_state_ty_after=mean_ty_after,
        note=note,
    )


def plot_f1_timeline():
    fid = "20260716T203450-2ca531c3"
    log = LOGS / fid / "flight.jsonl"
    if not log.exists():
        return
    _t0, states, dets, setpoints = load_log_series(log)
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    if dets:
        axes[0].plot([d[0] for d in dets], [d[1] for d in dets], "g.", ms=3, label="det ty (true)")
    if states:
        axes[0].plot([s[0] for s in states], [s[1] for s in states], "b-", lw=0.8, label="STATE ty (believed)")
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].set_ylabel("ty (m) +HIGH")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title(f"{fid} vertical believed vs measured")

    if dets:
        axes[1].plot([d[0] for d in dets], [d[3] for d in dets], "g.", ms=3, label="det range")
    if states:
        axes[1].plot([s[0] for s in states], [s[3] for s in states], "b-", lw=0.7, label="STATE range")
    axes[1].set_ylabel("range (m)")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    if states:
        axes[2].plot([s[0] for s in states], [s[4] for s in states], "m-", lw=0.8)
    axes[2].axhline(0.4, color="orange", ls="--", label="blind_climb age thresh")
    axes[2].set_ylabel("gate_rel_age (s)")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    if setpoints:
        axes[3].plot([s[0] for s in setpoints], [s[2] for s in setpoints], "k-", lw=0.7, label="vz_cmd (NED +down)")
    axes[3].axhline(0, color="gray", lw=0.5)
    axes[3].set_ylabel("vz_cmd")
    axes[3].set_xlabel("t (s)")
    axes[3].legend(fontsize=8)
    axes[3].grid(True, alpha=0.3)
    # phase bands
    for t, ph, _ in setpoints:
        if ph == "commit":
            axes[0].axvline(t, color="red", alpha=0.05, lw=0.4)
    fig.tight_layout()
    (OUT / "plots").mkdir(exist_ok=True)
    fig.savefig(OUT / "plots" / "f1_vertical_timeline.png", dpi=140)
    plt.close(fig)


def extract_banner_frames(flight_id: str, n: int = 6):
    """Save frames near last fix / close range from full vision."""
    vision = LOGS / flight_id / "vision.aigprec"
    log = LOGS / flight_id / "flight.jsonl"
    if not vision.exists() or not log.exists():
        return []
    t0, states, dets, _ = load_log_series(log)
    if not dets:
        return []
    last = [d for d in dets if d[3] < 10][-1]
    t_target = last[0]
    # Also a bit after for banner view
    targets = [t_target - 0.3, t_target, t_target + 0.4, t_target + 0.8]
    assembler = ChunkAssembler()
    best = {tt: None for tt in targets}
    out_dir = OUT / "frames"
    out_dir.mkdir(exist_ok=True)
    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    det_new = HsvGateDetector(params)
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        fid, sim_ns, jpeg = done
        t = (mono_ns - t0) / 1e9
        for tt in targets:
            err = abs(t - tt)
            if best[tt] is None or err < best[tt][0]:
                best[tt] = (err, t, fid, sim_ns, jpeg)
        if t > max(targets) + 2.0:
            break
    saved = []
    for tt, pack in best.items():
        if pack is None or pack[0] > 0.5:
            continue
        err, t, fid, sim_ns, jpeg = pack
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        d = det_new.detect(CameraFrame(frame_id=fid, ts_ns=sim_ns, image=img))
        vis = img.copy()
        h, w = vis.shape[:2]
        cv2.drawMarker(vis, (w // 2, h // 2), (200, 200, 200), cv2.MARKER_CROSS, 20, 1)
        ty = None
        rng = None
        if d is not None and d.rel_pose is not None:
            pts = np.asarray(d.corners_px, dtype=np.int32).reshape(-1, 2)
            cv2.polylines(vis, [pts], True, (0, 255, 255), 2)
            cv2.circle(vis, (int(d.center_px[0]), int(d.center_px[1])), 5, (0, 0, 255), -1)
            ty = float(d.rel_pose.t[1])
            rng = float(np.linalg.norm(d.rel_pose.t))
        st = nearest_state(states, t, 0.1)
        bel = st[1] if st else None
        cv2.putText(
            vis,
            f"{flight_id[-8:]} t={t:.2f} ty_pnp={ty} bel={bel} r={rng}",
            (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
        )
        if w > 900:
            vis = cv2.resize(vis, (900, int(h * 900 / w)))
        fname = f"{flight_id[-8:]}_t{t:.2f}_vert.jpg"
        cv2.imwrite(str(out_dir / fname), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        saved.append(fname)
    return saved


def detector_bin_stats(detector, vision: Path, log: Path, max_frames: int | None = 12000):
    """Fix rate by OWN detection range bins (not preceding) on unique frames."""
    t0_log, _states, _dets, _ = load_log_series(log)
    assembler = ChunkAssembler()
    bins = {
        "5-8m": [0, 0],
        "3-5m": [0, 0],
        "2-3m": [0, 0],
        "<2m": [0, 0],
        "other": [0, 0],
    }
    # preceding-bin style as phase5 study
    prec = {k: [0, 0] for k in bins}
    reasons = {k: {} for k in bins}
    preceding = None
    n = 0
    seen_jpeg = set()
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        fid, sim_ns, jpeg = done
        # light dedupe
        key = hash(jpeg[:64]) ^ len(jpeg)
        if key in seen_jpeg:
            continue
        seen_jpeg.add(key)
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        n += 1
        if max_frames and n > max_frames:
            break
        det = detector.detect(CameraFrame(frame_id=fid, ts_ns=sim_ns, image=img))
        hit = det is not None and det.rel_pose is not None
        rng = float(np.linalg.norm(det.rel_pose.t)) if hit else None

        # preceding bin
        def bin_of(r):
            if r is None:
                return None
            if 5 <= r < 8:
                return "5-8m"
            if 3 <= r < 5:
                return "3-5m"
            if 2 <= r < 3:
                return "2-3m"
            if r < 2:
                return "<2m"
            return "other"

        pb = bin_of(preceding) or "other"
        prec[pb][0] += 1
        if hit:
            prec[pb][1] += 1
            preceding = rng
            ob = bin_of(rng) or "other"
            bins[ob][0] += 1
            bins[ob][1] += 1
        else:
            # classify miss lightly
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lo = cv2.inRange(hsv, (0, 60, 50), (12, 255, 255))
            hi = cv2.inRange(hsv, (168, 60, 50), (180, 255, 255))
            red = cv2.bitwise_or(lo, hi)
            red_frac = float(cv2.countNonZero(red)) / (img.shape[0] * img.shape[1])
            reason = "no_red" if red_frac < 0.0015 else "other_miss"
            reasons[pb][reason] = reasons[pb].get(reason, 0) + 1

    def fmt(d):
        out = {}
        for k, (tot, hits) in d.items():
            out[k] = {
                "frames": tot,
                "fixes": hits,
                "fix_rate": (100.0 * hits / tot) if tot else None,
            }
        return out

    return {"n_unique_frames": n, "by_own_range": fmt(bins), "by_preceding": fmt(prec), "miss_reasons_prec": reasons}


def run_detector_comparison(flight_ids: list[str]):
    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    new_det = HsvGateDetector(params)
    old_det = load_old_detector(params)
    results = {}
    for fid in flight_ids:
        vision = LOGS / fid / "vision.aigprec"
        log = LOGS / fid / "flight.jsonl"
        if not vision.exists() or not log.exists():
            continue
        print(f"detector compare {fid} ...", flush=True)
        # Cap frames for huge files — sample by stopping at 15k unique
        old_stats = detector_bin_stats(old_det, vision, log, max_frames=15000)
        new_stats = detector_bin_stats(new_det, vision, log, max_frames=15000)
        results[fid] = {"old": old_stats, "new": new_stats}
        print(
            f"  old 3-5 rate={old_stats['by_preceding'].get('3-5m', {}).get('fix_rate')} "
            f"new={new_stats['by_preceding'].get('3-5m', {}).get('fix_rate')}",
            flush=True,
        )
    return results


def write_report(verts: list[LastFixVert], det_cmp: dict, banner_frames: list[str]):
    lines = [
        "# Phase 5b — VERTICAL axis P0 + detector old-vs-new",
        "",
        "HEAD ≥ `e9c1d97`. Convention: **ty > 0 ⇒ aircraft HIGH** (gate below center).",
        "",
        "## 1. Vertical believed − true at last approach fix (one number per flight)",
        "",
        "| flight | t_last | range | true ty | believed ty | **Δ (bel−true)** | runaway@closest | note |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for v in verts:
        if v is None or not math.isfinite(v.true_ty_m):
            continue
        run = (
            f"{v.runaway_believed_minus_true_m:+.3f}"
            if v.runaway_believed_minus_true_m is not None
            else "—"
        )
        lines.append(
            f"| `{v.flight_id}` | {v.t_last_fix_s:.2f} | {v.range_m:.2f} | "
            f"{v.true_ty_m:+.3f} | {v.believed_ty_m:+.3f} | "
            f"**{v.delta_believed_minus_true_m:+.3f}** | {run} | {v.note} |"
        )

    f1 = next((v for v in verts if v and "203450" in v.flight_id), None)
    lines += [
        "",
        "### F1 deep dive (`20260716T203450`)",
        "",
        "![timeline](plots/f1_vertical_timeline.png)",
        "",
    ]
    if f1:
        lines += [
            f"- Last fix: t={f1.t_last_fix_s:.2f}s range={f1.range_m:.2f}m "
            f"true_ty={f1.true_ty_m:+.3f} believed={f1.believed_ty_m:+.3f} "
            f"**Δ={f1.delta_believed_minus_true_m:+.3f} m**",
            f"- Closest STATE after: t={f1.t_closest_s} dist={f1.closest_dist_m} "
            f"believed_ty={f1.believed_at_closest_ty} "
            f"runaway(bel−true_frozen)={f1.runaway_believed_minus_true_m}",
            f"- Mean vz_cmd after last fix (NED +down): {f1.mean_vz_cmd_after}",
            f"- Fraction of commit samples with age>0.4 (blind_climb armed): {f1.frac_blind_climb_active}",
            "",
        ]
    lines += [
        "Banner / last-fix frames: " + ", ".join(f"`frames/{x}`" for x in banner_frames),
        "",
        "## 2. Where does the vertical error come from?",
        "",
        "Mechanisms in the planner (`race_planner` commit path):",
        "",
        "1. **altitude_hold_velocity** — holds `world_dz ≈ aim_up` using STATE `gate_rel`. "
        "If STATE ty is wrong-sign LOW (ty<0) while the aircraft is actually HIGH, "
        "`world_dz` looks like 'gate above me' → command is **climb** (vz_cmd < 0 in NED) "
        "→ drives further HIGH.",
        "2. **blind_climb_bias** (`extra[2] -= 0.2` when `gate_rel_age_s > 0.4`) — "
        "intentional climb during vision dropout. Correct for true sink; "
        "**double-compensates** if the aircraft is already HIGH / state already wrong-LOW.",
        "3. **vision-velocity vz** — blends into `v_world`; a phantom descent in the "
        "estimator can bias the outer loop, but altitude-hold was added specifically "
        "to stop integrating vz. Primary suspect for HIGH-overfly with LOW state is "
        "(1)+(2) acting on a stale inverted vertical state, not raw vz alone.",
        "",
    ]
    # Attribution verdict from F1 numbers
    if f1 and f1.mean_vz_cmd_after is not None:
        if f1.mean_vz_cmd_after < -0.05:
            lines.append(
                f"**F1 attribution:** mean vz_cmd after last fix is **{f1.mean_vz_cmd_after:+.3f}** "
                "(NED: negative = climb). That matches altitude-hold and/or blind_climb "
                "commanding UP while the aircraft was already HIGH — "
                "**blind_climb + altitude-hold on a LOW-believed state** is the smoking gun."
            )
        else:
            lines.append(
                f"**F1 attribution:** mean vz_cmd after last fix is {f1.mean_vz_cmd_after:+.3f}; "
                "see timeline plot for phase-resolved behavior."
            )
    lines += [
        "",
        "## 3. Detector old (9fe3702) vs new (HEAD bloom-proof) on full recordings",
        "",
        "Preceding-range bins (same semantics as Phase 5 study). Rates are % of frames "
        "in that preceding bin that produce a PnP fix.",
        "",
    ]
    # aggregate table
    for fid, cmp_ in det_cmp.items():
        lines.append(f"### `{fid}`")
        lines.append("")
        lines.append("| bin | old frames | old fix% | new frames | new fix% | Δ pp |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for b in ("5-8m", "3-5m", "2-3m", "<2m"):
            o = cmp_["old"]["by_preceding"].get(b, {})
            n = cmp_["new"]["by_preceding"].get(b, {})
            orate = o.get("fix_rate")
            nrate = n.get("fix_rate")
            dpp = (nrate - orate) if (orate is not None and nrate is not None) else None
            lines.append(
                f"| {b} | {o.get('frames', 0)} | "
                f"{orate if orate is not None else '—'} | "
                f"{n.get('frames', 0)} | "
                f"{nrate if nrate is not None else '—'} | "
                f"{dpp if dpp is not None else '—'} |"
            )
        lines.append("")
        # remaining misses
        lines.append("Remaining miss reasons (new, preceding bins):")
        for b, rs in cmp_["new"].get("miss_reasons_prec", {}).items():
            if rs:
                lines.append(f"- {b}: {rs}")
        lines.append("")

    lines += [
        "### What remains after bloom-proof",
        "",
        "Expect `partial_ring` / bloom-`no_red` to convert to fixes. Residual misses "
        "sizing the next perception task should be dominated by **true edge_clip** "
        "(gate leaving FOV) and **exposure_dark**, not washed pink.",
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`, `vertical_last_fix.csv`",
        "- `plots/f1_vertical_timeline.png`, `frames/`",
        "- `gate_detector_hsv_old.py` (9fe3702) for A/B",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    print("=== vertical per flight ===", flush=True)
    verts = []
    for fid in FLIGHTS:
        print(f"  {fid}", flush=True)
        verts.append(analyze_flight_vertical(fid))

    import csv

    with (OUT / "vertical_last_fix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "flight_id",
                "t_last_fix_s",
                "range_m",
                "true_ty_m",
                "believed_ty_m",
                "delta_believed_minus_true_m",
                "runaway_believed_minus_true_m",
                "believed_at_closest_ty",
                "closest_dist_m",
                "mean_vz_cmd_after",
                "frac_blind_climb_active",
                "note",
            ]
        )
        for v in verts:
            if v is None:
                continue
            w.writerow(
                [
                    v.flight_id,
                    v.t_last_fix_s,
                    v.range_m,
                    v.true_ty_m,
                    v.believed_ty_m,
                    v.delta_believed_minus_true_m,
                    v.runaway_believed_minus_true_m,
                    v.believed_at_closest_ty,
                    v.closest_dist_m,
                    v.mean_vz_cmd_after,
                    v.frac_blind_climb_active,
                    v.note,
                ]
            )

    print("=== F1 plot + frames ===", flush=True)
    plot_f1_timeline()
    banners = extract_banner_frames("20260716T203450-2ca531c3")
    banners += extract_banner_frames("20260716T212408-2ca531c3")

    print("=== detector old vs new (full recordings) ===", flush=True)
    # Focus on phase5 full recordings + milestone (manageable sizes)
    det_flights = [
        "20260716T203450-2ca531c3",
        "20260716T212408-2ca531c3",
        "20260716T131137-2ca531c3",
    ]
    det_cmp = run_detector_comparison(det_flights)

    write_report([v for v in verts if v], det_cmp, banners)

    summary = {
        "vertical": [asdict(v) for v in verts if v],
        "detector_comparison": det_cmp,
        "banner_frames": banners,
        "headline_number": {
            v.flight_id: v.delta_believed_minus_true_m for v in verts if v and math.isfinite(v.delta_believed_minus_true_m)
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
