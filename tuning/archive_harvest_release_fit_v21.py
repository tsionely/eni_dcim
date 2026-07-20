"""Archive harvest -> multi-cluster SIGMA_A release fit v2.1.

QA & MOCK-TUNER scope: recorded replay/CSV analysis only. No real simulator
is launched, clicked, reset, or commanded.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, minimize_scalar

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from aigp.core.params import ParamSet  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.planning.vertical_terminal import compute_terminal_guidance, robust_slope  # noqa: E402
from run_anchor_r26 import (  # noqa: E402
    attach_flight_signals,
    full_observation_series,
    withheld_full_vz_ref,
)
from run_l1_perception_replay import (  # noqa: E402
    assert_mock_safe,
    fnum,
    fmt,
    run_video_replay,
    write_csv,
)


ARCHIVE_DIRS = [
    ROOT / "fixtures" / "20260720T071602-phase6l-cohort-3",
    ROOT / "fixtures" / "20260720T133508-phase7m-metrology-f1",
    ROOT / "fixtures" / "20260720T134548-phase7m-metrology-f2",
    ROOT / "fixtures" / "20260720T135040-phase7m-metrology-f3",
]
P4_DIR = ROOT / "tuning" / "hold-lift-p4-3b554f3-3942837-20260720T115546Z"
OUT_PREFIX = "archive-harvest-release-fit-v21"
BOOTSTRAP_N = 2200
BOOTSTRAP_SEED = 20260720
NU = 5.0
SIGMA_A_GATE = 0.35
MIN_RELEASE_CLUSTERS = 6
AGE_BINS = [
    ("0p00-0p10", 0.00, 0.10),
    ("0p10-0p20", 0.10, 0.20),
    ("0p20-0p30", 0.20, 0.30),
    ("0p30-0p40", 0.30, 0.40),
    ("0p40-0p50", 0.40, 0.50),
    ("gt0p50", 0.50, float("inf")),
]


def percentile(values: list[float], pct: float) -> float | None:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = pct / 100.0 * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def rms(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return None
    return math.sqrt(statistics.fmean([v * v for v in vals]))


def age_bin(age: float) -> str:
    for label, lo, hi in AGE_BINS:
        if lo <= age < hi:
            return label
    return "unknown"


def git_head() -> tuple[str, str]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return head, head[:7]


def source_commit(ref: str) -> tuple[str, str]:
    sha = subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()
    return sha, sha[:7]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def targets_from_archive() -> list[dict]:
    targets = []
    seq = 0
    for archive_dir in ARCHIVE_DIRS:
        if not (archive_dir / "manifest.json").exists():
            continue
        manifest = json.loads((archive_dir / "manifest.json").read_text(encoding="utf-8"))
        recordings = {}
        logs = {}
        for item in manifest["items"]:
            file = item["file"]
            if file.endswith(".aigprec"):
                fid = file.replace("_takeoff_to_end.aigprec", "")
                recordings[fid] = file
            elif file.endswith("-flight.jsonl"):
                fid = file.replace("-flight.jsonl", "")
                logs[fid] = file
        for fid in sorted(recordings):
            if fid not in logs:
                continue
            seq += 1
            targets.append({
                "label": f"F{seq}",
                "flight_id": fid,
                "fixture_dir": archive_dir.name,
                "recording": str((archive_dir / recordings[fid]).relative_to(ROOT)),
                "log": str((archive_dir / logs[fid]).relative_to(ROOT)),
                "contact_offset_m": 0.162,
            })
    return targets


def certified_full(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("feature_mode") == "FULL_QUAD"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
        and fnum(r.get("range_z_m")) is not None
    ]


def certified_side(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("feature_mode") == "SIDE_PAIR"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
        and fnum(r.get("range_z_m")) is not None
    ]


def split_approaches(rows: list[dict], meta: dict) -> list[dict]:
    full_close = [r for r in certified_full(rows) if float(r["range_z_m"]) <= 3.5]
    full_close.sort(key=lambda r: float(r["t_rel_s"]))
    if not full_close:
        return []
    segments: list[list[dict]] = []
    cur = [full_close[0]]
    for row in full_close[1:]:
        dt = float(row["t_rel_s"]) - float(cur[-1]["t_rel_s"])
        if dt > 1.25:
            segments.append(cur)
            cur = [row]
        else:
            cur.append(row)
    segments.append(cur)
    out = []
    sides = certified_side(rows)
    for idx, seg in enumerate(segments, start=1):
        t0 = max(0.0, float(seg[0]["t_rel_s"]) - 0.50)
        t1 = float(seg[-1]["t_rel_s"]) + 0.85
        side_in = [s for s in sides if t0 <= float(s["t_rel_s"]) <= t1]
        if len(seg) < 4 or len(side_in) < 2:
            continue
        aid = f"{meta['flight_id']}:A{idx}"
        out.append({
            "approach_id": aid,
            "flight": meta["flight"],
            "flight_id": meta["flight_id"],
            "t_start_s": t0,
            "t_end_s": t1,
            "full_rows_below_3p5": len(seg),
            "side_rows_est": len(side_in),
            "full_depth_m": min(float(r["range_z_m"]) for r in seg),
            "est_rows": len(side_in),
            "census_ok": True,
        })
    return out


def census_diagnostics(features: list[dict], metas: list[dict],
                       approaches: list[dict]) -> list[dict]:
    rows = []
    for meta in metas:
        fr = [r for r in features if r.get("flight_id") == meta["flight_id"]]
        apps = [a for a in approaches if a["flight_id"] == meta["flight_id"]]
        full_any = [
            r for r in fr
            if r.get("feature_mode") == "FULL_QUAD"
            and r.get("cert_status") == "certified"
            and fnum(r.get("range_z_m")) is not None
            and float(r["range_z_m"]) <= 3.5
        ]
        full_ok = [
            r for r in full_any
            if fnum(r.get("e_meas")) is not None
            and r.get("e_reject") == "ok"
        ]
        side_cert = certified_side(fr)
        side_row_only = [r for r in fr if r.get("feature_mode") == "SIDE_PAIR_ROW_ONLY"]
        if apps:
            reason = "OK"
        elif not full_any:
            reason = "NO_CERTIFIED_FULL_BELOW_3P5"
        elif len(full_ok) < 4:
            reason = "FULL_BELOW_3P5_NOT_EZ_USABLE"
        elif len(side_cert) < 2:
            reason = "NO_CERTIFIED_SIDE_ROWS"
        else:
            reason = "SEGMENT_SPLIT_REJECTED"
        rows.append({
            "flight": meta["flight"],
            "flight_id": meta["flight_id"],
            "approaches": len(apps),
            "full_certified_below_3p5_any": len(full_any),
            "full_ok_below_3p5": len(full_ok),
            "full_depth_any_m": min([float(r["range_z_m"]) for r in full_any], default=""),
            "full_depth_ok_m": min([float(r["range_z_m"]) for r in full_ok], default=""),
            "side_pair_certified": len(side_cert),
            "side_pair_row_only": len(side_row_only),
            "failure_reason": reason,
        })
    return rows


def run_archive_replays(params: ParamSet) -> tuple[list[dict], list[dict], list[dict]]:
    features = []
    metas = []
    approaches = []
    for target in targets_from_archive():
        rows, meta = run_video_replay(params, target)
        attach_flight_signals(params, rows, target)
        features.extend(rows)
        metas.append(meta)
        approaches.extend(split_approaches(rows, meta))
    return features, metas, approaches


def rows_for_approach(rows: list[dict], app: dict) -> list[dict]:
    return [
        r for r in rows
        if r.get("flight_id") == app["flight_id"]
        and float(app["t_start_s"]) <= float(r["t_rel_s"]) <= float(app["t_end_s"])
    ]


def history_before(full_rows: list[dict], ts_s: float, window_s: float = 0.50) -> list[dict]:
    hist = [
        r for r in full_rows
        if ts_s - window_s <= float(r["feature_ts_ns"]) / 1e9 <= ts_s
    ]
    by_ts = {}
    for row in hist:
        by_ts[int(row["feature_ts_ns"])] = row
    return [by_ts[k] for k in sorted(by_ts)]


def slope_rate(hist: list[dict]) -> tuple[float | None, int, float, float]:
    if len(hist) < 4:
        return None, len(hist), 0.0, 0.0
    times = [float(r["feature_ts_ns"]) / 1e9 for r in hist]
    vals = [float(r["e_meas"]) for r in hist]
    slope = robust_slope(times, vals)
    if slope is None:
        return None, len(hist), 0.0, 0.0
    span = max(times) - min(times)
    auth = min(1.0, (span / 0.3) * (len(set(times)) / 10.0))
    return -float(slope), len(set(times)), span, auth


def forecast_pair(params: ParamSet, row: dict, e_z: float,
                  old_vz: float, new_vz: float) -> dict:
    r_z = fnum(row.get("range_z_m"))
    speed = fnum(row.get("setpoint_speed_xy_mps"))
    if r_z is None or speed is None or speed <= 0.05:
        return {
            "shadow_tau_s": "",
            "shadow_e_z_cmd_m": "",
            "shadow_e_cross_old_m": "",
            "shadow_e_cross_new_m": "",
            "shadow_vz_cmd_old_mps": "",
            "shadow_vz_cmd_new_mps": "",
            "shadow_command_delta_mps": "",
            "shadow_e_cross_delta_m": "",
        }
    tau_s = max(0.0, r_z / speed)
    cmd_clamp = float(params.get("planner.terminal.cmd_clamp_m", default=0.10))
    margin = float(params.get("planner.terminal.margin_m", default=0.55))
    vz_max = float(params.get("planner.terminal.vz_max_mps", default=0.6))
    az_max = float(params.get("planner.terminal.az_max_mps2", default=3.0))
    e_cmd = float(np.clip(e_z, -cmd_clamp, cmd_clamp))
    old = compute_terminal_guidance(e_z=e_cmd, sigma_e=0.10, v_z=old_vz,
                                    sigma_v=0.15, tau_s=tau_s,
                                    margin_m=margin, vz_max=vz_max,
                                    az_max=az_max)
    new = compute_terminal_guidance(e_z=e_cmd, sigma_e=0.10, v_z=new_vz,
                                    sigma_v=0.15, tau_s=tau_s,
                                    margin_m=margin, vz_max=vz_max,
                                    az_max=az_max)
    old_cmd = old["vz_cmd"]
    new_cmd = new["vz_cmd"]
    return {
        "shadow_tau_s": tau_s,
        "shadow_e_z_cmd_m": e_cmd,
        "shadow_e_cross_old_m": old["e_cross"],
        "shadow_e_cross_new_m": new["e_cross"],
        "shadow_vz_cmd_old_mps": old_cmd if old_cmd is not None else "",
        "shadow_vz_cmd_new_mps": new_cmd if new_cmd is not None else "",
        "shadow_command_delta_mps": (
            new_cmd - old_cmd if old_cmd is not None and new_cmd is not None else ""
        ),
        "shadow_e_cross_delta_m": old["e_cross"] - new["e_cross"],
    }


def build_forced_withhold_rows(features: list[dict], approaches: list[dict]) -> tuple[list[dict], list[dict]]:
    samples = []
    cluster_rows = []
    for app in approaches:
        app_rows = rows_for_approach(features, app)
        full_rows = certified_full(app_rows)
        side_rows = certified_side(app_rows)
        full_rows.sort(key=lambda r: int(r["feature_ts_ns"]))
        side_rows.sort(key=lambda r: int(r["feature_ts_ns"]))
        full_series = full_observation_series(app_rows)
        cut_rows = []
        for row in full_rows:
            if float(row["range_z_m"]) > 3.5:
                continue
            ts_s = float(row["feature_ts_ns"]) / 1e9
            rate, n_full, span_full, auth = slope_rate(history_before(full_rows, ts_s))
            if rate is None or n_full < 4:
                continue
            after = [
                s for s in side_rows
                if 0.10 <= float(s["feature_ts_ns"]) / 1e9 - ts_s <= 0.55
            ]
            if after:
                cut_rows.append((row, rate, n_full, span_full, auth))
        # Keep enough cut points for age coverage without turning one approach
        # into an accidental row-count empire.
        if len(cut_rows) > 10:
            step = max(1, len(cut_rows) // 10)
            cut_rows = cut_rows[::step][:10]
        for cut_idx, (cut, v_latch_true, n_full, span_full, auth) in enumerate(cut_rows, start=1):
            cut_ts_ns = int(cut["feature_ts_ns"])
            cut_ts_s = cut_ts_ns / 1e9
            v_anchor = v_latch_true * auth
            anchor_applied = fnum(cut.get("setpoint_vz_up_mps")) or 0.0
            pred_b0 = (1.0 - auth) * v_latch_true
            cut_id = f"{app['approach_id']}:cut{cut_idx:02d}"
            for side in side_rows:
                age = float(side["feature_ts_ns"]) / 1e9 - cut_ts_s
                if not (0.0 <= age <= 0.55):
                    continue
                oracle_ref = withheld_full_vz_ref(full_series, float(side["feature_ts_ns"]) / 1e9, cut_ts_ns)
                v_ref = fnum(oracle_ref.get("oracle_ref_vz_up_mps"))
                if v_ref is None:
                    continue
                applied_now = fnum(side.get("setpoint_vz_up_mps"))
                ff = (applied_now - anchor_applied) if applied_now is not None else 0.0
                v_hold = v_anchor + ff
                v_shadow = v_latch_true + ff
                rv = v_ref - v_hold
                regime = "authority_limited" if auth < 0.95 else (
                    "up" if ff > 0.02 else "down" if ff < -0.02 else "flat_no_ff"
                )
                e_side = float(side["e_meas"])
                sample = {
                    "approach_id": app["approach_id"],
                    "cluster_id": app["approach_id"],
                    "flight": app["flight"],
                    "flight_id": app["flight_id"],
                    "cut_id": cut_id,
                    "cut_frame_id": cut["frame_id"],
                    "frame_id": side["frame_id"],
                    "feature_ts_ns": side["feature_ts_ns"],
                    "age_s": age,
                    "age2_s2": age * age,
                    "age_bin": age_bin(age),
                    "range_z_m": side.get("range_z_m", ""),
                    "r_v_mps": rv,
                    "rv2_m2ps2": rv * rv,
                    "v_ref_oracle_mps": v_ref,
                    "v_hold_mps": v_hold,
                    "v_shadow_hold_mps": v_shadow,
                    "residual_sign_convention": "r_v = v_ref_oracle - (v_anchor_old + feed_forward)",
                    "v_latch_mps": v_latch_true,
                    "v_latch_true_mps": v_latch_true,
                    "v_full_raw_mps": v_latch_true,
                    "v_anchor_old_mps": v_anchor,
                    "v_latch_auth_applied_mps": v_anchor,
                    "delta_latch_mps": v_anchor - v_latch_true,
                    "auth_at_latch": auth,
                    "rate_anchor_v_raw": cut.get("rate_anchor_v_raw", ""),
                    "rate_anchor_quality": cut.get("rate_anchor_quality", ""),
                    "shadow_vz_up": side.get("shadow_vz_up", ""),
                    "n_full_at_latch": n_full,
                    "span_full_at_latch_s": span_full,
                    "predicted_b0_from_auth_mps": pred_b0,
                    "rate_feed_forward_mps": ff,
                    "command_regime": regime,
                    "oracle_ref_n": oracle_ref.get("oracle_ref_n", ""),
                    "oracle_ref_span_s": oracle_ref.get("oracle_ref_span_s", ""),
                }
                sample.update(forecast_pair(params, side, e_side, v_hold, v_shadow))
                samples.append(sample)
        app_samples = [s for s in samples if s["approach_id"] == app["approach_id"]]
        b0, b1 = fit_mean_values(app_samples)
        preds = [float(s["predicted_b0_from_auth_mps"]) for s in app_samples]
        auths = [float(s["auth_at_latch"]) for s in app_samples]
        cluster_rows.append({
            **app,
            "sample_rows": len(app_samples),
            "cut_count": len({s["cut_id"] for s in app_samples}),
            "auth_at_latch_median": statistics.median(auths) if auths else "",
            "v_latch_median_mps": statistics.median([float(s["v_latch_true_mps"]) for s in app_samples]) if app_samples else "",
            "predicted_b0_median_mps": statistics.median(preds) if preds else "",
            "fitted_b0_mps": b0 if b0 is not None else "",
            "fitted_b1_mps_per_s": b1 if b1 is not None else "",
            "b0_pred_minus_fit_mps": (
                statistics.median(preds) - b0 if preds and b0 is not None else ""
            ),
        })
    return samples, cluster_rows


def fit_mean_values(samples: list[dict]) -> tuple[float | None, float | None]:
    if not samples:
        return None, None
    xs = [float(s["age_s"]) for s in samples]
    ys = [float(s["r_v_mps"]) for s in samples]
    xm = statistics.fmean(xs)
    ym = statistics.fmean(ys)
    den = sum((x - xm) ** 2 for x in xs)
    b1 = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / den if den > 1e-18 else 0.0
    b0 = ym - b1 * xm
    return b0, b1


def fit_mean(samples: list[dict]) -> dict:
    b0, b1 = fit_mean_values(samples)
    if b0 is None:
        return {"b0": "", "b1": "", "mean_fit_residual_rms_mps": ""}
    centered = [float(s["r_v_mps"]) - (b0 + b1 * float(s["age_s"])) for s in samples]
    return {"b0": b0, "b1": b1, "mean_fit_residual_rms_mps": rms(centered)}


def student_nll(samples: list[dict], b0: float, b1: float, sigma0: float, sigmaa: float) -> float:
    total = 0.0
    for row in samples:
        age = float(row["age_s"])
        err = float(row["r_v_mps"]) - (b0 + b1 * age)
        scale = math.sqrt(max(sigma0 * sigma0 + (sigmaa * age) ** 2, 1e-12))
        z = err / scale
        total += math.log(scale) + 0.5 * (NU + 1.0) * math.log1p((z * z) / NU)
    return total


def fit_scale(samples: list[dict], b0: float, b1: float) -> dict:
    centered = [float(s["r_v_mps"]) - (b0 + b1 * float(s["age_s"])) for s in samples]
    base = rms(centered) or 0.02

    def obj(x):
        return student_nll(samples, b0, b1, float(x[0]), float(x[1]))

    best = None
    starts = [(base, 0.05), (max(base, 0.02), 0.25), (0.05, 0.50), (0.10, 0.0)]
    for start in starts:
        res = minimize(
            obj,
            np.asarray(start, dtype=float),
            method="L-BFGS-B",
            bounds=[(1e-6, 3.0), (0.0, 5.0)],
            options={"maxiter": 300},
        )
        if best is None or float(res.fun) < float(best.fun):
            best = res
    return {
        "sigma_0_mps": float(best.x[0]),
        "sigma_a_mps2": float(best.x[1]),
        "nll": float(best.fun),
    }


def profile_u95(samples: list[dict], b0: float, b1: float, best_nll: float) -> dict:
    threshold = best_nll + 1.352771727047702  # one-sided 95%, 0.5*chi2_1(0.95)

    def prof_loss(sa: float) -> float:
        res = minimize_scalar(
            lambda s0: student_nll(samples, b0, b1, max(float(s0), 1e-6), sa),
            bounds=(1e-6, 3.0),
            method="bounded",
            options={"xatol": 1e-5},
        )
        return float(res.fun)

    grid = np.linspace(0.0, 2.0, 81)
    losses = [prof_loss(float(sa)) for sa in grid]
    valid = [float(sa) for sa, loss in zip(grid, losses) if loss <= threshold]
    nearly_flat = max(losses) - min(losses) < 0.25
    u95 = max(valid) if valid else 0.0
    if valid and u95 >= float(grid[-1]) - 1e-9:
        nearly_flat = True
    return {
        "profile_u95_sigma_a_mps2": u95,
        "profile_threshold_nll": threshold,
        "profile_nearly_flat": nearly_flat,
        "profile_loss_min": min(losses),
        "profile_loss_max": max(losses),
    }


def fit_release(samples: list[dict]) -> dict:
    mean = fit_mean(samples)
    b0 = float(mean["b0"] or 0.0)
    b1 = float(mean["b1"] or 0.0)
    scale = fit_scale(samples, b0, b1)
    prof = profile_u95(samples, b0, b1, scale["nll"])
    return {**mean, **scale, **prof}


def by_cluster(samples: list[dict]) -> dict[str, list[dict]]:
    out = {}
    for row in samples:
        out.setdefault(str(row["cluster_id"]), []).append(row)
    return out


def cluster_bootstrap(samples: list[dict], n_boot: int = BOOTSTRAP_N) -> dict:
    groups = by_cluster(samples)
    ids = sorted(groups)
    rng = random.Random(BOOTSTRAP_SEED)
    vals = []
    b0s = []
    b1s = []
    for _ in range(n_boot):
        draw = []
        for _cid in ids:
            draw.extend(groups[rng.choice(ids)])
        fit = fit_release(draw)
        vals.append(float(fit["sigma_a_mps2"]))
        b0s.append(float(fit["b0"]))
        b1s.append(float(fit["b1"]))
    return {
        "cluster_bootstrap_n": n_boot,
        "cluster_bootstrap_u95_sigma_a_mps2": percentile(vals, 95),
        "cluster_bootstrap_sigma_a_min_mps2": min(vals) if vals else "",
        "cluster_bootstrap_sigma_a_max_mps2": max(vals) if vals else "",
        "b0_ci_low_mps": percentile(b0s, 2.5),
        "b0_ci_median_mps": percentile(b0s, 50),
        "b0_ci_high_mps": percentile(b0s, 97.5),
        "b1_ci_low_mps_per_s": percentile(b1s, 2.5),
        "b1_ci_median_mps_per_s": percentile(b1s, 50),
        "b1_ci_high_mps_per_s": percentile(b1s, 97.5),
    }


def loao_sensitivity(samples: list[dict]) -> list[dict]:
    rows = []
    groups = by_cluster(samples)
    for cid in sorted(groups):
        train = [r for r in samples if r["cluster_id"] != cid]
        if not train:
            continue
        fit = fit_release(train)
        u95 = float(fit["profile_u95_sigma_a_mps2"])
        rows.append({
            "left_out_approach": cid,
            "train_clusters": len({r["cluster_id"] for r in train}),
            "train_rows": len(train),
            "point_sigma_a_mps2": fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": u95,
            "pushes_over_gate": u95 > SIGMA_A_GATE,
            "profile_nearly_flat": fit["profile_nearly_flat"],
        })
    return rows


def flight_loao_sensitivity(samples: list[dict]) -> list[dict]:
    rows = []
    flight_ids = sorted({r["flight_id"] for r in samples})
    for fid in flight_ids:
        train = [r for r in samples if r["flight_id"] != fid]
        if not train:
            continue
        fit = fit_release(train)
        u95 = float(fit["profile_u95_sigma_a_mps2"])
        rows.append({
            "left_out_flight_id": fid,
            "train_flights": len({r["flight_id"] for r in train}),
            "train_clusters": len({r["cluster_id"] for r in train}),
            "train_rows": len(train),
            "point_sigma_a_mps2": fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": u95,
            "pushes_over_gate": u95 > SIGMA_A_GATE,
            "profile_nearly_flat": fit["profile_nearly_flat"],
        })
    return rows


def regime_rows(samples: list[dict]) -> list[dict]:
    out = []
    for label in ["up", "down", "triangular", "slew_limited", "saturated", "authority_limited", "flat_no_ff"]:
        group = [r for r in samples if r.get("command_regime") == label]
        ages = [float(r["age_s"]) for r in group]
        vals = [float(r["r_v_mps"]) for r in group]
        out.append({
            "command_regime": label,
            "n": len(group),
            "approaches": len({r["cluster_id"] for r in group}),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "signed_mean_r_v_mps": statistics.fmean(vals) if vals else "",
            "signed_median_r_v_mps": statistics.median(vals) if vals else "",
            "r_v_rms_mps": rms(vals) if vals else "",
        })
    return out


def cluster_balanced_coverage(samples: list[dict], fit: dict) -> tuple[list[dict], str, bool]:
    b0 = float(fit["b0"])
    b1 = float(fit["b1"])
    sigma0 = float(fit["sigma_0_mps"])
    sigmaa = float(fit["sigma_a_mps2"])
    out = []
    max_validated = "none"
    coverages = []
    for label, lo, hi in AGE_BINS:
        group = [r for r in samples if lo <= float(r["age_s"]) < hi]
        approach_ids = sorted({r["cluster_id"] for r in group})
        flight_ids = sorted({r["flight_id"] for r in group})
        centered = [float(r["r_v_mps"]) - (b0 + b1 * float(r["age_s"])) for r in group]
        per_app = []
        dangerous = 0
        for aid in approach_ids:
            ar = [r for r in group if r["cluster_id"] == aid]
            ok = 0
            for r in ar:
                age = float(r["age_s"])
                pred = b0 + b1 * age
                scale = math.sqrt(sigma0 * sigma0 + (sigmaa * age) ** 2)
                inside = abs(float(r["r_v_mps"]) - pred) <= 2.0 * scale
                ok += int(inside)
                dangerous += int(not inside)
            per_app.append(ok / len(ar) if ar else 0.0)
        balanced = statistics.fmean(per_app) if per_app else ""
        coverages.append(float(balanced) if fnum(balanced) is not None else None)
        predicted_scales = [
            math.sqrt(sigma0 * sigma0 + (sigmaa * float(r["age_s"])) ** 2)
            for r in group
        ]
        green = (
            len(approach_ids) >= 5
            and fnum(balanced) is not None
            and float(balanced) >= 0.95
            and dangerous == 0
        )
        if green:
            max_validated = label
        out.append({
            "age_bin": label,
            "approaches": len(approach_ids),
            "flights": len(flight_ids),
            "n_rows": len(group),
            "median_signed_r_v_mps": statistics.median([float(r["r_v_mps"]) for r in group]) if group else "",
            "p95_abs_centered_r_v_mps": percentile([abs(v) for v in centered], 95) if centered else "",
            "predicted_scale_mps": statistics.median(predicted_scales) if predicted_scales else "",
            "balanced_coverage": balanced,
            "worst_undercoverage": min(per_app) if per_app else "",
            "dangerous_safe_misclassifications": dangerous,
            "green": green,
        })
    nums = [c for c in coverages if c is not None]
    monotone_degrade = len(nums) >= 3 and all(a >= b for a, b in zip(nums, nums[1:]))
    return out, max_validated, monotone_degrade


def fallback_bound(samples: list[dict], fit: dict) -> list[dict]:
    b0 = float(fit["b0"])
    b1 = float(fit["b1"])
    running = 0.0
    out = []
    for label, lo, hi in AGE_BINS:
        group = [r for r in samples if lo <= float(r["age_s"]) < hi]
        vals = [abs(float(r["r_v_mps"]) - (b0 + b1 * float(r["age_s"]))) for r in group]
        raw = percentile(vals, 95) if vals else None
        if raw is not None:
            running = max(running, raw)
        out.append({
            "age_bin": label,
            "n_rows": len(group),
            "raw_p95_abs_centered_r_v_mps": raw if raw is not None else "",
            "isotonic_B_rate_drift_mps": running,
        })
    return out


def pseudo_samples(features: list[dict], approaches: list[dict]) -> list[dict]:
    out = []
    for app in approaches:
        rows = rows_for_approach(features, app)
        full = certified_full(rows)
        full.sort(key=lambda r: int(r["feature_ts_ns"]))
        for anchor in full:
            t0 = float(anchor["feature_ts_ns"]) / 1e9
            hist = history_before(full, t0, 0.35)
            v_true, n, span, auth = slope_rate(hist)
            if v_true is None:
                continue
            v_anchor = v_true * auth
            for age in [0.10, 0.20, 0.30, 0.40, 0.50]:
                eval_pts = [
                    r for r in full
                    if t0 + age <= float(r["feature_ts_ns"]) / 1e9 <= t0 + age + 0.35
                ]
                if len(eval_pts) < 4:
                    continue
                v_ref, _, _, _ = slope_rate(eval_pts)
                if v_ref is None:
                    continue
                rv = v_ref - v_anchor
                out.append({
                    "approach_id": app["approach_id"],
                    "cluster_id": app["approach_id"],
                    "flight": app["flight"],
                    "flight_id": app["flight_id"],
                    "anchor_frame_id": anchor["frame_id"],
                    "age_s": age,
                    "age_bin": age_bin(age),
                    "r_v_mps": rv,
                    "rv2_m2ps2": rv * rv,
                    "auth_at_latch": auth,
                    "n_full_at_latch": n,
                    "span_full_at_latch_s": span,
                })
    return out


def p4_acceptance_diff() -> list[dict]:
    rows = read_csv(P4_DIR / "p4_feature_rows.csv")
    det = {
        int(r["frame_id"]): r for r in rows
        if r["flight"] == "F4" and r["arm"] == "detector_only" and r["feature_mode"] == "FULL_QUAD"
    }
    par_full = {
        int(r["frame_id"]): r for r in rows
        if r["flight"] == "F4" and r["arm"] == "parallel_tracker" and r["feature_mode"] == "FULL_QUAD"
    }
    par_side = [
        r for r in rows
        if r["flight"] == "F4" and r["arm"] == "parallel_tracker" and r["feature_mode"] == "SIDE_PAIR"
    ]
    lost = sorted(set(det) - set(par_full))
    out = []
    for fid in lost:
        prior_side = [r for r in par_side if int(r["frame_id"]) <= fid]
        preceded = bool(prior_side)
        out.append({
            "flight": "F4",
            "frame_id": fid,
            "phase": det[fid].get("phase", ""),
            "ts_proxy_frame_id": fid,
            "range_m": "",
            "parallel_acceptance_stage": "other_identity_or_lock_acceptance",
            "parallel_certificate_status": "not_available_in_p4_feature_rows",
            "parallel_scale_gate": "not_available_in_p4_feature_rows",
            "tracker_prediction_inconsistent_relock_preceded": preceded,
            "range_mismatch_m": "not_available_in_p4_feature_rows",
            "verdict": (
                "needs enhanced replay trace; existing P4 CSV proves row loss but lacks raw reject stage/range"
            ),
        })
    return out


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# Archive Harvest Release Fit v2.1",
        "",
        "Scope: recorded replay/CSV only; no FlightSim/DCGame launch.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        f"Source target: `{summary['source_ref']}` -> `{summary['source_sha']}`.",
        "",
        "## Step 1 Census",
        "",
        "| flight_id | approaches | FULL depth | est. rows | status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in summary["census"]:
        lines.append(
            f"| `{row['flight_id']}` | {row['approaches']} | {fmt(row['full_depth_m'])} | "
            f"{row['est_rows']} | {row['status']} |"
        )
    lines.extend([
        "",
        f"Census verdict: `{summary['census_verdict']}`.",
        "",
        "## Census Diagnostics",
        "",
        "| flight_id | full any <3.5 | full e_z ok <3.5 | side certified | row-only side | reason |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for row in summary.get("census_diagnostics", []):
        lines.append(
            f"| `{row['flight_id']}` | {row['full_certified_below_3p5_any']} | "
            f"{row['full_ok_below_3p5']} | {row['side_pair_certified']} | "
            f"{row['side_pair_row_only']} | `{row['failure_reason']}` |"
        )
    if summary.get("stopped_after_census"):
        lines.append("")
        lines.append("Stopped before fitting because fewer than six independent approaches were available.")
    else:
        rel = summary["release"]
        lines.extend([
            "",
            "## Step 3 Release Fit v2.1",
            "",
            "| n_flights | n_clusters | n_rows | point sigma_a | profile U95 | bootstrap U95 | U95 release | sigma_0 | pseudo sigma_0 | max age | verdict |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
            f"| {rel['n_flights']} | {rel['n_clusters']} | {rel['n_rows']} | "
            f"{fmt(rel['point_sigma_a_mps2'])} | {fmt(rel['profile_u95_sigma_a_mps2'])} | "
            f"{fmt(rel['cluster_bootstrap_u95_sigma_a_mps2'])} | {fmt(rel['u95_release_sigma_a_mps2'])} | "
            f"{fmt(rel['sigma_0_mps'])} | {fmt(rel['pseudo_sigma_0_mps'])} | "
            f"`{rel['max_validated_age']}` | `{rel['verdict']}` |",
            "",
            f"Flat-in-sigma_a: `{rel['profile_nearly_flat']}`. LOAO gate push: `{rel['loao_pushes_over_gate']}`.",
            "",
            "## Step 2 Mechanism Test",
            "",
            "| approach | auth median | v_latch median | predicted b0 | fitted b0 | pred-fit | rows |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for row in summary["cluster_mechanism"]:
            lines.append(
                f"| `{row['approach_id']}` | {fmt(row['auth_at_latch_median'])} | "
                f"{fmt(row['v_latch_median_mps'])} | {fmt(row['predicted_b0_median_mps'])} | "
                f"{fmt(row['fitted_b0_mps'])} | {fmt(row['b0_pred_minus_fit_mps'])} | "
                f"{row['sample_rows']} |"
            )
        lines.extend([
            "",
            "## Step 4 P4 Clause (d)",
            "",
            f"Lost F4 accepted-FULL rows: `{summary['p4_lost_rows']}`. "
            "The existing P4 artifact lacks raw reject-stage/range fields, so this artifact reports the row-level loss and marks the missing range-stage fields explicitly.",
            "",
            "## Step 5 R26-2/3 Formal Close Map",
            "",
            "- Constrained robust fit + boundary-aware U95: `release_fit.csv`, `profile_likelihood.csv`, `cluster_bootstrap.csv`.",
            "- Cluster bootstrap and LOAO sensitivity: `cluster_bootstrap.csv`, `loao_sensitivity.csv`.",
            "- Mean/regime kill tables: `mean_fit.csv`, `command_regimes.csv`, `cluster_mechanism.csv`.",
            "- Pseudo floor: `pseudo_release_fit.csv`, `pseudo_samples.csv`.",
            "- Cluster-balanced coverage/max age/model-form fallback: `cluster_balanced_coverage.csv`, `fallback_monotone_bound.csv`.",
            "- P4(d): `p4_f4_lost_full_diff.csv`.",
        ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ref", default="7a51b09")
    parser.add_argument("--census-only", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    assert_mock_safe()
    head, head_short = git_head()
    src_sha, src_short = source_commit(args.source_ref)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir.resolve() if args.out_dir else ROOT / "tuning" / f"{OUT_PREFIX}-{src_short}-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"), [])
    features, metas, approaches = run_archive_replays(params)
    write_csv(out_dir / "features_archive.csv", features)
    write_csv(out_dir / "flight_meta.csv", metas)
    write_csv(out_dir / "approaches.csv", approaches)
    diag = census_diagnostics(features, metas, approaches)
    write_csv(out_dir / "census_diagnostics.csv", diag)

    census_by_flight = []
    for meta in metas:
        apps = [a for a in approaches if a["flight_id"] == meta["flight_id"]]
        census_by_flight.append({
            "flight": meta["flight"],
            "flight_id": meta["flight_id"],
            "approaches": len(apps),
            "full_depth_m": min([float(a["full_depth_m"]) for a in apps], default=""),
            "est_rows": sum(int(a["est_rows"]) for a in apps),
            "status": "OK" if apps else "NO_APPROACH",
        })
    write_csv(out_dir / "census.csv", census_by_flight)
    census_ok = len(approaches) >= MIN_RELEASE_CLUSTERS
    summary = {
        "repo_head": head,
        "source_ref": args.source_ref,
        "source_sha": src_sha,
        "census": census_by_flight,
        "census_diagnostics": diag,
        "census_verdict": "PASS" if census_ok else "STOP_ARCHIVE_LT_6_APPROACHES",
        "stopped_after_census": bool(args.census_only or not census_ok),
    }
    if args.census_only or not census_ok:
        write_report(out_dir, summary)
        print(f"[archive-harvest] census={out_dir / 'census.csv'} approaches={len(approaches)}")
        print(f"[archive-harvest] report={out_dir / 'summary.md'}")
        return 0 if census_ok else 2

    samples, cluster_mechanism = build_forced_withhold_rows(features, approaches)
    write_csv(out_dir / "forced_withhold_samples.csv", samples)
    write_csv(out_dir / "cluster_mechanism.csv", cluster_mechanism)
    fit = fit_release(samples)
    boot = cluster_bootstrap(samples)
    loao = loao_sensitivity(samples)
    flight_loao = flight_loao_sensitivity(samples)
    reg = regime_rows(samples)
    cov, max_age, monotone = cluster_balanced_coverage(samples, fit)
    fallback = fallback_bound(samples, fit)
    ps = pseudo_samples(features, approaches)
    pfit = fit_release(ps) if ps else {}
    p4 = p4_acceptance_diff()

    u95_release = max(float(fit["profile_u95_sigma_a_mps2"]), float(boot["cluster_bootstrap_u95_sigma_a_mps2"]))
    loao_push = any(str(r.get("pushes_over_gate")) == "True" or r.get("pushes_over_gate") is True for r in loao)
    flat = bool(fit["profile_nearly_flat"])
    if flat:
        verdict = "HOLD, PARAMETER-NOT-IDENTIFIED"
    elif loao_push:
        verdict = "HOLD, DATA-INSUFFICIENT"
    elif u95_release <= SIGMA_A_GATE:
        verdict = "RELEASE-READY (statistics side)"
    elif float(fit["sigma_a_mps2"]) <= SIGMA_A_GATE:
        verdict = "HOLD, DATA-INSUFFICIENT"
    else:
        verdict = "FAIL"
    release_row = {
        "n_flights": len({s["flight_id"] for s in samples}),
        "n_clusters": len({s["cluster_id"] for s in samples}),
        "n_rows": len(samples),
        "point_sigma_a_mps2": fit["sigma_a_mps2"],
        "profile_u95_sigma_a_mps2": fit["profile_u95_sigma_a_mps2"],
        "cluster_bootstrap_u95_sigma_a_mps2": boot["cluster_bootstrap_u95_sigma_a_mps2"],
        "u95_release_sigma_a_mps2": u95_release,
        "sigma_0_mps": fit["sigma_0_mps"],
        "pseudo_sigma_0_mps": pfit.get("sigma_0_mps", ""),
        "pseudo_sigma_a_mps2": pfit.get("sigma_a_mps2", ""),
        "profile_nearly_flat": fit["profile_nearly_flat"],
        "loao_pushes_over_gate": loao_push,
        "coverage_monotone_degrade": monotone,
        "max_validated_age": max_age,
        "verdict": verdict,
    }
    write_csv(out_dir / "release_fit.csv", [release_row])
    write_csv(out_dir / "mean_fit.csv", [{k: fit[k] for k in ["b0", "b1", "mean_fit_residual_rms_mps"]} | boot])
    write_csv(out_dir / "cluster_bootstrap.csv", [boot])
    write_csv(out_dir / "profile_likelihood.csv", [{k: fit[k] for k in ["profile_u95_sigma_a_mps2", "profile_threshold_nll", "profile_nearly_flat", "profile_loss_min", "profile_loss_max"]}])
    write_csv(out_dir / "loao_sensitivity.csv", loao)
    write_csv(out_dir / "flight_loao_sensitivity.csv", flight_loao)
    write_csv(out_dir / "command_regimes.csv", reg)
    write_csv(out_dir / "cluster_balanced_coverage.csv", cov)
    write_csv(out_dir / "fallback_monotone_bound.csv", fallback)
    write_csv(out_dir / "pseudo_samples.csv", ps)
    write_csv(out_dir / "pseudo_release_fit.csv", [pfit] if pfit else [])
    write_csv(out_dir / "p4_f4_lost_full_diff.csv", p4)
    summary.update({
        "stopped_after_census": False,
        "release": release_row,
        "cluster_mechanism": cluster_mechanism,
        "p4_lost_rows": len(p4),
    })
    write_report(out_dir, summary)
    print(f"[archive-harvest] report={out_dir / 'summary.md'}")
    print(f"[archive-harvest] verdict={verdict} clusters={release_row['n_clusters']} rows={release_row['n_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
