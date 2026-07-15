"""Pin the LATERAL frame offset on phase3d (+ phase3c compare).

AGENTS.md DATA ANALYST CURRENT TASK:
1. Camera mount YAW/ROLL from rest-phase frames (docs/08 pitch method twin).
2. Correlate vy_est error vs commanded yaw activity (mount vs frozen-z coupling).
3. Vertical crossing error phase3c vs phase3d; recommend mount_pitch 24/29/34.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

FIX3D = ROOT / "fixtures" / "20260715T135600-phase3d-r2training"
FIX3C = ROOT / "fixtures" / "20260715T052244-phase3c-r2training"

# Pitch calibration precedent (AGENTS / phase3d commit message):
# optical +11 deg above horizon, IMU pitch -17.8 deg => mount_pitch ≈ 29.
PITCH_CAL_OPTICAL_HORIZON_DEG = 11.0
PITCH_CAL_IMU_DEG = -17.8
PITCH_CAL_MOUNT_DEG = 29.0

FOV_DEG = 90.0  # params_default perception.camera.fov_deg
FX_640 = (640 / 2.0) / math.tan(math.radians(FOV_DEG) / 2.0)  # ~320


@dataclass
class FlightSeries:
    label: str
    path: Path
    phase: str  # phase3c | phase3d
    mount_pitch_param: float
    t0: int = 0
    imu: list = field(default_factory=list)  # (t, gyro, accel)
    dets: list = field(default_factory=list)  # (t, u, v, tx, ty, tz, corners)
    states: list = field(default_factory=list)  # (t, v_world, q, center, gate_rel_t)
    setpoints: list = field(default_factory=list)  # (t, phase, v_body, yaw_rate)
    hover_end_s: float | None = None


def load_flight(label: str, path: Path, phase: str, mount_pitch: float) -> FlightSeries:
    fs = FlightSeries(label=label, path=path, phase=phase, mount_pitch_param=mount_pitch)
    t0 = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
                fs.t0 = t0
            t = (mono - t0) / 1e9
            d = rec["data"]
            topic = rec["topic"]
            if topic == "imu":
                fs.imu.append(
                    (
                        t,
                        np.asarray(d["gyro"], dtype=np.float64),
                        np.asarray(d["accel"], dtype=np.float64),
                    )
                )
            elif topic == "detection" and d.get("rel_pose") is not None:
                c = d["center_px"]
                rp = d["rel_pose"]["t"]
                corners = d.get("corners_px")
                fs.dets.append(
                    (
                        t,
                        float(c[0]),
                        float(c[1]),
                        float(rp[0]),
                        float(rp[1]),
                        float(rp[2]),
                        np.asarray(corners, dtype=np.float64) if corners else None,
                    )
                )
            elif topic == "state":
                vw = np.asarray(d["v_world"], dtype=np.float64)
                q = np.asarray(d["q_att"], dtype=np.float64)
                gr = d.get("gate_rel")
                gt = None if gr is None else np.asarray(gr["t"], dtype=np.float64)
                fs.states.append((t, vw, q, d.get("gate_center_px"), gt))
            elif topic == "setpoint":
                fs.setpoints.append(
                    (
                        t,
                        d.get("phase", "?"),
                        np.asarray(d.get("v_body", [0, 0, 0]), dtype=np.float64),
                        float(d.get("yaw_rate", 0.0)),
                    )
                )
    for t, ph, *_ in fs.setpoints:
        if ph == "takeoff":
            fs.hover_end_s = t
            break
    if fs.hover_end_s is None:
        fs.hover_end_s = 15.0  # fallback
    return fs


def imu_gravity_rpy_deg(accel_mean: np.ndarray) -> tuple[float, float]:
    """Return (roll_deg, pitch_deg) from specific-force at rest.

    Body z-down: level => accel ≈ [0,0,-g]. Nose-down => ax < 0.
    Aircraft-style signed pitch: negative = nose down (matches AGENTS -17.8).
    """
    ax, ay, az = accel_mean
    roll = math.degrees(math.atan2(ay, -az if az < 0 else az))
    # Prefer classic: pitch = asin(-ax/|a|) with nose-down negative when ax<0...
    # AGENTS reports IMU x -17.8 with ax≈-3: use pitch = atan2(ax, -az) so ax<0 => neg.
    pitch = math.degrees(math.atan2(ax, -az))
    return roll, pitch


def optical_gate_bearing_deg(tx: float, ty: float, tz: float) -> tuple[float, float]:
    """Camera-frame bearing to gate: yaw (right +), pitch (up +)."""
    yaw = math.degrees(math.atan2(tx, tz))
    pitch = math.degrees(math.atan2(-ty, tz))  # cam y down => up-positive
    return yaw, pitch


def quad_roll_deg(corners: np.ndarray) -> float | None:
    """Frame-edge roll from gate top edge (tl->tr), degrees; CCW positive."""
    if corners is None or len(corners) < 2:
        return None
    tl, tr = corners[0], corners[1]
    dy = float(tr[1] - tl[1])
    dx = float(tr[0] - tl[0])
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    # Image y down: positive angle = top edge tilts down-to-right = roll?
    return math.degrees(math.atan2(dy, dx))


def rest_mount_offsets(fs: FlightSeries) -> dict:
    """Estimate mount yaw/roll/pitch from hover rest phase."""
    he = fs.hover_end_s or 15.0
    # Use mid-hover to avoid countdown jitter (skip first 2s, last 0.5s)
    t0, t1 = 2.0, max(2.5, he - 0.5)
    dets = [d for d in fs.dets if t0 <= d[0] <= t1]
    imus = [a for t, g, a in fs.imu if t0 <= t <= t1]
    out = {
        "label": fs.label,
        "phase": fs.phase,
        "mount_pitch_param": fs.mount_pitch_param,
        "hover_window_s": [t0, t1],
        "n_dets": len(dets),
        "n_imu": len(imus),
    }
    if len(imus) < 20:
        out["status"] = "insufficient_imu"
        return out
    a_mean = np.mean(imus, axis=0)
    roll_imu, pitch_imu = imu_gravity_rpy_deg(a_mean)
    out["imu_accel_mean"] = a_mean.tolist()
    out["imu_roll_deg"] = roll_imu
    out["imu_pitch_deg"] = pitch_imu  # aircraft signed (nose-down negative)

    if len(dets) < 20:
        out["status"] = "insufficient_dets"
        return out

    t_mean = np.mean([[d[3], d[4], d[5]] for d in dets], axis=0)
    c_mean = np.mean([[d[1], d[2]] for d in dets], axis=0)
    c_std = np.std([[d[1], d[2]] for d in dets], axis=0)
    yaw_opt, pitch_opt = optical_gate_bearing_deg(*t_mean)
    out["gate_t_cam_mean_m"] = t_mean.tolist()
    out["gate_center_px_mean"] = c_mean.tolist()
    out["gate_center_px_std"] = c_std.tolist()
    out["optical_yaw_to_gate_deg"] = yaw_opt
    out["optical_pitch_to_gate_deg"] = pitch_opt

    # Pixel-based optical angles from image center (independent of PnP mount rot)
    u_n = (c_mean[0] - 320.0) / FX_640
    v_n = (c_mean[1] - 180.0) / FX_640
    out["pixel_yaw_deg"] = math.degrees(math.atan(u_n))
    out["pixel_pitch_deg"] = math.degrees(math.atan(-v_n))  # up positive

    rolls = [quad_roll_deg(d[6]) for d in dets if d[6] is not None]
    rolls = [r for r in rolls if r is not None]
    if rolls:
        out["frame_edge_roll_deg_mean"] = float(np.mean(rolls))
        out["frame_edge_roll_deg_std"] = float(np.std(rolls))
    else:
        out["frame_edge_roll_deg_mean"] = None
        out["frame_edge_roll_deg_std"] = None

    # Mount pitch (docs/08 method twin): optical_horizon - imu_pitch.
    # We don't have a robust horizon detector; use the CALIBRATED precedent
    # check: reconstruct optical_horizon ≈ mount_param + imu_pitch when
    # mount_param is applied in PnP, OR for pre-mount (phase3c) estimate
    # residual from gate elevation assuming known geometry.
    #
    # Practical rest estimate used for LATERAL axes:
    #   mount_yaw ≈ optical yaw to gate (pad faces gate ⇒ expected body yaw≈0)
    #   mount_roll ≈ frame_edge_roll - imu_roll_residual
    # IMU roll near ±180 from atan2 quirks when nearly level — use small-angle
    # from ay/|a|: roll ≈ atan2(ay, g).
    roll_small = math.degrees(math.atan2(a_mean[1], max(1e-6, abs(a_mean[2]))))
    out["imu_roll_small_deg"] = roll_small

    # Expected: parked facing gate ⇒ body yaw to gate ≈ 0 ⇒ mount_yaw = optical_yaw
    out["mount_yaw_est_deg"] = yaw_opt
    out["mount_yaw_est_unc_deg"] = float(
        abs(math.degrees(math.atan(c_std[0] / FX_640))) + 0.3
    )

    if rolls:
        # Frame-edge roll should be 0 if cam roll-aligned to horizon/gate.
        # IMU small roll is gravity roll of body. Mount roll ≈ edge - body.
        out["mount_roll_est_deg"] = float(np.mean(rolls)) - roll_small
        out["mount_roll_est_unc_deg"] = float(np.std(rolls)) + 0.5
    else:
        out["mount_roll_est_deg"] = None
        out["mount_roll_est_unc_deg"] = None

    # Pitch cross-check vs known calibration (not the lateral unknown)
    # optical_pitch_to_gate includes gate height above pad — NOT horizon.
    # Residual vs IMU for reporting only.
    out["pitch_gate_minus_imu_deg"] = pitch_opt - pitch_imu
    out["pitch_cal_precedent_deg"] = PITCH_CAL_MOUNT_DEG
    out["status"] = "ok"
    return out


def phase_mask(fs: FlightSeries, phases: set[str]) -> list[tuple[float, float]]:
    """Return list of (t0,t1) intervals for given setpoint phases."""
    intervals = []
    cur = None
    for t, ph, *_ in fs.setpoints:
        if ph in phases:
            if cur is None:
                cur = t
        else:
            if cur is not None:
                intervals.append((cur, t))
                cur = None
    if cur is not None and fs.setpoints:
        intervals.append((cur, fs.setpoints[-1][0]))
    return intervals


def in_intervals(t: float, intervals: list[tuple[float, float]]) -> bool:
    return any(a <= t <= b for a, b in intervals)


def vy_yaw_correlation(fs: FlightSeries) -> dict:
    """Test static mount vs yaw-coupling for lateral phantom."""
    approach = phase_mask(fs, {"approach", "commit"})
    if not approach:
        return {"label": fs.label, "status": "no_approach"}

    # Build synced series on state timeline
    rows = []
    sp_idx = 0
    for t, vw, q, center, gt in fs.states:
        if not in_intervals(t, approach):
            continue
        # nearest setpoint
        while sp_idx + 1 < len(fs.setpoints) and fs.setpoints[sp_idx + 1][0] <= t:
            sp_idx += 1
        _, ph, vb, yaw_rate = fs.setpoints[sp_idx]
        # nearest detection for gate lateral bearing
        # Proxy TRUE lateral velocity from gate: if flying at gate, desired vy≈0
        # in gate-aligned frame; vy_est is the phantom when |u| is small/stable.
        speed = float(np.linalg.norm(vw))
        vx, vy, vz = float(vw[0]), float(vw[1]), float(vw[2])
        rows.append((t, vy, vx, vz, speed, yaw_rate, abs(yaw_rate), ph))

    if len(rows) < 30:
        return {"label": fs.label, "status": "insufficient_samples", "n": len(rows)}

    arr = np.asarray(rows, dtype=object)
    t = np.array([r[0] for r in rows], float)
    vy = np.array([r[1] for r in rows], float)
    vx = np.array([r[2] for r in rows], float)
    speed = np.array([r[4] for r in rows], float)
    yaw_rate = np.array([r[5] for r in rows], float)
    abs_yaw = np.array([r[6] for r in rows], float)

    # Integrate |yaw_rate| from approach start
    yaw_int = np.zeros_like(t)
    for i in range(1, len(t)):
        yaw_int[i] = yaw_int[i - 1] + abs_yaw[i] * max(t[i] - t[i - 1], 0.0)

    def corr(a, b):
        if a.std() < 1e-9 or b.std() < 1e-9:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])

    def slope(x, y):
        if x.std() < 1e-9:
            return float("nan")
        return float(np.polyfit(x, y, 1)[0])

    # Error signature: vy_est itself (true lateral≈0 when lined up on approach).
    # Also vy vs forward speed (mount yaw would give vy ≈ -V * sin(mount_yaw))
    out = {
        "label": fs.label,
        "phase": fs.phase,
        "status": "ok",
        "n": len(rows),
        "vy_mean": float(vy.mean()),
        "vy_std": float(vy.std()),
        "vy_abs_mean": float(np.abs(vy).mean()),
        "speed_mean": float(speed.mean()),
        "abs_yaw_rate_mean": float(abs_yaw.mean()),
        "yaw_integral_end_rad": float(yaw_int[-1]),
        "corr_vy_speed": corr(vy, speed),
        "corr_vy_abs_yaw_rate": corr(vy, abs_yaw),
        "corr_vy_yaw_integral": corr(vy, yaw_int),
        "corr_absvy_speed": corr(np.abs(vy), speed),
        "corr_absvy_abs_yaw_rate": corr(np.abs(vy), abs_yaw),
        "corr_absvy_yaw_integral": corr(np.abs(vy), yaw_int),
        "slope_vy_per_speed": slope(speed, vy),
        "slope_absvy_per_speed": slope(speed, np.abs(vy)),
        "slope_absvy_per_yawint": slope(yaw_int, np.abs(vy)),
        "implied_mount_yaw_deg_from_slope": (
            math.degrees(math.asin(max(-1.0, min(1.0, -slope(speed, vy)))))
            if abs(slope(speed, vy)) <= 1.0
            else float("nan")
        ),
    }

    # Decision heuristic
    c_speed = out["corr_absvy_speed"]
    c_yaw = out["corr_absvy_yaw_integral"]
    if np.isfinite(c_speed) and np.isfinite(c_yaw):
        if abs(c_speed) > abs(c_yaw) + 0.1 and abs(c_speed) > 0.35:
            out["verdict"] = "static_mount_offset"
            out["verdict_note"] = (
                "|vy| tracks forward speed more than yaw-integral → geometric mount yaw/roll."
            )
        elif abs(c_yaw) > abs(c_speed) + 0.1 and abs(c_yaw) > 0.35:
            out["verdict"] = "yaw_coupling"
            out["verdict_note"] = (
                "|vy| grows with yaw activity integral → frozen-z / tilted-IMU coupling."
            )
        else:
            out["verdict"] = "mixed_or_weak"
            out["verdict_note"] = (
                "Neither correlation dominates; both mount and coupling may contribute."
            )
    else:
        out["verdict"] = "inconclusive"
        out["verdict_note"] = "Insufficient variation for a clean decision."

    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(t, vy, label="vy_est", color="C0")
    axes[0].plot(t, speed, label="|v|≈speed", color="C1", alpha=0.7)
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].set_ylabel("m/s")
    axes[0].legend(fontsize=8)
    axes[0].set_title(f"{fs.label}: lateral phantom vs speed/yaw")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(t, yaw_rate, label="yaw_rate cmd", color="C2")
    axes[1].set_ylabel("rad/s")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)
    axes[2].plot(t, yaw_int, label="∫|yaw_rate| dt", color="C3")
    axes[2].set_ylabel("rad")
    axes[2].set_xlabel("time [s]")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)
    fig.tight_layout()
    plot = OUT / "plots" / f"{fs.label}_vy_vs_yaw.png"
    fig.savefig(plot, dpi=120)
    plt.close(fig)
    out["plot"] = str(plot.relative_to(OUT)).replace("\\", "/")
    return out


def vertical_crossing_stats(fs: FlightSeries) -> dict:
    """Quantify vertical miss from closest detections (v_norm in image)."""
    # Use detections with small distance during approach/commit
    approach = phase_mask(fs, {"approach", "commit"})
    close = []
    for t, u, v, tx, ty, tz, _corners in fs.dets:
        if not in_intervals(t, approach):
            continue
        dist = math.sqrt(tx * tx + ty * ty + tz * tz)
        if dist > 8.0:
            continue
        # normalized image coords
        u_n = (u - 320.0) / 320.0
        v_n = (v - 180.0) / 180.0  # + = LOW in image = aircraft HIGH
        close.append((t, dist, u_n, v_n, ty))

    if not close:
        # fallback: absolute closest dets overall
        scored = sorted(
            (
                (math.sqrt(tx * tx + ty * ty + tz * tz), t, u, v, ty)
                for t, u, v, tx, ty, tz, _ in fs.dets
            ),
            key=lambda x: x[0],
        )[:40]
        for dist, t, u, v, ty in scored:
            u_n = (u - 320.0) / 320.0
            v_n = (v - 180.0) / 180.0
            close.append((t, dist, u_n, v_n, ty))

    if not close:
        return {"label": fs.label, "phase": fs.phase, "status": "no_close_dets"}

    # Take the closest 5% or min 8 samples
    close.sort(key=lambda r: r[1])
    k = max(8, len(close) // 20)
    top = close[:k]
    v_ns = np.array([r[3] for r in top], float)
    u_ns = np.array([r[2] for r in top], float)
    dists = np.array([r[1] for r in top], float)
    # Positive v_n => gate LOW in image => aircraft too HIGH
    mean_v = float(v_ns.mean())
    if mean_v > 0.25:
        side = "HIGH/top"
    elif mean_v < -0.25:
        side = "LOW/bottom"
    else:
        side = "center-y"
    return {
        "label": fs.label,
        "phase": fs.phase,
        "mount_pitch_param": fs.mount_pitch_param,
        "status": "ok",
        "n_close": len(top),
        "dist_mean_m": float(dists.mean()),
        "v_norm_mean": mean_v,
        "v_norm_std": float(v_ns.std()),
        "u_norm_mean": float(u_ns.mean()),
        "vertical_side": side,
        "high_score": mean_v,  # larger => more high miss
    }


def recommend_pitch(stats3c: list[dict], stats3d: list[dict]) -> dict:
    """Recommend mount_pitch 24/29/34 from vertical residual change."""
    def mean_v(stats):
        ok = [s["v_norm_mean"] for s in stats if s.get("status") == "ok"]
        return float(np.mean(ok)) if ok else float("nan")

    v3c = mean_v(stats3c)
    v3d = mean_v(stats3d)
    # After mount_pitch=29, if still HIGH (v_norm>0), need MORE pitch (34);
    # if now LOW (v_norm<0), overshot → 24; if near 0, keep 29.
    if not np.isfinite(v3d):
        rec, note = 29, "Insufficient phase3d vertical samples; keep 29."
    elif v3d > 0.35:
        rec, note = 34, (
            f"phase3d still HIGH (v_norm={v3d:.2f}); increase mount_pitch toward 34."
        )
    elif v3d < -0.25:
        rec, note = 24, (
            f"phase3d overshot LOW (v_norm={v3d:.2f}); reduce mount_pitch toward 24."
        )
    else:
        rec, note = 29, (
            f"phase3d vertical near center (v_norm={v3d:.2f}); keep mount_pitch=29."
        )
    return {
        "phase3c_v_norm_mean": v3c,
        "phase3d_v_norm_mean": v3d,
        "delta_v_norm": (v3d - v3c) if np.isfinite(v3c) and np.isfinite(v3d) else None,
        "recommend_mount_pitch_deg": rec,
        "note": note,
    }


def discover_flights() -> list[tuple[str, Path, str, float]]:
    flights = []
    # phase3d
    for p in sorted(FIX3D.glob("*-flight.jsonl")):
        params = json.loads(p.with_name(p.name.replace("-flight.jsonl", "-params.json")).read_text(encoding="utf-8"))
        mp = float(params.get("perception", {}).get("camera", {}).get("mount_pitch_deg", 29.0))
        label = "3d_" + p.name.split("-")[0][-6:]  # unique-ish
        # better label from notes IDs
        label = p.stem.replace("-flight", "")
        flights.append((label, p, "phase3d", mp))
    # phase3c (for vertical compare); skip no-vision
    for p in sorted(FIX3C.glob("*-flight.jsonl")):
        params_path = p.with_name(p.name.replace("-flight.jsonl", "-params.json"))
        params = json.loads(params_path.read_text(encoding="utf-8"))
        mp = float(params.get("perception", {}).get("camera", {}).get("mount_pitch_deg", 0.0))
        label = p.stem.replace("-flight", "")
        flights.append((label, p, "phase3c", mp))
    return flights


def write_report(rests, corrs, verts, pitch_rec) -> None:
    lines = [
        "# Lateral frame offset — phase3d pin-down",
        "",
        "Generated by `analysis/2026-07-15-lateral-offset/run_lateral_offset.py`.",
        "Implements AGENTS.md DATA ANALYST CURRENT TASK: pin the LATERAL frame offset.",
        f"HEAD at analysis time: see git; pitch calibration precedent from AGENTS/docs: "
        f"optical {PITCH_CAL_OPTICAL_HORIZON_DEG}° − IMU {PITCH_CAL_IMU_DEG}° ⇒ mount_pitch≈{PITCH_CAL_MOUNT_DEG}°.",
        "",
        "## 1. Camera mount YAW / ROLL (rest-phase)",
        "",
        "Method (twin of pitch calibration): during countdown hover, drone faces the first gate.",
        "Expected body yaw to gate ≈ 0. Optical yaw = atan2(t_x, t_z) from PnP; "
        "mount_yaw ≈ optical_yaw. Mount roll ≈ gate top-edge image angle − IMU small-angle roll.",
        "",
        "| flight | phase | n_dets | opt yaw° | mount_yaw° ±unc | frame-edge roll° | IMU roll_small° | mount_roll° ±unc | IMU pitch° |",
        "|---|---|---:|---:|---|---:|---:|---|---:|",
    ]
    yaw_vals, roll_vals = [], []
    for r in rests:
        if r.get("status") != "ok":
            lines.append(
                f"| `{r['label']}` | {r.get('phase')} | {r.get('n_dets', 0)} | — | — | — | — | — | — |"
            )
            continue
        my = r["mount_yaw_est_deg"]
        mr = r.get("mount_roll_est_deg")
        yaw_vals.append(my)
        if mr is not None:
            roll_vals.append(mr)
        fe = r.get("frame_edge_roll_deg_mean")
        muc = r.get("mount_roll_est_unc_deg")
        fe_s = f"{fe:.2f}" if fe is not None else "—"
        mr_s = f"**{mr:.2f}±{muc:.2f}**" if mr is not None and muc is not None else "—"
        lines.append(
            f"| `{r['label']}` | {r['phase']} | {r['n_dets']} | {r['optical_yaw_to_gate_deg']:.2f} | "
            f"**{my:.2f}±{r['mount_yaw_est_unc_deg']:.2f}** | "
            f"{fe_s} | "
            f"{r['imu_roll_small_deg']:.2f} | "
            f"{mr_s} | "
            f"{r['imu_pitch_deg']:.2f} |"
        )
    if yaw_vals:
        lines += [
            "",
            f"**Aggregate mount_yaw:** mean **{np.mean(yaw_vals):.2f}°** "
            f"(std {np.std(yaw_vals):.2f}°, n={len(yaw_vals)}).",
        ]
    if roll_vals:
        lines.append(
            f"**Aggregate mount_roll:** mean **{np.mean(roll_vals):.2f}°** "
            f"(std {np.std(roll_vals):.2f}°, n={len(roll_vals)})."
        )
    lines += [
        "",
        "### Pitch precedent cross-check",
        "",
        f"IMU pitch at rest ≈ −17.8° was the pitch-calibration input (measured here per flight in table). "
        f"Gate optical elevation is NOT the horizon — do not re-derive mount_pitch from gate pitch alone.",
        "",
        "## 2. Phantom vy vs yaw activity",
        "",
        "During approach/commit, treat vy_est as the lateral error proxy (lined-up approach ⇒ true vy≈0).",
        "Decision rule: |vy|↔speed dominates ⇒ **static mount**; |vy|↔∫|yaw_rate| dominates ⇒ **yaw coupling**.",
        "",
        "| flight | phase | n | vy mean | |vy| mean | speed mean | corr(|vy|,speed) | corr(|vy|,∫|yaw|) | slope vy/speed | implied yaw° | verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for c in corrs:
        if c.get("status") != "ok":
            lines.append(f"| `{c['label']}` | {c.get('phase','')} | — | — | — | — | — | — | — | — | {c.get('status')} |")
            continue
        lines.append(
            f"| `{c['label']}` | {c['phase']} | {c['n']} | {c['vy_mean']:.2f} | {c['vy_abs_mean']:.2f} | "
            f"{c['speed_mean']:.2f} | {c['corr_absvy_speed']:.2f} | {c['corr_absvy_yaw_integral']:.2f} | "
            f"{c['slope_vy_per_speed']:.2f} | {c['implied_mount_yaw_deg_from_slope']:.1f} | "
            f"**{c['verdict']}** |"
        )
    # Majority verdict on phase3d
    v3d = [c for c in corrs if c.get("phase") == "phase3d" and c.get("status") == "ok"]
    if v3d:
        from collections import Counter

        maj = Counter(c["verdict"] for c in v3d).most_common(1)[0][0]
        lines += [
            "",
            f"### Mechanism decision (phase3d)",
            "",
            f"**Majority verdict: `{maj}`**",
            "",
        ]
        for c in v3d:
            lines.append(f"- `{c['label']}`: {c['verdict']} — {c['verdict_note']}")
        lines.append("")
        lines.append("Plots: `plots/*_vy_vs_yaw.png`.")

    lines += [
        "",
        "## 3. Vertical crossing: phase3c vs phase3d (mount_pitch 0 → 29)",
        "",
        "Metric: mean normalized gate `v` among closest approach detections "
        "(+ = LOW in image = aircraft HIGH / top-bar).",
        "",
        "| flight | phase | mount_pitch | n | dist mean | v_norm | u_norm | side |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in verts:
        if s.get("status") != "ok":
            lines.append(f"| `{s['label']}` | {s.get('phase')} | {s.get('mount_pitch_param')} | — | — | — | — | {s.get('status')} |")
            continue
        lines.append(
            f"| `{s['label']}` | {s['phase']} | {s['mount_pitch_param']:.0f} | {s['n_close']} | "
            f"{s['dist_mean_m']:.2f} | {s['v_norm_mean']:.2f} | {s['u_norm_mean']:.2f} | {s['vertical_side']} |"
        )
    lines += [
        "",
        "### Recommendation",
        "",
        f"- phase3c mean v_norm = **{pitch_rec['phase3c_v_norm_mean']:.2f}** (pre mount_pitch).",
        f"- phase3d mean v_norm = **{pitch_rec['phase3d_v_norm_mean']:.2f}** (mount_pitch=29).",
        f"- Δv_norm = {pitch_rec['delta_v_norm']}",
        f"- **Recommend `perception.camera.mount_pitch_deg = {pitch_rec['recommend_mount_pitch_deg']}`**",
        f"- {pitch_rec['note']}",
        "",
        "## Deliverables",
        "",
        "- `report.md` (this file)",
        "- `summary.json`",
        "- `plots/*_vy_vs_yaw.png`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    flights = discover_flights()
    print(f"Loading {len(flights)} flights...", flush=True)
    series = []
    for label, path, phase, mp in flights:
        print(f"  {phase} {label} mount_pitch={mp}", flush=True)
        series.append(load_flight(label, path, phase, mp))

    rests = [rest_mount_offsets(fs) for fs in series]
    corrs = [vy_yaw_correlation(fs) for fs in series]
    verts = [vertical_crossing_stats(fs) for fs in series]
    pitch_rec = recommend_pitch(
        [v for v in verts if v.get("phase") == "phase3c"],
        [v for v in verts if v.get("phase") == "phase3d"],
    )

    summary = {
        "rest_mount": rests,
        "vy_yaw": corrs,
        "vertical": verts,
        "pitch_recommendation": pitch_rec,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(rests, corrs, verts, pitch_rec)
    print(f"Wrote {OUT / 'report.md'}", flush=True)
    print("pitch_rec", pitch_rec, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
