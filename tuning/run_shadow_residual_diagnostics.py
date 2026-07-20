"""Shadow residual fit + wrong-sign disclosure diagnostics.

QA & MOCK-TUNER scope: committed CSV artifacts only. This script refuses to
run if the simulator lock or process is visible, and writes only under tuning/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize, minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from archive_harvest_release_fit_v21 import (  # noqa: E402
    AGE_BINS,
    BOOTSTRAP_N,
    BOOTSTRAP_SEED,
    NU,
    SIGMA_A_GATE,
    cluster_balanced_coverage,
    fallback_bound,
    fit_mean_values,
    percentile,
    rms,
)
from run_l1_perception_replay import assert_mock_safe  # noqa: E402


TASK_A_DIR = ROOT / "tuning" / "taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z"
TASK_B_DIR = ROOT / "tuning" / "taskB-five-cluster-DIAGNOSTIC-bb0dbcf-20260720T183318Z"
OUT_PREFIX = "shadow-residual-DIAGNOSTIC"
CORRIDOR_M = 0.30


def git_head() -> tuple[str, str]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return head, head[:7]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def era_family(era: str) -> str:
    if era.startswith("phase5"):
        return "phase5"
    if era.startswith("phase6"):
        return "phase6"
    if era.startswith("phase7"):
        return "phase7"
    if era.startswith("phase4"):
        return "phase4"
    if era.startswith("phase3"):
        return "phase3"
    return era or "unknown"


def one_row(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    return rows[0] if rows else {}


def sample_arrays(samples: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    ages = np.asarray([float(r["age_s"]) for r in samples], dtype=float)
    residuals = np.asarray([float(r["r_v_mps"]) for r in samples], dtype=float)
    return ages, residuals


def fit_mean_fast(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"b0": "", "b1": "", "mean_fit_residual_rms_mps": ""}
    ages, residuals = sample_arrays(samples)
    xm = float(np.mean(ages))
    ym = float(np.mean(residuals))
    den = float(np.sum((ages - xm) ** 2))
    b1 = float(np.sum((ages - xm) * (residuals - ym)) / den) if den > 1e-18 else 0.0
    b0 = ym - b1 * xm
    centered = residuals - (b0 + b1 * ages)
    return {"b0": b0, "b1": b1, "mean_fit_residual_rms_mps": rms(centered.tolist())}


def student_nll_fast(ages: np.ndarray, residuals: np.ndarray,
                     b0: float, b1: float, sigma0: float, sigmaa: float) -> float:
    err = residuals - (b0 + b1 * ages)
    scale = np.sqrt(np.maximum(sigma0 * sigma0 + (sigmaa * ages) ** 2, 1e-12))
    z = err / scale
    return float(np.sum(np.log(scale) + 0.5 * (NU + 1.0) * np.log1p((z * z) / NU)))


def fit_scale_fast(samples: list[dict[str, Any]], b0: float, b1: float) -> dict[str, Any]:
    ages, residuals = sample_arrays(samples)
    centered = residuals - (b0 + b1 * ages)
    base = float(math.sqrt(float(np.mean(centered * centered)))) if len(centered) else 0.02

    def obj(x: np.ndarray) -> float:
        return student_nll_fast(ages, residuals, b0, b1, float(x[0]), float(x[1]))

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


def profile_u95_fast(samples: list[dict[str, Any]], b0: float, b1: float,
                     best_nll: float) -> dict[str, Any]:
    ages, residuals = sample_arrays(samples)
    threshold = best_nll + 1.352771727047702

    def prof_loss(sa: float) -> float:
        res = minimize_scalar(
            lambda s0: student_nll_fast(ages, residuals, b0, b1, max(float(s0), 1e-6), sa),
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


def fit_release_fast(samples: list[dict[str, Any]]) -> dict[str, Any]:
    mean = fit_mean_fast(samples)
    b0 = float(mean["b0"] or 0.0)
    b1 = float(mean["b1"] or 0.0)
    scale = fit_scale_fast(samples, b0, b1)
    prof = profile_u95_fast(samples, b0, b1, scale["nll"])
    return {**mean, **scale, **prof}


def cluster_bootstrap_fast(samples: list[dict[str, Any]], n_boot: int = BOOTSTRAP_N) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        groups[str(row["cluster_id"])].append(row)
    ids = sorted(groups)
    rng = __import__("random").Random(BOOTSTRAP_SEED)
    vals: list[float] = []
    b0s: list[float] = []
    b1s: list[float] = []
    for _ in range(n_boot):
        draw: list[dict[str, Any]] = []
        for _cid in ids:
            draw.extend(groups[rng.choice(ids)])
        fit = fit_release_fast(draw)
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


def loao_sensitivity_fast(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    ids = sorted({str(r["cluster_id"]) for r in samples})
    for cid in ids:
        train = [r for r in samples if r["cluster_id"] != cid]
        fit = fit_release_fast(train)
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


def flight_loao_sensitivity_fast(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    ids = sorted({str(r["flight_id"]) for r in samples})
    for fid in ids:
        train = [r for r in samples if r["flight_id"] != fid]
        fit = fit_release_fast(train)
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


def shadow_samples(old_samples: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in old_samples:
        v_ref = fnum(row.get("v_ref_oracle_mps"))
        v_shadow = fnum(row.get("v_shadow_hold_mps"))
        if v_ref is None or v_shadow is None:
            continue
        rv = v_ref - v_shadow
        rec = dict(row)
        rec.update({
            "diagnostic_only": True,
            "anchor_policy": "shadow_unattenuated_anchor",
            "r_v_mps": rv,
            "rv2_m2ps2": rv * rv,
            "v_hold_mps": v_shadow,
            "v_anchor_policy_hold_mps": v_shadow,
            "residual_sign_convention": (
                "DIAGNOSTIC shadow: r_v = v_ref_oracle - "
                "(v_latch_true + feed_forward)"
            ),
        })
        out.append(rec)
    return out


def per_cluster_b0(old_samples: list[dict[str, str]],
                   new_samples: list[dict[str, Any]],
                   clusters: list[dict[str, str]]) -> list[dict[str, Any]]:
    old_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    new_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in old_samples:
        old_by[row["cluster_id"]].append(row)
    for row in new_samples:
        new_by[row["cluster_id"]].append(row)
    cluster_meta = {row["cluster_id"]: row for row in clusters}
    rows: list[dict[str, Any]] = []
    for cid in sorted(cluster_meta):
        old_group = old_by.get(cid, [])
        new_group = new_by.get(cid, [])
        old_b0, old_b1 = fit_mean_values(old_group)
        new_b0, new_b1 = fit_mean_values(new_group)
        auths = [fnum(r.get("auth_at_latch")) for r in old_group]
        v_latch = [fnum(r.get("v_latch_true_mps")) for r in old_group]
        auth_vals = [v for v in auths if v is not None]
        v_vals = [v for v in v_latch if v is not None]
        meta = cluster_meta[cid]
        rows.append({
            "diagnostic_only": True,
            "cluster_id": cid,
            "flight_id": meta.get("flight_id", ""),
            "flight": meta.get("flight", ""),
            "fixture_dir": meta.get("fixture_dir", ""),
            "era": meta.get("era", ""),
            "recording_regime": meta.get("recording_regime", ""),
            "n_rows_old": len(old_group),
            "n_rows_shadow": len(new_group),
            "auth_at_latch_median": statistics.median(auth_vals) if auth_vals else "",
            "v_latch_median_mps": statistics.median(v_vals) if v_vals else "",
            "b0_old_mps": old_b0 if old_b0 is not None else "",
            "b1_old_mps_per_s": old_b1 if old_b1 is not None else "",
            "b0_new_mps": new_b0 if new_b0 is not None else "",
            "b1_new_mps_per_s": new_b1 if new_b1 is not None else "",
            "b0_old_minus_new_mps": (
                old_b0 - new_b0
                if old_b0 is not None and new_b0 is not None else ""
            ),
        })
    return rows


def release_summary_rows(old_release: dict[str, str], shadow_fit: dict[str, Any],
                         shadow_boot: dict[str, Any], max_age: str,
                         monotone: bool, n_flights: int, n_clusters: int,
                         n_rows: int) -> list[dict[str, Any]]:
    shadow_u95 = max(
        float(shadow_fit["profile_u95_sigma_a_mps2"]),
        float(shadow_boot["cluster_bootstrap_u95_sigma_a_mps2"]),
    )
    return [
        {
            "anchor_policy": "old_attenuated_anchor",
            "diagnostic_only": True,
            "n_flights": old_release.get("n_flights", ""),
            "n_clusters": old_release.get("n_clusters", ""),
            "n_rows": old_release.get("n_rows", ""),
            "point_sigma_a_mps2": old_release.get("point_sigma_a_mps2", ""),
            "profile_u95_sigma_a_mps2": old_release.get("profile_u95_sigma_a_mps2", ""),
            "cluster_bootstrap_u95_sigma_a_mps2": old_release.get("cluster_bootstrap_u95_sigma_a_mps2", ""),
            "u95_release_sigma_a_mps2": old_release.get("u95_release_sigma_a_mps2", ""),
            "sigma_0_mps": old_release.get("sigma_0_mps", ""),
            "profile_nearly_flat": old_release.get("profile_nearly_flat", ""),
            "coverage_monotone_degrade": old_release.get("coverage_monotone_degrade", ""),
            "max_validated_age": old_release.get("max_validated_age", ""),
            "verdict": old_release.get("verdict", ""),
            "note": "diagnostic side-by-side read of old Task A numbers; RESPONSE47 marks this inadmissible as release physics",
        },
        {
            "anchor_policy": "shadow_unattenuated_anchor",
            "diagnostic_only": True,
            "n_flights": n_flights,
            "n_clusters": n_clusters,
            "n_rows": n_rows,
            "point_sigma_a_mps2": shadow_fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": shadow_fit["profile_u95_sigma_a_mps2"],
            "cluster_bootstrap_u95_sigma_a_mps2": shadow_boot["cluster_bootstrap_u95_sigma_a_mps2"],
            "u95_release_sigma_a_mps2": shadow_u95,
            "sigma_0_mps": shadow_fit["sigma_0_mps"],
            "profile_nearly_flat": shadow_fit["profile_nearly_flat"],
            "coverage_monotone_degrade": monotone,
            "max_validated_age": max_age,
            "verdict": (
                "DIAGNOSTIC_ONLY_SHADOW_COLLAPSE"
                if shadow_u95 <= SIGMA_A_GATE else
                "DIAGNOSTIC_ONLY_SHADOW_STILL_OVER_GATE"
            ),
            "note": "diagnostic shadow residuals only; release read must be re-earned on the shipping build",
        },
    ]


def join_old_shadow_by_key(old_rows: list[dict[str, str]],
                           shadow_rows: list[dict[str, Any]],
                           key: str,
                           prefix: str) -> list[dict[str, Any]]:
    old_by = {row[key]: row for row in old_rows if row.get(key)}
    out = []
    for row in shadow_rows:
        oid = row.get(key, "")
        old = old_by.get(oid, {})
        rec = {key: oid}
        for k, v in old.items():
            if k != key:
                rec[f"old_{k}"] = v
        for k, v in row.items():
            if k != key:
                rec[f"{prefix}_{k}"] = v
        out.append(rec)
    return out


def sign_opposed(cmd: float | None, reference: float | None,
                 cmd_deadband: float, ref_deadband: float) -> bool:
    if cmd is None or reference is None:
        return False
    if abs(cmd) <= cmd_deadband or abs(reference) <= ref_deadband:
        return False
    return cmd * reference < 0.0


def count_step_beyond_slew(rows: list[dict[str, str]], cmd_col: str,
                           threshold: float = 0.08) -> int:
    prev: float | None = None
    count = 0
    for row in rows:
        cmd = fnum(row.get(cmd_col))
        if prev is not None and cmd is not None and abs(cmd - prev) > threshold:
            count += 1
        if cmd is not None:
            prev = cmd
    return count


def wrong_sign_disclosure(task_b_dir: Path, out_dir: Path) -> dict[str, Any]:
    rows = read_csv(task_b_dir / "DIAGNOSTIC_r26_1_anchor_trial_rows.csv")
    restamp = one_row(task_b_dir / "DIAGNOSTIC_r26_1_restamp_verdict.csv")
    term_rows = [r for r in rows if r.get("shadow_owner") == "term"]

    legacy_flagged = []
    for idx, row in enumerate(term_rows):
        cmd = fnum(row.get("terminal_vz_up_mps"))
        raw_e = fnum(row.get("e_meas"))
        flagged = (
            cmd is not None and raw_e is not None
            and abs(raw_e) > 0.03
            and cmd * raw_e < -1e-6
        )
        if flagged:
            legacy_flagged.append({
                "term_row_index": idx,
                "trial": row.get("trial", ""),
                "frame_id": row.get("frame_id", ""),
                "range_z_m": row.get("range_z_m", ""),
                "terminal_vz_up_mps": row.get("terminal_vz_up_mps", ""),
                "e_meas": row.get("e_meas", ""),
                "applied_e_z": row.get("applied_e_z", ""),
                "truth_vz_up_mps": row.get("truth_vz_up_mps", ""),
                "formula": "cmd=terminal_vz_up_mps; raw_e=e_meas; abs(raw_e)>0.03; cmd*raw_e<-1e-6",
            })
    write_csv(out_dir / "DIAGNOSTIC_wrong_sign_rows_legacy_formula.csv", legacy_flagged)

    legal = int(restamp.get("legal_trial_count") or 0)
    owner_side = int(restamp.get("owner_term_side_rows") or 0)
    side_caps = int(restamp.get("side_shadow_capture_rows") or 0)
    max_score = fnum(restamp.get("max_admission_score"))
    phase_changes = int(restamp.get("phase_changed_rows") or 0)
    base_pass = bool(
        legal and owner_side > 0 and side_caps > 0
        and max_score is not None and max_score <= CORRIDOR_M
        and phase_changes == 0
    )

    score_defs = [
        {
            "definition": "legacy_harness_raw_e_meas",
            "path": "old_actual_applied",
            "cmd_col": "terminal_vz_up_mps",
            "ref_col": "e_meas",
            "cmd_deadband": 0.0,
            "ref_deadband": 0.03,
            "extra_condition": "cmd*e_meas < -1e-6",
            "diagnostic_only": True,
        },
        {
            "definition": "needed_correction_deadband_0p02",
            "path": "old_actual_applied",
            "cmd_col": "terminal_vz_up_mps",
            "ref_col": "applied_e_z",
            "cmd_deadband": 0.02,
            "ref_deadband": 0.02,
            "extra_condition": "cmd*applied_e_z < 0",
            "diagnostic_only": True,
        },
        {
            "definition": "needed_correction_deadband_0p02",
            "path": "old_goal_forecast",
            "cmd_col": "shadow_vz_cmd_old_mps",
            "ref_col": "applied_e_z",
            "cmd_deadband": 0.02,
            "ref_deadband": 0.02,
            "extra_condition": "cmd*applied_e_z < 0",
            "diagnostic_only": True,
        },
        {
            "definition": "needed_correction_deadband_0p02",
            "path": "new_shadow_goal_forecast",
            "cmd_col": "shadow_vz_cmd_new_mps",
            "ref_col": "applied_e_z",
            "cmd_deadband": 0.02,
            "ref_deadband": 0.02,
            "extra_condition": "cmd*applied_e_z < 0",
            "diagnostic_only": True,
        },
        {
            "definition": "current_velocity_context_deadband_0p02",
            "path": "old_actual_applied",
            "cmd_col": "terminal_vz_up_mps",
            "ref_col": "truth_vz_up_mps",
            "cmd_deadband": 0.02,
            "ref_deadband": 0.02,
            "extra_condition": "cmd*truth_vz_up_mps < 0",
            "diagnostic_only": True,
        },
        {
            "definition": "current_velocity_context_deadband_0p02",
            "path": "new_shadow_goal_forecast",
            "cmd_col": "shadow_vz_cmd_new_mps",
            "ref_col": "truth_vz_up_mps",
            "cmd_deadband": 0.02,
            "ref_deadband": 0.02,
            "extra_condition": "cmd*truth_vz_up_mps < 0",
            "diagnostic_only": True,
        },
    ]
    score_rows = []
    for spec in score_defs:
        valid = 0
        active = 0
        violations = 0
        for row in term_rows:
            cmd = fnum(row.get(spec["cmd_col"]))
            ref = fnum(row.get(spec["ref_col"]))
            if cmd is None or ref is None:
                continue
            valid += 1
            if abs(cmd) > float(spec["cmd_deadband"]) and abs(ref) > float(spec["ref_deadband"]):
                active += 1
            if spec["definition"] == "legacy_harness_raw_e_meas":
                if abs(ref) > 0.03 and cmd * ref < -1e-6:
                    violations += 1
            elif sign_opposed(cmd, ref, float(spec["cmd_deadband"]), float(spec["ref_deadband"])):
                violations += 1
        step_rows = count_step_beyond_slew(term_rows, str(spec["cmd_col"]))
        score_rows.append({
            "definition": spec["definition"],
            "path": spec["path"],
            "diagnostic_only": spec["diagnostic_only"],
            "cmd_col": spec["cmd_col"],
            "reference_col": spec["ref_col"],
            "cmd_deadband": spec["cmd_deadband"],
            "reference_deadband": spec["ref_deadband"],
            "extra_condition": spec["extra_condition"],
            "term_owner_rows": len(term_rows),
            "valid_rows": valid,
            "active_after_deadband_rows": active,
            "wrong_sign_rows": violations,
            "command_step_beyond_slew_rows_for_path": step_rows,
            "base_liveness_pass": base_pass,
            "verdict_under_definition": (
                "PASS" if base_pass and violations == 0 and step_rows == 0 else "FAIL_OR_HELD"
            ),
            "verdict_note": (
                "QA disclosure only; channel ruling owns whether this definition changes the restamp verdict"
            ),
        })
    write_csv(out_dir / "DIAGNOSTIC_wrong_sign_scorecard.csv", score_rows)

    formula_md = [
        "# DIAGNOSTIC Wrong-Sign Formula Disclosure",
        "",
        "Scope: CSV-only restamp disclosure. This file does not change the channel verdict.",
        "",
        "## Legacy Formula That Produced `wrong_sign_command_rows=28`",
        "",
        "Rows considered: `DIAGNOSTIC_r26_1_anchor_trial_rows.csv` rows where `shadow_owner == 'term'`.",
        "",
        "Columns:",
        "- `cmd = terminal_vz_up_mps`",
        "- `raw_e = e_meas`",
        "",
        "Predicate:",
        "",
        "```python",
        "cmd is not None and raw_e is not None and abs(raw_e) > 0.03 and cmd * raw_e < -1e-6",
        "```",
        "",
        f"Recomputed count: `{len(legacy_flagged)}`.",
        "",
        "## Re-score Requested By RESPONSE47",
        "",
        "Needed-correction score uses `applied_e_z` as the correction actually fed to the terminal owner, with `abs(cmd)>0.02`, `abs(applied_e_z)>0.02`, and `cmd*applied_e_z < 0` as opposition.",
        "",
        "See `DIAGNOSTIC_wrong_sign_scorecard.csv` for old actual, old forecast, and new shadow forecast rows.",
        "",
    ]
    (out_dir / "DIAGNOSTIC_wrong_sign_formula.md").write_text("\n".join(formula_md), encoding="utf-8")
    return {
        "legacy_wrong_sign_rows": len(legacy_flagged),
        "needed_correction_old_actual_wrong_sign_rows": next(
            r["wrong_sign_rows"] for r in score_rows
            if r["definition"] == "needed_correction_deadband_0p02"
            and r["path"] == "old_actual_applied"
        ),
        "needed_correction_new_shadow_wrong_sign_rows": next(
            r["wrong_sign_rows"] for r in score_rows
            if r["definition"] == "needed_correction_deadband_0p02"
            and r["path"] == "new_shadow_goal_forecast"
        ),
        "base_liveness_pass": base_pass,
    }


def y_eligible_and_signature(task_a_dir: Path, out_dir: Path) -> dict[str, Any]:
    rows = read_csv(task_a_dir / "censored_approach_diagnostics.csv")
    detailed: list[dict[str, Any]] = []
    for row in rows:
        y = truthy(row.get("cluster_ok")) or row.get("failure_reason") == "OK"
        full_close_any = fnum(row.get("full_certified_below_3p5_any")) or 0.0
        full_dies_gt4p5 = row.get("failure_reason") == "NO_CLOSE_FEATURE_EPOCH_LE4P5"
        never_recert_le3p5 = full_close_any == 0.0
        signature = full_dies_gt4p5 and never_recert_le3p5
        detailed.append({
            "flight": row.get("flight", ""),
            "flight_id": row.get("flight_id", ""),
            "approach_id": row.get("approach_id", ""),
            "fixture_dir": row.get("fixture_dir", ""),
            "era": row.get("era", ""),
            "era_family": era_family(row.get("era", "")),
            "recording_regime": row.get("recording_regime", ""),
            "Y_eligible": y,
            "failure_reason": row.get("failure_reason", ""),
            "frozen_compound_signature_positive": signature,
            "full_dies_gt4p5_proxy": full_dies_gt4p5,
            "never_recertifies_le3p5": never_recert_le3p5,
            "definition": (
                "frozen RESPONSE42/44 proxy: no current-perception close feature epoch <=4.5m "
                "AND zero certified FULL <=3.5m; thresholds unchanged"
            ),
        })
    write_csv(out_dir / "DIAGNOSTIC_approach_eligibility_signature_rows.csv", detailed)

    era_rows = []
    for era in sorted({r["era"] for r in detailed}):
        group = [r for r in detailed if r["era"] == era]
        y_count = sum(1 for r in group if r["Y_eligible"])
        era_rows.append({
            "era": era,
            "era_family": era_family(era),
            "approaches": len(group),
            "Y_eligible": y_count,
            "Y_ineligible": len(group) - y_count,
            "Y_eligible_rate": y_count / len(group) if group else "",
            "signature_positive": sum(1 for r in group if r["frozen_compound_signature_positive"]),
            "signature_negative": sum(1 for r in group if not r["frozen_compound_signature_positive"]),
        })
    write_csv(out_dir / "DIAGNOSTIC_Y_eligible_by_era.csv", era_rows)

    sig_rows = []
    for signature in [False, True]:
        for y in [False, True]:
            group = [r for r in detailed if r["frozen_compound_signature_positive"] == signature and r["Y_eligible"] == y]
            sig_rows.append({
                "frozen_compound_signature_positive": signature,
                "Y_eligible": y,
                "approaches": len(group),
                "eras": ";".join(sorted({r["era"] for r in group})),
            })
    write_csv(out_dir / "DIAGNOSTIC_frozen_compound_signature_2x2.csv", sig_rows)

    by_era_rows = []
    for era in sorted({r["era"] for r in detailed}):
        for signature in [False, True]:
            for y in [False, True]:
                group = [
                    r for r in detailed
                    if r["era"] == era
                    and r["frozen_compound_signature_positive"] == signature
                    and r["Y_eligible"] == y
                ]
                by_era_rows.append({
                    "era": era,
                    "era_family": era_family(era),
                    "frozen_compound_signature_positive": signature,
                    "Y_eligible": y,
                    "approaches": len(group),
                })
    write_csv(out_dir / "DIAGNOSTIC_frozen_compound_signature_2x2_by_era.csv", by_era_rows)

    return {
        "approaches": len(detailed),
        "Y_eligible": sum(1 for r in detailed if r["Y_eligible"]),
        "signature_positive": sum(1 for r in detailed if r["frozen_compound_signature_positive"]),
    }


def run(args: argparse.Namespace) -> Path:
    assert_mock_safe()
    head, short = git_head()
    task_a = args.task_a_dir.resolve()
    task_b = args.task_b_dir.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"{OUT_PREFIX}-{short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    old_samples = read_csv(task_a / "forced_withhold_samples.csv")
    clusters = read_csv(task_a / "expanded_census_clusters.csv")
    new_samples = shadow_samples(old_samples)
    write_csv(out_dir / "DIAGNOSTIC_shadow_forced_withhold_samples.csv", new_samples)

    shadow_fit = fit_release_fast(new_samples)
    print("fit_release_fast complete", flush=True)
    shadow_boot = cluster_bootstrap_fast(new_samples)
    print("cluster_bootstrap_fast complete", flush=True)
    shadow_loao = loao_sensitivity_fast(new_samples)
    print("loao_sensitivity_fast complete", flush=True)
    shadow_flight_loao = flight_loao_sensitivity_fast(new_samples)
    print("flight_loao_sensitivity_fast complete", flush=True)
    coverage, max_age, monotone = cluster_balanced_coverage(new_samples, shadow_fit)
    fallback = fallback_bound(new_samples, shadow_fit)
    b0_rows = per_cluster_b0(old_samples, new_samples, clusters)

    n_flights = len({r["flight_id"] for r in new_samples})
    n_clusters = len({r["cluster_id"] for r in new_samples})
    old_release = one_row(task_a / "release_fit.csv")
    release_rows = release_summary_rows(
        old_release,
        shadow_fit,
        shadow_boot,
        max_age,
        monotone,
        n_flights,
        n_clusters,
        len(new_samples),
    )

    write_csv(out_dir / "DIAGNOSTIC_shadow_release_fit.csv", [{
        "diagnostic_only": True,
        "n_flights": n_flights,
        "n_clusters": n_clusters,
        "n_rows": len(new_samples),
        "point_sigma_a_mps2": shadow_fit["sigma_a_mps2"],
        "profile_u95_sigma_a_mps2": shadow_fit["profile_u95_sigma_a_mps2"],
        "cluster_bootstrap_u95_sigma_a_mps2": shadow_boot["cluster_bootstrap_u95_sigma_a_mps2"],
        "u95_release_sigma_a_mps2": max(
            float(shadow_fit["profile_u95_sigma_a_mps2"]),
            float(shadow_boot["cluster_bootstrap_u95_sigma_a_mps2"]),
        ),
        "sigma_0_mps": shadow_fit["sigma_0_mps"],
        "profile_nearly_flat": shadow_fit["profile_nearly_flat"],
        "max_validated_age": max_age,
        "coverage_monotone_degrade": monotone,
        "label": "DIAGNOSTIC_SHADOW_RESIDUALS_NOT_RELEASE",
    }])
    write_csv(out_dir / "DIAGNOSTIC_shadow_cluster_bootstrap.csv", [shadow_boot])
    write_csv(out_dir / "DIAGNOSTIC_shadow_loao_sensitivity.csv", shadow_loao)
    write_csv(out_dir / "DIAGNOSTIC_shadow_flight_loao_sensitivity.csv", shadow_flight_loao)
    write_csv(out_dir / "DIAGNOSTIC_shadow_cluster_balanced_coverage.csv", coverage)
    write_csv(out_dir / "DIAGNOSTIC_shadow_fallback_monotone_bound.csv", fallback)
    write_csv(out_dir / "DIAGNOSTIC_shadow_b0_new_per_cluster.csv", b0_rows)
    write_csv(out_dir / "DIAGNOSTIC_old_vs_shadow_release_fit.csv", release_rows)
    write_csv(
        out_dir / "DIAGNOSTIC_old_vs_shadow_loao_sensitivity.csv",
        join_old_shadow_by_key(read_csv(task_a / "loao_sensitivity.csv"), shadow_loao, "left_out_approach", "shadow"),
    )
    write_csv(
        out_dir / "DIAGNOSTIC_old_vs_shadow_flight_loao_sensitivity.csv",
        join_old_shadow_by_key(read_csv(task_a / "flight_loao_sensitivity.csv"), shadow_flight_loao, "left_out_flight_id", "shadow"),
    )
    write_csv(
        out_dir / "DIAGNOSTIC_old_vs_shadow_cluster_balanced_coverage.csv",
        join_old_shadow_by_key(read_csv(task_a / "cluster_balanced_coverage.csv"), coverage, "age_bin", "shadow"),
    )

    wrong = wrong_sign_disclosure(task_b, out_dir)
    ledger = y_eligible_and_signature(task_a, out_dir)

    failure_counts = Counter(r.get("failure_reason", "") for r in read_csv(task_a / "censored_approach_diagnostics.csv"))
    summary = {
        "repo_head": head,
        "task_a_source": str(task_a.relative_to(ROOT)),
        "task_b_source": str(task_b.relative_to(ROOT)),
        "diagnostic_only": True,
        "shadow_fit": {
            "n_flights": n_flights,
            "n_clusters": n_clusters,
            "n_rows": len(new_samples),
            "point_sigma_a_mps2": shadow_fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": shadow_fit["profile_u95_sigma_a_mps2"],
            "cluster_bootstrap_u95_sigma_a_mps2": shadow_boot["cluster_bootstrap_u95_sigma_a_mps2"],
            "u95_release_sigma_a_mps2": max(
                float(shadow_fit["profile_u95_sigma_a_mps2"]),
                float(shadow_boot["cluster_bootstrap_u95_sigma_a_mps2"]),
            ),
            "sigma_0_mps": shadow_fit["sigma_0_mps"],
            "max_validated_age": max_age,
            "coverage_monotone_degrade": monotone,
        },
        "old_path": old_release,
        "wrong_sign": wrong,
        "ledger": {
            **ledger,
            "failure_reason_counts": dict(sorted(failure_counts.items())),
        },
        "artifacts": [
            "DIAGNOSTIC_old_vs_shadow_release_fit.csv",
            "DIAGNOSTIC_shadow_b0_new_per_cluster.csv",
            "DIAGNOSTIC_wrong_sign_formula.md",
            "DIAGNOSTIC_wrong_sign_scorecard.csv",
            "DIAGNOSTIC_Y_eligible_by_era.csv",
            "DIAGNOSTIC_frozen_compound_signature_2x2.csv",
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    old_u95 = old_release.get("u95_release_sigma_a_mps2", "")
    shadow_u95 = summary["shadow_fit"]["u95_release_sigma_a_mps2"]
    lines = [
        "# SHADOW-RESIDUAL FIT + WRONG-SIGN DISCLOSURE",
        "",
        "Scope: DIAGNOSTIC, CSV-only; no FlightSim/DCGame launch.",
        f"Repo HEAD: `{head}`.",
        "",
        "## Shadow Fit",
        "",
        f"- Same clusters: `{n_clusters}`.",
        f"- Same sample count after shadow residual conversion: `{len(new_samples)}`.",
        f"- Shadow point sigma_a: `{shadow_fit['sigma_a_mps2']}`.",
        f"- Shadow profile U95: `{shadow_fit['profile_u95_sigma_a_mps2']}`.",
        f"- Shadow bootstrap U95: `{shadow_boot['cluster_bootstrap_u95_sigma_a_mps2']}`.",
        f"- Shadow conservative U95: `{shadow_u95}`.",
        f"- Old-path conservative U95: `{old_u95}`.",
        f"- Max validated age: `{max_age}`.",
        "",
        "This is not a release claim; RESPONSE47 requires the release read to be re-earned on the shipping repaired build.",
        "",
        "## Wrong-Sign Disclosure",
        "",
        f"- Legacy exact-formula count: `{wrong['legacy_wrong_sign_rows']}`.",
        f"- Needed-correction old actual count: `{wrong['needed_correction_old_actual_wrong_sign_rows']}`.",
        f"- Needed-correction new shadow count: `{wrong['needed_correction_new_shadow_wrong_sign_rows']}`.",
        "",
        "The scorecard reports both definitions side by side. QA does not alter the channel verdict here.",
        "",
        "## Ledger",
        "",
        f"- Approaches examined: `{ledger['approaches']}`.",
        f"- Y_eligible: `{ledger['Y_eligible']}`.",
        f"- Frozen compound-signature positives: `{ledger['signature_positive']}`.",
        "",
        "Primary artifacts: `DIAGNOSTIC_old_vs_shadow_release_fit.csv`, "
        "`DIAGNOSTIC_shadow_b0_new_per_cluster.csv`, "
        "`DIAGNOSTIC_wrong_sign_scorecard.csv`, "
        "`DIAGNOSTIC_Y_eligible_by_era.csv`, and "
        "`DIAGNOSTIC_frozen_compound_signature_2x2.csv`.",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-a-dir", type=Path, default=TASK_A_DIR)
    ap.add_argument("--task-b-dir", type=Path, default=TASK_B_DIR)
    args = ap.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
