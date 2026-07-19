"""M2 add-ons on the true-vertical audit.

1. Separating regression: (believed − true) vertical gap vs R_lastfix
   on the 88 scored arrivals. Slope ~0.31 = phantom share; intercept
   ~0.33 = aperture share.
2. P4: reflight --blind-last-s warm/cold table with TRUE-frame vertical
   (0.95·ty + 0.31·tz ≈ true_world_dz linearization).
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
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from aigp.core.messages import CameraFrame, ImuSample, RelPose  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.state_estimator import StateEstimator  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.close_tracker import GateCloseTracker  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from aigp.planning.approach import gate_world_dz, true_world_dz  # noqa: E402
from reflight import load_frame_monos, load_frames, load_imu  # noqa: E402

DEFAULT_LEVEL_PITCH = -0.311
COS_TILT = math.cos(abs(DEFAULT_LEVEL_PITCH))  # ~0.952
SIN_TILT = math.sin(abs(DEFAULT_LEVEL_PITCH))  # ~0.306


def true_vert_lin(t_vec) -> float:
    """Advisory linearization: true vertical ≈ 0.95·ty + 0.31·tz (cam)."""
    return COS_TILT * float(t_vec[1]) + SIN_TILT * float(t_vec[2])


def ols(x: np.ndarray, y: np.ndarray) -> dict:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 3:
        return {"n": n, "error": "too few points"}
    A = np.vstack([np.ones(n), x]).T
    coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    intercept, slope = float(coef[0]), float(coef[1])
    yhat = intercept + slope * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else None
    return {
        "n": n,
        "intercept": intercept,
        "slope": slope,
        "r_squared": r2,
        "residual_rmse": float(np.sqrt(ss_res / n)),
        "x_mean": float(np.mean(x)),
        "y_mean": float(np.mean(y)),
    }


# ---------------------------------------------------------------------------
# 1. Separating regression
# ---------------------------------------------------------------------------

def load_log_dets_states(path: Path):
    t0 = None
    states, dets = [], []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            if rec["topic"] == "state" and d.get("gate_rel") and d["gate_rel"].get("t"):
                tv = [float(x) for x in d["gate_rel"]["t"]]
                states.append({
                    "t": t,
                    "t_vec": tv,
                    "dist": float(np.linalg.norm(tv)),
                    "q": d.get("q_att") or [1, 0, 0, 0],
                    "level_pitch": float(d["level_pitch"]) if d.get("level_pitch") is not None else DEFAULT_LEVEL_PITCH,
                    "level_roll": float(d["level_roll"]) if d.get("level_roll") is not None else 0.0,
                    "age": float(d.get("gate_rel_age_s") or 0.0),
                })
            elif rec["topic"] == "detection" and d.get("rel_pose"):
                tv = [float(x) for x in d["rel_pose"]["t"]]
                dets.append({
                    "t": t,
                    "t_vec": tv,
                    "dist": float(np.linalg.norm(tv)),
                })
    return states, dets


def find_flight_log(flight_id: str) -> Path | None:
    hits = list(FIX.rglob(f"{flight_id}-flight.jsonl"))
    return hits[0] if hits else None


def run_separating_regression() -> dict:
    """gap = believed_height − true_height vs R_lastfix.

    Heights are −dz (opening above camera). Believed uses tilted-frame
    gate_world_dz (= cam ty at rest); true uses true_world_dz.
    Equivalent: gap = true_dz − phantom_dz.
    Expected: gap ≈ 0.33 + 0.31·R  (aperture + phantom shares).
    """
    rows_path = OUT / "miss_table_true_vertical.csv"
    if not rows_path.exists():
        return {"error": f"missing {rows_path} — run run_true_vertical_audit.py first"}

    arrivals = []
    with rows_path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fid = r["flight_id"]
            t_c = float(r["t_closest_s"])
            R_closest = float(r["closest_dist_m"])
            age_c = float(r["gate_rel_age_s"])
            log = find_flight_log(fid)
            R_last = None
            gap_h = None
            phantom = true = None
            fix_t = None
            # Last NEAR trusted fix before closest — reject far-gate flickers.
            # Cap: within 1.5× closest or absolutely < 5 m.
            r_cap = max(5.0, R_closest * 1.5) if R_closest < 5.0 else 5.0
            if log and log.exists():
                states, dets = load_log_dets_states(log)
                near = [
                    d for d in dets
                    if d["t"] <= t_c + 0.02 and 0.3 <= d["dist"] <= r_cap
                ]
                if near:
                    d_last = max(near, key=lambda d: d["t"])
                    R_last = d_last["dist"]
                    fix_t = d_last["t"]
                    st = min(states, key=lambda s: abs(s["t"] - d_last["t"])) if states else None
                    q = st["q"] if st else [1.0, 0, 0, 0]
                    lp = st["level_pitch"] if st else DEFAULT_LEVEL_PITCH
                    lr = st["level_roll"] if st else 0.0
                    rel = RelPose(
                        t=np.array(d_last["t_vec"], float),
                        normal=np.array([0.0, 0.0, -1.0]),
                    )
                    qn = np.array(q, float)
                    phantom = gate_world_dz(rel, qn)
                    true = true_world_dz(rel, qn, lr, lp)
                    # Height-above-camera: believed(phantom) − true
                    gap_h = (-phantom) - (-true)  # = true_dz - phantom_dz? 
                    # phantom_h = -phantom_dz; true_h = -true_dz
                    # believed_minus_true height = phantom_h - true_h = true_dz - phantom_dz
                    gap_h = true - phantom
                elif age_c < 0.2:
                    # Fresh lock at closest — use closest state as last fix
                    R_last = R_closest
                    phantom = float(r["miss_vertical_phantom_dz"])
                    true = float(r["miss_vertical_true_dz"])
                    gap_h = true - phantom
                    fix_t = t_c
            if R_last is None or gap_h is None:
                # Last resort: closest-state gap (may be DR) — still score
                R_last = R_closest
                phantom = float(r["miss_vertical_phantom_dz"])
                true = float(r["miss_vertical_true_dz"])
                gap_h = true - phantom
                fix_t = t_c

            arrivals.append({
                "flight_id": fid,
                "attempt_n": int(r["attempt_n"]),
                "t_closest_s": t_c,
                "t_lastfix_s": fix_t,
                "R_closest_m": R_closest,
                "R_lastfix_m": R_last,
                "phantom_dz": phantom,
                "true_dz": true,
                "gap_height_believed_minus_true": gap_h,
                "age_s": age_c,
                "old_label": r["old_label"],
                "true_label": r["true_label"],
            })

    x = np.array([a["R_lastfix_m"] for a in arrivals])
    y = np.array([a["gap_height_believed_minus_true"] for a in arrivals])
    fit = ols(x, y)
    fit["definition"] = (
        "y = believed_opening_height − true_opening_height "
        "(= true_dz − phantom_dz) at LAST NEAR fix (R≤5m); "
        "x = R_lastfix. Far-gate flickers excluded."
    )
    fit["expected_slope"] = SIN_TILT
    fit["expected_intercept_aperture"] = 0.33
    fit["slope_vs_sin_tilt"] = (
        abs(fit["slope"] - SIN_TILT) if fit.get("slope") is not None else None
    )
    fit["R_lastfix_median"] = float(np.median(x))
    fit["R_lastfix_mean"] = float(np.mean(x))

    # Fresh-lock subset + near-range subset (R < 4)
    fresh = [a for a in arrivals if a["age_s"] < 0.25]
    fit_fresh = ols(
        np.array([a["R_lastfix_m"] for a in fresh]),
        np.array([a["gap_height_believed_minus_true"] for a in fresh]),
    ) if len(fresh) >= 3 else {"n": len(fresh)}
    near = [a for a in arrivals if a["R_lastfix_m"] <= 4.0]
    fit_near = ols(
        np.array([a["R_lastfix_m"] for a in near]),
        np.array([a["gap_height_believed_minus_true"] for a in near]),
    ) if len(near) >= 3 else {"n": len(near)}

    # Plot
    (OUT / "plots").mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x, y, s=28, alpha=0.75, edgecolors="k", linewidths=0.3, label="arrivals")
    if fit.get("slope") is not None:
        xs = np.linspace(max(0.1, x.min()), x.max(), 50)
        ax.plot(xs, fit["intercept"] + fit["slope"] * xs, "r-",
                label=f"fit: {fit['intercept']:.3f}+{fit['slope']:.3f}·R  R²={fit['r_squared']:.3f}")
        ax.plot(xs, 0.33 + SIN_TILT * xs, "g--",
                label=f"advisory: 0.33+{SIN_TILT:.3f}·R")
    ax.set_xlabel("R_lastfix (m)")
    ax.set_ylabel("believed − true opening height (m)")
    ax.set_title("M2 separating regression — phantom vs aperture share")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "plots" / "m2_separating_regression.png", dpi=140)
    plt.close(fig)

    with (OUT / "m2_separating_points.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(arrivals[0].keys()))
        w.writeheader()
        w.writerows(arrivals)

    return {
        "fit_all_88": fit,
        "fit_fresh_age_lt_0_25": fit_fresh,
        "fit_R_le_4m": fit_near,
        "n_arrivals": len(arrivals),
        "interpretation": {
            "slope_is_phantom_share": (
                fit.get("slope") is not None and abs(fit["slope"] - SIN_TILT) < 0.15
            ),
            "intercept_is_aperture_share": (
                fit.get("intercept") is not None and abs(fit["intercept"] - 0.33) < 0.25
            ),
            "prior_bug": (
                "v1 used any last det including 10-40m flickers (R_mean~15m) "
                "→ slope collapsed; v2 restricts to near fixes R≤5m"
            ),
        },
    }


# ---------------------------------------------------------------------------
# 2. P4 true-frame holdout
# ---------------------------------------------------------------------------

def run_blind_holdout(slices: list[Path], log: Path, blind_s: float = 0.6) -> dict:
    """Replay reflight blind window; score range + TRUE vertical errors."""
    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])
    detector = HsvGateDetector(params)
    est = StateEstimator(params)
    tracker = GateCloseTracker(params, detector)

    imu = load_imu(str(log))
    monos = load_frame_monos(str(log))
    frames = []
    seen: set[int] = set()
    for slc in slices:
        for f in load_frames(str(slc), monos):
            if f[1] not in seen:
                seen.add(f[1])
                frames.append(f)
    frames.sort(key=lambda f: f[0])
    if not frames or not imu:
        return {"error": "no frames/imu", "slices": [str(s) for s in slices]}

    t_warm = frames[0][0] - int(3.0 * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", t, (fid, sim_ns, img)) for t, fid, sim_ns, img in frames])
    events.sort(key=lambda e: e[1])

    blind = []  # believed_R, meas_R, believed_ty, meas_ty, believed_true_v, meas_true_v
    blind_from = frames[-1][0] - int(blind_s * 1e9)
    last_full_mono = None
    span = (frames[-1][0] - frames[0][0]) / 1e9

    for kind, mono, payload in events:
        if kind == "imu":
            ts, a, g = payload
            est.predict(ImuSample(ts_ns=ts, accel=a, gyro=g))
            continue
        fid, sim_ns, img = payload
        cf = CameraFrame(frame_id=fid, ts_ns=sim_ns, image=img)
        prior = None
        gr = est.state.gate_rel
        if gr is not None and est.state.gate_rel_age_s < 1.0:
            prior = float(np.linalg.norm(gr.t))
        det = detector.detect(cf, prior)
        if det is None and tracker.enabled and last_full_mono is not None \
                and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s \
                and est.state.gate_rel is not None:
            det = tracker.track(cf, est.state.gate_rel)
        elif det is not None and det.confidence >= 0.55:
            last_full_mono = mono
            if det.cert_status == "certified" and det.rel_pose is not None:
                r_fix = float(np.linalg.norm(det.rel_pose.t))
                if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                    tracker.certificate.on_full_quad(det.ts_ns)

        if det is not None and det.rel_pose is not None:
            rng = float(np.linalg.norm(det.rel_pose.t))
            if mono >= blind_from:
                gr = est.state.gate_rel
                ref_prev = blind[-1][1] if blind else (
                    float(np.linalg.norm(gr.t)) if gr is not None else None)
                if gr is not None and ref_prev is not None and abs(rng - ref_prev) < 2.0:
                    lp = float(getattr(est.state, "level_pitch", DEFAULT_LEVEL_PITCH) or DEFAULT_LEVEL_PITCH)
                    lr = float(getattr(est.state, "level_roll", 0.0) or 0.0)
                    b_true = true_world_dz(gr, est.state.q_att, lr, lp)
                    m_true = true_world_dz(det.rel_pose, est.state.q_att, lr, lp)
                    b_lin = true_vert_lin(gr.t)
                    m_lin = true_vert_lin(det.rel_pose.t)
                    blind.append((
                        float(np.linalg.norm(gr.t)), rng,
                        float(gr.t[1]), float(det.rel_pose.t[1]),
                        b_true, m_true, b_lin, m_lin,
                    ))
                continue
            est.update_vision(det)

    if not blind:
        return {
            "error": "empty blind window",
            "n_frames": len(frames),
            "span_s": span,
            "slices": [s.name for s in slices],
        }

    rerr = np.array([b[0] - b[1] for b in blind])
    tyerr = np.array([b[2] - b[3] for b in blind])
    true_err = np.array([b[4] - b[5] for b in blind])
    lin_err = np.array([b[6] - b[7] for b in blind])

    return {
        "slices": [s.name for s in slices],
        "n_frames": len(frames),
        "vision_history_s": span,
        "blind_s": blind_s,
        "n_blind_refs": len(blind),
        "range_error_end_m": float(rerr[-1]),
        "range_error_max_abs_m": float(np.abs(rerr).max()),
        "vertical_ty_error_end_m": float(tyerr[-1]),
        "vertical_ty_error_max_abs_m": float(np.abs(tyerr).max()),
        "vertical_true_dz_error_end_m": float(true_err[-1]),
        "vertical_true_dz_error_max_abs_m": float(np.abs(true_err).max()),
        "vertical_lin_error_end_m": float(lin_err[-1]),
        "vertical_lin_error_max_abs_m": float(np.abs(lin_err).max()),
        "note": (
            "true_dz via true_world_dz(level_pitch); "
            "lin = 0.95·ty+0.31·tz advisory linearization"
        ),
    }


def run_p4_holdout() -> dict:
    base = FIX / "20260716T212744-phase5-closerange-frames"
    fid = "20260716T203450-2ca531c3"
    log = base / f"{fid}-flight.jsonl"
    cold_slice = base / f"{fid}_range3m_to_collision.aigprec"
    warm_early = base / f"{fid}_range5m_to_3m.aigprec"
    if not log.exists():
        return {"error": f"missing log {log}"}
    out = {"flight": fid, "blind_s": 0.6, "legacy_tilted_table": {
        "cold": {"range": "+1.77 / 1.77", "vertical_ty": "0.00 / 0.26"},
        "warm": {"range": "+0.97 / 0.97", "vertical_ty": "−0.69 / 0.76"},
        "source": "docs/thinktank/RESPONSE5.md",
    }}
    print("  P4 cold…", flush=True)
    out["cold"] = run_blind_holdout([cold_slice], log, 0.6)
    print("  P4 warm…", flush=True)
    out["warm"] = run_blind_holdout([warm_early, cold_slice], log, 0.6)
    return out


# ---------------------------------------------------------------------------
# Report update
# ---------------------------------------------------------------------------

def append_report(reg: dict, p4: dict):
    md_paths = [
        OUT / "true-vertical-audit.md",
        ROOT / "analysis" / "2026-07-19-true-vertical-audit.md",
    ]
    section = [
        "",
        "## M2 add-ons",
        "",
        "### 1. Separating regression — phantom vs aperture share",
        "",
        "Across the 88 scored arrivals:",
        "",
        r"\[ y = (\text{believed opening height} - \text{true opening height}) = a + b\, R_{\mathrm{lastfix}} \]",
        "",
        "with heights = `−dz` (so `y = true_dz − phantom_dz`).",
        "",
        f"```json\n{json.dumps(reg, indent=2)}\n```",
        "",
        f"- **slope b** (phantom share): "
        f"**{(reg.get('fit_all_88') or {}).get('slope')}** "
        f"(expect ≈ sin(17.8°) = {SIN_TILT:.3f})",
        f"- **intercept a** (aperture share): "
        f"**{(reg.get('fit_all_88') or {}).get('intercept')}** "
        f"(expect ≈ 0.33)",
        f"- **R²**: **{(reg.get('fit_all_88') or {}).get('r_squared')}**",
        "",
        "Plot: `plots/m2_separating_regression.png` · points: `m2_separating_points.csv`",
        "",
        "### 2. P4 — vertical holdout on TRUE-frame axes",
        "",
        "Same F1 harness as RESPONSE5 (cold = `range3m_to_collision`; "
        "warm = `range5m_to_3m` + collision), `--blind-last-s 0.6`. "
        "Vertical now scored with `true_world_dz` (and the 0.95·ty+0.31·tz "
        "linearization as a cross-check). Legacy 0.76 m max was on tilted ty.",
        "",
        "| condition | vision hist | range err end/max | ty err end/max (tilted) | TRUE dz err end/max | lin err end/max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in ("cold", "warm"):
        r = p4.get(key) or {}
        if r.get("error"):
            section.append(f"| {key} | — | ERROR: {r['error']} | — | — | — |")
            continue
        section.append(
            f"| {key} | {r.get('vision_history_s'):.2f}s | "
            f"{r.get('range_error_end_m'):+.2f} / {r.get('range_error_max_abs_m'):.2f} | "
            f"{r.get('vertical_ty_error_end_m'):+.2f} / {r.get('vertical_ty_error_max_abs_m'):.2f} | "
            f"**{r.get('vertical_true_dz_error_end_m'):+.2f} / {r.get('vertical_true_dz_error_max_abs_m'):.2f}** | "
            f"{r.get('vertical_lin_error_end_m'):+.2f} / {r.get('vertical_lin_error_max_abs_m'):.2f} |"
        )
    section += [
        "",
        f"```json\n{json.dumps(p4, indent=2, default=str)}\n```",
        "",
        "Legacy tilted warm max |ty| error **0.76 m** → replace with TRUE-frame "
        "max |dz| from the warm row above for T1 budget work.",
        "",
    ]
    text = "\n".join(section)
    for p in md_paths:
        if p.exists():
            prev = p.read_text(encoding="utf-8")
            if "## M2 add-ons" in prev:
                prev = prev.split("## M2 add-ons")[0].rstrip() + "\n"
            p.write_text(prev + text, encoding="utf-8")
        else:
            p.write_text("# True-vertical audit — M2 add-ons\n" + text, encoding="utf-8")


def main() -> int:
    print("=== M2.1 separating regression ===", flush=True)
    reg = run_separating_regression()
    fit = reg.get("fit_all_88") or {}
    print(
        f"  fit_all_88 n={fit.get('n')} intercept={fit.get('intercept')} "
        f"slope={fit.get('slope')} R2={fit.get('r_squared')} "
        f"R_lastfix mean={fit.get('R_lastfix_mean')} median={fit.get('R_lastfix_median')}",
        flush=True,
    )
    fit4 = reg.get("fit_R_le_4m") or {}
    print(
        f"  fit_R_le_4m n={fit4.get('n')} intercept={fit4.get('intercept')} "
        f"slope={fit4.get('slope')} R2={fit4.get('r_squared')} "
        f"R_lastfix x_mean={fit4.get('x_mean')}",
        flush=True,
    )
    (OUT / "m2_separating_regression.json").write_text(
        json.dumps(reg, indent=2), encoding="utf-8"
    )

    print("=== M2.2 / P4 true-frame holdout ===", flush=True)
    p4 = run_p4_holdout()
    for k in ("cold", "warm"):
        r = p4.get(k) or {}
        print(
            f"  {k}: range {r.get('range_error_end_m')}/{r.get('range_error_max_abs_m')} "
            f"ty {r.get('vertical_ty_error_end_m')}/{r.get('vertical_ty_error_max_abs_m')} "
            f"TRUE {r.get('vertical_true_dz_error_end_m')}/{r.get('vertical_true_dz_error_max_abs_m')}",
            flush=True,
        )
    (OUT / "m2_p4_true_holdout.json").write_text(
        json.dumps(p4, indent=2, default=str), encoding="utf-8"
    )

    append_report(reg, p4)

    # Update summary.json
    summary_path = OUT / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    summary["m2"] = {
        "separating_regression": reg.get("fit_all_88"),
        "separating_interpretation": reg.get("interpretation"),
        "p4_holdout": {
            "cold": {k: (p4.get("cold") or {}).get(k) for k in (
                "vision_history_s", "range_error_end_m", "range_error_max_abs_m",
                "vertical_ty_error_end_m", "vertical_ty_error_max_abs_m",
                "vertical_true_dz_error_end_m", "vertical_true_dz_error_max_abs_m",
                "vertical_lin_error_end_m", "vertical_lin_error_max_abs_m",
            )},
            "warm": {k: (p4.get("warm") or {}).get(k) for k in (
                "vision_history_s", "range_error_end_m", "range_error_max_abs_m",
                "vertical_ty_error_end_m", "vertical_ty_error_max_abs_m",
                "vertical_true_dz_error_end_m", "vertical_true_dz_error_max_abs_m",
                "vertical_lin_error_end_m", "vertical_lin_error_max_abs_m",
            )},
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("Updated report + summary.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
