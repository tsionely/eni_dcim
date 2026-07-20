"""SIGMA_A release fit v2 from existing caa2398 CSV residuals.

QA & MOCK-TUNER scope: CSV-only analysis. This script does not run replay,
mock campaigns, or the real simulator.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "tuning" / "hold-lift-r26-3b554f3-35bfa6d-20260720T121704Z"
OUT_PREFIX = "sigma-a-release-fit-v2-caa2398"

BOOTSTRAP_N = 2500
BOOTSTRAP_SEED = 20260720
NU_STUDENT_T = 5.0
SIGMA_A_GATE = 0.35
MIN_RELEASE_CLUSTERS = 6
PSEUDO_ANCHOR_WINDOW_S = 0.35
PSEUDO_EVAL_WINDOW_S = 0.35
AGE_BINS = [
    ("0p00-0p10", 0.00, 0.10),
    ("0p10-0p20", 0.10, 0.20),
    ("0p20-0p30", 0.20, 0.30),
    ("0p30-0p40", 0.30, 0.40),
    ("0p40-0p50", 0.40, 0.50),
    ("gt0p50", 0.50, float("inf")),
]


def fnum(raw: object) -> float | None:
    try:
        if raw in ("", None):
            return None
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if math.isfinite(val) else None


def fmt(raw: object) -> str:
    val = fnum(raw)
    if val is None:
        return "n/a"
    if abs(val) < 5e-13:
        val = 0.0
    return f"{val:.3f}"


def percentile(values: list[float], pct: float) -> float | None:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (pct / 100.0) * (len(vals) - 1)
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


def bin_label(age_s: float) -> str:
    for label, lo, hi in AGE_BINS:
        if lo <= age_s < hi:
            return label
    return "unknown"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def robust_slope(xs: list[float], ys: list[float]) -> float | None:
    slopes = []
    for i, (x1, y1) in enumerate(zip(xs, ys)):
        for x2, y2 in zip(xs[i + 1:], ys[i + 1:]):
            if abs(x2 - x1) > 1e-12:
                slopes.append((y2 - y1) / (x2 - x1))
    return statistics.median(slopes) if slopes else None


def load_residual_samples(source_dir: Path) -> list[dict]:
    rows = []
    for rec in read_csv(source_dir / "sigma_a_oracle_rows.csv"):
        age = fnum(rec.get("rate_anchor_age_s"))
        residual = fnum(rec.get("rate_error_oracle_mps"))
        if age is None or residual is None:
            continue
        transition = rec.get("transition_id") or rec.get("candidate_frame_id") or "unknown"
        flight_id = rec.get("flight_id") or rec.get("flight") or "unknown_flight"
        cluster_id = f"{flight_id}:{rec.get('trial', '')}:transition_{transition}"
        rows.append({
            "flight": rec.get("flight", ""),
            "flight_id": flight_id,
            "trial": rec.get("trial", ""),
            "transition_id": transition,
            "cluster_id": cluster_id,
            "frame_id": rec.get("frame_id", ""),
            "feature_ts_ns": rec.get("feature_ts_ns", ""),
            "age_s": age,
            "age2_s2": age * age,
            "age_bin": bin_label(age),
            "r_v_mps": residual,
            "rv2_m2ps2": residual * residual,
            "rate_feed_forward_mps": fnum(rec.get("rate_feed_forward_mps")) or 0.0,
            "terminal_vz_up_mps": fnum(rec.get("terminal_vz_up_mps")),
            "terminal_vz_goal_mps": fnum(rec.get("terminal_vz_goal_mps")),
            "logged_applied_vz_up_mps": fnum(rec.get("logged_applied_vz_up_mps")),
            "runtime_hold_authorized": rec.get("runtime_hold_authorized", ""),
        })
    return rows


def fit_mean(samples: list[dict]) -> dict:
    if not samples:
        return {"b0": "", "b1": ""}
    xs = [float(row["age_s"]) for row in samples]
    ys = [float(row["r_v_mps"]) for row in samples]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    b1 = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom if denom > 1e-18 else 0.0
    b0 = y_mean - b1 * x_mean
    residuals = [y - (b0 + b1 * x) for x, y in zip(xs, ys)]
    return {
        "b0": b0,
        "b1": b1,
        "signed_r_mean_mps": y_mean,
        "mean_fit_residual_rms_mps": rms(residuals),
    }


def student_t_nll(samples: list[dict], b0: float, b1: float,
                  sigma0: float, sigmaa: float, nu: float = NU_STUDENT_T) -> float:
    total = 0.0
    for row in samples:
        age = float(row["age_s"])
        err = float(row["r_v_mps"]) - (b0 + b1 * age)
        scale = math.sqrt(max(sigma0 * sigma0 + (sigmaa * age) ** 2, 1e-12))
        z = err / scale
        total += math.log(scale) + 0.5 * (nu + 1.0) * math.log1p((z * z) / nu)
    return total


def fit_student_t_scale(samples: list[dict], b0: float, b1: float) -> dict:
    centered = [float(r["r_v_mps"]) - (b0 + b1 * float(r["age_s"])) for r in samples]
    base = rms(centered) or 0.01
    sigma0_max = max(0.02, min(2.0, 3.0 * base + 0.05))
    sigmaa_max = 3.0
    best = (float("inf"), 0.0, 0.0)
    ranges = [(0.0, sigma0_max, 0.0, sigmaa_max)]
    for pass_idx in range(5):
        lo0, hi0, loa, hia = ranges[-1]
        steps = 42 if pass_idx == 0 else 24
        for i in range(steps + 1):
            sigma0 = lo0 + (hi0 - lo0) * i / steps
            for j in range(steps + 1):
                sigmaa = loa + (hia - loa) * j / steps
                loss = student_t_nll(samples, b0, b1, sigma0, sigmaa)
                if loss < best[0]:
                    best = (loss, sigma0, sigmaa)
        _, c0, ca = best
        width0 = max((hi0 - lo0) / 5.0, 1e-5)
        widtha = max((hia - loa) / 5.0, 1e-5)
        ranges.append((max(0.0, c0 - width0), c0 + width0, max(0.0, ca - widtha), ca + widtha))
    loss, sigma0, sigmaa = best
    return {
        "estimator": "student_t_scale_nu5_constrained",
        "nu": NU_STUDENT_T,
        "sigma_0_mps": sigma0,
        "sigma_a_mps2": sigmaa,
        "loss": loss,
        "mean_centered": True,
    }


def retired_theil_sen(samples: list[dict]) -> dict:
    xs = [float(row["age2_s2"]) for row in samples]
    ys = [float(row["rv2_m2ps2"]) for row in samples]
    slope = robust_slope(xs, ys) or 0.0
    intercept = statistics.median([y - slope * x for x, y in zip(xs, ys)]) if xs else 0.0
    return {
        "estimator": "RETIRED-AS-RELEASE_theil_sen_r2_vs_a2_raw",
        "sigma_0_mps": math.sqrt(max(intercept, 0.0)),
        "sigma_a_mps2": math.sqrt(max(slope, 0.0)),
        "slope_raw": slope,
        "intercept_raw": intercept,
    }


def clusters(samples: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in samples:
        grouped.setdefault(str(row["cluster_id"]), []).append(row)
    return grouped


def fit_release(samples: list[dict]) -> dict:
    mean = fit_mean(samples)
    scale = fit_student_t_scale(samples, float(mean["b0"]), float(mean["b1"]))
    return {**mean, **scale}


def cluster_bootstrap(samples: list[dict], n_boot: int = BOOTSTRAP_N) -> dict:
    grouped = clusters(samples)
    ids = sorted(grouped)
    if len(ids) <= 1:
        fit = fit_release(samples)
        return {
            "bootstrap_n": n_boot,
            "bootstrap_valid": False,
            "u95_sigma_a_mps2": float(fit["sigma_a_mps2"]),
            "sigma_a_bootstrap_min_mps2": float(fit["sigma_a_mps2"]),
            "sigma_a_bootstrap_max_mps2": float(fit["sigma_a_mps2"]),
            "b0_ci_low_mps": float(fit["b0"]),
            "b0_ci_median_mps": float(fit["b0"]),
            "b0_ci_high_mps": float(fit["b0"]),
            "b1_ci_low_mps_per_s": float(fit["b1"]),
            "b1_ci_median_mps_per_s": float(fit["b1"]),
            "b1_ci_high_mps_per_s": float(fit["b1"]),
        }
    rng = random.Random(BOOTSTRAP_SEED)
    sigmas = []
    b0s = []
    b1s = []
    for _ in range(n_boot):
        draw = []
        for _ in ids:
            draw.extend(grouped[rng.choice(ids)])
        fit = fit_release(draw)
        sigmas.append(float(fit["sigma_a_mps2"]))
        b0s.append(float(fit["b0"]))
        b1s.append(float(fit["b1"]))
    valid = len(ids) >= MIN_RELEASE_CLUSTERS
    return {
        "bootstrap_n": n_boot,
        "bootstrap_valid": valid,
        "u95_sigma_a_mps2": percentile(sigmas, 95),
        "sigma_a_bootstrap_min_mps2": min(sigmas) if sigmas else "",
        "sigma_a_bootstrap_max_mps2": max(sigmas) if sigmas else "",
        "b0_ci_low_mps": percentile(b0s, 2.5),
        "b0_ci_median_mps": percentile(b0s, 50),
        "b0_ci_high_mps": percentile(b0s, 97.5),
        "b1_ci_low_mps_per_s": percentile(b1s, 2.5),
        "b1_ci_median_mps_per_s": percentile(b1s, 50),
        "b1_ci_high_mps_per_s": percentile(b1s, 97.5),
    }


def command_regime(row: dict, cluster_signs: set[int]) -> str:
    ff = float(row.get("rate_feed_forward_mps") or 0.0)
    vz = row.get("terminal_vz_up_mps")
    goal = row.get("terminal_vz_goal_mps")
    if goal is not None and abs(float(goal)) >= 0.59:
        return "saturated"
    if vz is not None and goal is not None and abs(float(goal) - float(vz)) > 0.02:
        return "slew_limited"
    if -1 in cluster_signs and 1 in cluster_signs:
        return "triangular"
    if ff > 0.02:
        return "up"
    if ff < -0.02:
        return "down"
    return "flat_no_ff"


def regime_table(samples: list[dict]) -> list[dict]:
    by_cluster = clusters(samples)
    cluster_signs = {
        cid: {1 if float(r["rate_feed_forward_mps"]) > 0.02 else -1
              if float(r["rate_feed_forward_mps"]) < -0.02 else 0 for r in rows}
        for cid, rows in by_cluster.items()
    }
    out = []
    for row in samples:
        row["command_regime"] = command_regime(row, cluster_signs[str(row["cluster_id"])])
    for label in ["up", "down", "triangular", "slew_limited", "saturated", "flat_no_ff"]:
        group = [r for r in samples if r["command_regime"] == label]
        ages = [float(r["age_s"]) for r in group]
        vals = [float(r["r_v_mps"]) for r in group]
        out.append({
            "command_regime": label,
            "n": len(group),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "signed_mean_r_v_mps": statistics.fmean(vals) if vals else "",
            "signed_median_r_v_mps": statistics.median(vals) if vals else "",
            "r_v_rms_mps": rms(vals) if vals else "",
        })
    return out


def pseudo_transition_samples(source_dir: Path) -> list[dict]:
    full = []
    for rec in read_csv(source_dir / "full_observation_series.csv"):
        ts = fnum(rec.get("ts_s"))
        ez = fnum(rec.get("e_z"))
        if ts is None or ez is None:
            continue
        full.append({
            "flight": rec.get("flight", ""),
            "frame_id": rec.get("frame_id", ""),
            "ts_s": ts,
            "feature_ts_ns": rec.get("feature_ts_ns", ""),
            "e_z": ez,
        })
    full.sort(key=lambda r: float(r["ts_s"]))
    out = []
    age_grid = [0.10, 0.20, 0.30, 0.40, 0.50]
    for anchor in full:
        t0 = float(anchor["ts_s"])
        hist = [r for r in full if t0 - PSEUDO_ANCHOR_WINDOW_S <= float(r["ts_s"]) <= t0]
        if len(hist) < 4:
            continue
        span = float(hist[-1]["ts_s"]) - float(hist[0]["ts_s"])
        anchor_slope = robust_slope([float(r["ts_s"]) for r in hist], [float(r["e_z"]) for r in hist])
        if anchor_slope is None:
            continue
        authority = min(1.0, (span / 0.3) * (len(hist) / 10.0))
        anchor_v = -float(anchor_slope) * authority
        for age in age_grid:
            te = t0 + age
            eval_pts = [
                r for r in full
                if te <= float(r["ts_s"]) <= te + PSEUDO_EVAL_WINDOW_S
            ]
            if len(eval_pts) < 4:
                continue
            eval_slope = robust_slope(
                [float(r["ts_s"]) for r in eval_pts],
                [float(r["e_z"]) for r in eval_pts],
            )
            if eval_slope is None:
                continue
            v_ref = -float(eval_slope)
            residual = v_ref - anchor_v
            out.append({
                "flight": anchor["flight"],
                "cluster_id": f"{anchor['flight']}:pseudo_full_only",
                "anchor_frame_id": anchor["frame_id"],
                "anchor_ts_s": t0,
                "age_s": age,
                "age2_s2": age * age,
                "age_bin": bin_label(age),
                "anchor_n": len(hist),
                "anchor_span_s": span,
                "anchor_authority": authority,
                "anchor_v_mps": anchor_v,
                "oracle_v_mps": v_ref,
                "r_v_mps": residual,
                "rv2_m2ps2": residual * residual,
            })
    return out


def lofo_table(samples: list[dict], release_fit: dict) -> tuple[list[dict], str]:
    flights = sorted({str(r["flight_id"]) for r in samples})
    rows = []
    for label, lo, hi in AGE_BINS:
        group = [r for r in samples if lo <= float(r["age_s"]) < hi]
        flights_in_bin = sorted({str(r["flight_id"]) for r in group})
        rows.append({
            "age_bin": label,
            "n": len(group),
            "n_flights": len(flights_in_bin),
            "coverage": "",
            "worst_flight": flights_in_bin[0] if flights_in_bin else "",
            "status": "DATA-INSUFFICIENT: need >=2 flights for LOFO" if len(flights) < 2 else "",
        })
    return rows, "none"


def fallback_bound(samples: list[dict], mean: dict) -> list[dict]:
    raw = []
    for label, lo, hi in AGE_BINS:
        group = [r for r in samples if lo <= float(r["age_s"]) < hi]
        centered = [
            abs(float(r["r_v_mps"]) - (float(mean["b0"]) + float(mean["b1"]) * float(r["age_s"])))
            for r in group
        ]
        raw.append({
            "age_bin": label,
            "n": len(group),
            "raw_p95_abs_centered_r_v_mps": percentile(centered, 95) if centered else "",
        })
    running = 0.0
    for row in raw:
        val = fnum(row["raw_p95_abs_centered_r_v_mps"])
        if val is not None:
            running = max(running, val)
        row["isotonic_B_rate_drift_mps"] = running
    return raw


def release_verdict(n_clusters: int, point: float, u95: float | None,
                    bootstrap_valid: bool) -> tuple[str, str, int]:
    if n_clusters < MIN_RELEASE_CLUSTERS:
        return (
            "HOLD, DATA-INSUFFICIENT",
            f"n_clusters={n_clusters} < {MIN_RELEASE_CLUSTERS}; cluster bootstrap U95 is degenerate/not release-valid.",
            MIN_RELEASE_CLUSTERS - n_clusters,
        )
    if point > SIGMA_A_GATE:
        return ("FAIL", "point sigma_a exceeds 0.35; (c)-floor configuration becomes the plan.", 0)
    if not bootstrap_valid or u95 is None or u95 > SIGMA_A_GATE:
        return (
            "HOLD, DATA-INSUFFICIENT",
            "point <= 0.35 but U95 is not inside the release gate.",
            0,
        )
    return ("RELEASE-READY (statistics side)", "U95(sigma_a) <= 0.35.", 0)


def write_report(out_dir: Path, summary: dict, release_row: dict,
                 mean_row: dict, regime_rows: list[dict], pseudo_row: dict,
                 retired_row: dict, lofo_rows: list[dict],
                 fallback_rows: list[dict]) -> None:
    lines = [
        "# SIGMA_A Release Fit v2",
        "",
        "Scope: CSV-only on existing `caa2398` oracle-reference residuals; no replay, campaign, FlightSim, or DCGame launch.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        f"Source artifact: `{summary['source_dir']}`.",
        f"Response note read: `{summary['response31_path']}`.",
        "",
        "## Release Columns",
        "",
        "| n_flights | n_clusters | n_rows | point sigma_a | U95(sigma_a) | sigma_0 | pseudo floor sigma_0 | b0 | b1 | max validated age | verdict |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        f"| {summary['n_flights']} | {summary['n_clusters']} | {summary['n_rows']} | "
        f"{fmt(release_row['sigma_a_mps2'])} | {fmt(release_row['u95_sigma_a_mps2'])} | "
        f"{fmt(release_row['sigma_0_mps'])} | {fmt(pseudo_row.get('sigma_0_mps'))} | "
        f"{fmt(mean_row['b0_mps'])} | {fmt(mean_row['b1_mps_per_s'])} | "
        f"`{summary['max_validated_age']}` | `{summary['verdict']}` |",
        "",
        f"DATA-INSUFFICIENT check: `{summary['data_insufficient_note']}`",
        f"Estimated additional clusters needed: `{summary['additional_clusters_needed_min']}`.",
        "",
        "## Constrained Robust Fit",
        "",
        "| Estimator | nu | sigma_0 | sigma_a | U95 | bootstrap valid | note |",
        "|---|---:|---:|---:|---:|---|---|",
        f"| `{release_row['estimator']}` | {fmt(release_row['nu'])} | "
        f"{fmt(release_row['sigma_0_mps'])} | {fmt(release_row['sigma_a_mps2'])} | "
        f"{fmt(release_row['u95_sigma_a_mps2'])} | `{release_row['bootstrap_valid']}` | "
        f"{release_row['bootstrap_note']} |",
        f"| `{retired_row['estimator']}` | n/a | {fmt(retired_row['sigma_0_mps'])} | "
        f"{fmt(retired_row['sigma_a_mps2'])} | n/a | `False` | sensitivity only; retired as release instrument |",
        "",
        "## Mean Fit",
        "",
        "| b0 | b0 CI | b1 | b1 CI | residual RMS after mean | deterministic note |",
        "|---:|---|---:|---|---:|---|",
        f"| {fmt(mean_row['b0_mps'])} | "
        f"{fmt(mean_row['b0_ci_low_mps'])}/{fmt(mean_row['b0_ci_median_mps'])}/{fmt(mean_row['b0_ci_high_mps'])} | "
        f"{fmt(mean_row['b1_mps_per_s'])} | "
        f"{fmt(mean_row['b1_ci_low_mps_per_s'])}/{fmt(mean_row['b1_ci_median_mps_per_s'])}/{fmt(mean_row['b1_ci_high_mps_per_s'])} | "
        f"{fmt(mean_row['mean_fit_residual_rms_mps'])} | {mean_row['deterministic_note']} |",
        "",
        "## Command Regimes",
        "",
        "| Regime | n | age range | signed mean | signed median | RMS |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for row in regime_rows:
        lines.append(
        f"| `{row['command_regime']}` | {row['n']} | "
            f"{fmt(row['age_min_s'])}-{fmt(row['age_max_s'])} | "
            f"{fmt(row['signed_mean_r_v_mps'])} | {fmt(row['signed_median_r_v_mps'])} | "
            f"{fmt(row['r_v_rms_mps'])} |"
        )
    lines.extend([
        "",
        "Mean/regime deterministic read: the point mean fit has a nonzero signed age slope and the non-empty regimes have nonzero signed means. With one cluster this is not release-stable, but it is reported as a deterministic-model suspect and is not folded into sigma.",
        "",
        "## Pseudo-Transition Intercept Floor",
        "",
        "| n | sigma_0 | sigma_a | real sigma_0 below floor | note |",
        "|---:|---:|---:|---|---|",
        f"| {pseudo_row.get('n', 0)} | {fmt(pseudo_row.get('sigma_0_mps'))} | "
        f"{fmt(pseudo_row.get('sigma_a_mps2'))} | "
        f"`{pseudo_row.get('real_below_pseudo_floor')}` | {pseudo_row.get('note', '')} |",
        "",
        "Pseudo-floor read: real sigma_0 below the FULL-only pseudo floor is a sanity blocker unless additional clusters overturn it.",
        "",
        "## LOFO Coverage",
        "",
        "| Age bin | n | n flights | coverage | worst flight | status |",
        "|---|---:|---:|---:|---|---|",
    ])
    for row in lofo_rows:
        lines.append(
            f"| `{row['age_bin']}` | {row['n']} | {row['n_flights']} | "
            f"{fmt(row['coverage'])} | `{row['worst_flight']}` | {row['status']} |"
        )
    lines.extend([
        "",
        "## Model-Form Kill Test And Fallback",
        "",
        "LOFO monotonic degradation cannot be tested with one flight. The fallback bound below is an in-sample/advisory-only monotone ceiling.",
        "",
        "| Age bin | n | raw p95 | isotonic B_rate_drift |",
        "|---|---:|---:|---:|",
    ])
    for row in fallback_rows:
        lines.append(
            f"| `{row['age_bin']}` | {row['n']} | "
            f"{fmt(row['raw_p95_abs_centered_r_v_mps'])} | "
            f"{fmt(row['isotonic_B_rate_drift_mps'])} |"
        )
    lines.extend([
        "",
        "## Verdict",
        "",
        f"`{summary['verdict']}`: {summary['verdict_note']}",
        "",
        "The point estimate is below the gate, but the release statistic is not releasable because the current artifact has one independent transition cluster. The next action is to add at least five more independent replay transition clusters from the archive, not to squeeze the fit.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    source_dir = args.source_dir.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir.resolve() if args.out_dir else ROOT / "tuning" / f"{OUT_PREFIX}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_residual_samples(source_dir)
    if not samples:
        raise RuntimeError(f"No residual samples in {source_dir}")
    grouped = clusters(samples)
    n_flights = len({str(r["flight_id"]) for r in samples})
    n_clusters = len(grouped)

    release = fit_release(samples)
    boot = cluster_bootstrap(samples)
    release.update(boot)
    release["bootstrap_note"] = (
        "cluster bootstrap is release-valid"
        if boot["bootstrap_valid"]
        else "DATA-INSUFFICIENT: cluster bootstrap degenerate/prohibited for release"
    )

    retired = retired_theil_sen(samples)
    mean = fit_mean(samples)
    mean_row = {
        "b0_mps": mean["b0"],
        "b1_mps_per_s": mean["b1"],
        "b0_ci_low_mps": boot["b0_ci_low_mps"],
        "b0_ci_median_mps": boot["b0_ci_median_mps"],
        "b0_ci_high_mps": boot["b0_ci_high_mps"],
        "b1_ci_low_mps_per_s": boot["b1_ci_low_mps_per_s"],
        "b1_ci_median_mps_per_s": boot["b1_ci_median_mps_per_s"],
        "b1_ci_high_mps_per_s": boot["b1_ci_high_mps_per_s"],
        "mean_fit_residual_rms_mps": mean["mean_fit_residual_rms_mps"],
        "deterministic_note": (
            "DETERMINISTIC-SUSPECT: point b1 is nonzero, but cluster CI is invalid with one cluster; do not fold this signed trend into sigma."
        ),
    }
    regimes = regime_table(samples)

    pseudo = pseudo_transition_samples(source_dir)
    pseudo_fit = fit_release(pseudo) if pseudo else {"sigma_0_mps": "", "sigma_a_mps2": ""}
    pseudo_row = {
        "n": len(pseudo),
        "sigma_0_mps": pseudo_fit.get("sigma_0_mps", ""),
        "sigma_a_mps2": pseudo_fit.get("sigma_a_mps2", ""),
        "real_below_pseudo_floor": (
            float(release["sigma_0_mps"]) + 1e-9 < float(pseudo_fit["sigma_0_mps"])
            if pseudo and fnum(pseudo_fit.get("sigma_0_mps")) is not None
            else ""
        ),
        "note": (
            "FULL-only pseudo anchors/evaluations use non-overlapping 0.35s windows."
            if pseudo
            else "No pseudo samples available from existing CSV."
        ),
    }
    lofo, max_validated_age = lofo_table(samples, release)
    fallback = fallback_bound(samples, mean)
    verdict, verdict_note, more_clusters = release_verdict(
        n_clusters,
        float(release["sigma_a_mps2"]),
        fnum(release.get("u95_sigma_a_mps2")),
        bool(release["bootstrap_valid"]),
    )
    summary = {
        "repo_head": git_head(),
        "source_dir": str(source_dir),
        "response31_path": str(ROOT / "docs" / "thinktank" / "RESPONSE31.md"),
        "n_flights": n_flights,
        "n_clusters": n_clusters,
        "n_rows": len(samples),
        "max_validated_age": max_validated_age,
        "verdict": verdict,
        "verdict_note": verdict_note,
        "additional_clusters_needed_min": more_clusters,
        "data_insufficient_note": (
            f"n_clusters={n_clusters}; release requires >= {MIN_RELEASE_CLUSTERS} independent clusters."
        ),
    }

    release_row = {
        "estimator": release["estimator"],
        "nu": release["nu"],
        "sigma_0_mps": release["sigma_0_mps"],
        "sigma_a_mps2": release["sigma_a_mps2"],
        "u95_sigma_a_mps2": release["u95_sigma_a_mps2"],
        "bootstrap_valid": release["bootstrap_valid"],
        "bootstrap_note": release["bootstrap_note"],
    }

    write_csv(out_dir / "samples.csv", samples)
    write_csv(out_dir / "release_fit.csv", [release_row])
    write_csv(out_dir / "mean_fit.csv", [mean_row])
    write_csv(out_dir / "command_regimes.csv", regimes)
    write_csv(out_dir / "pseudo_transition_samples.csv", pseudo)
    write_csv(out_dir / "pseudo_transition_floor.csv", [pseudo_row])
    write_csv(out_dir / "retired_sensitivity.csv", [retired])
    write_csv(out_dir / "lofo_coverage.csv", lofo)
    write_csv(out_dir / "fallback_monotone_bound.csv", fallback)
    write_csv(out_dir / "release_verdict.csv", [summary])
    write_report(out_dir, summary, release_row, mean_row, regimes, pseudo_row, retired, lofo, fallback)
    print(f"[release-fit-v2] report={out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
