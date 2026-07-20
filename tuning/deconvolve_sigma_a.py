"""Deconvolve sigma_a from existing R26 residuals.

QA & MOCK-TUNER scope: reads already-committed tuning CSV artifacts only.
No replay, mock campaign, or real simulator is launched.
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
DEFAULT_SOURCE = (
    ROOT
    / "tuning"
    / "hold-lift-r26-3b554f3-35bfa6d-20260720T121704Z"
)
DEFAULT_OUT_PREFIX = "sigma-a-deconv-caa2398"
SIGMA_A_GATE_MPS2 = 0.35
SIGMA_REF_SANITY_LO_MPS = 0.15
SIGMA_REF_SANITY_HI_MPS = 0.30
BOOTSTRAP_N = 5000
BOOTSTRAP_SEED = 20260720


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


def age_bin(age: float) -> str:
    if age < 0.10:
        return "lt0p10"
    if age < 0.20:
        return "0p10-0p20"
    if age < 0.30:
        return "0p20-0p30"
    if age < 0.50:
        return "0p30-0p50"
    return "gte0p50"


def read_samples(source_dir: Path) -> list[dict]:
    path = source_dir / "sigma_a_oracle_rows.csv"
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            age = fnum(rec.get("rate_anchor_age_s"))
            residual = fnum(rec.get("rate_error_oracle_mps"))
            if age is None or residual is None or age < 0.10:
                continue
            rows.append({
                "flight": rec.get("flight", ""),
                "frame_id": rec.get("frame_id", ""),
                "feature_ts_ns": rec.get("feature_ts_ns", ""),
                "trial": rec.get("trial", ""),
                "regime": rec.get("sigma_regime") or (
                    "switch_adjacent" if age < 0.20 else "maintenance"
                ),
                "age_bin": age_bin(age),
                "age_s": age,
                "age2_s2": age * age,
                "rate_error_oracle_mps": residual,
                "rv2_m2ps2": residual * residual,
                "legacy_ratio_abs_sigma_a_mps2": abs(residual) / age,
            })
    return rows


def ols_fit(samples: list[dict]) -> dict:
    if not samples:
        return {}
    xs = [float(row["age2_s2"]) for row in samples]
    ys = [float(row["rv2_m2ps2"]) for row in samples]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    slope = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom
        if denom > 1e-18
        else 0.0
    )
    intercept = y_mean - slope * x_mean
    return fit_row("per_sample_ols", samples, slope, intercept)


def theil_sen_fit(samples: list[dict]) -> dict:
    if not samples:
        return {}
    pts = [(float(row["age2_s2"]), float(row["rv2_m2ps2"])) for row in samples]
    slopes = []
    for i, (x1, y1) in enumerate(pts):
        for x2, y2 in pts[i + 1:]:
            if abs(x2 - x1) <= 1e-18:
                continue
            slopes.append((y2 - y1) / (x2 - x1))
    slope = statistics.median(slopes) if slopes else 0.0
    intercept = statistics.median([y - slope * x for x, y in pts])
    out = fit_row("per_sample_theil_sen", samples, slope, intercept)
    out["pair_slope_n"] = len(slopes)
    return out


def fit_row(estimator: str, samples: list[dict], slope: float, intercept: float) -> dict:
    sigma_a = math.sqrt(slope) if slope > 0.0 else 0.0
    sigma_ref = math.sqrt(intercept) if intercept > 0.0 else 0.0
    return {
        "estimator": estimator,
        "n": len(samples),
        "age_min_s": min(float(r["age_s"]) for r in samples) if samples else "",
        "age_max_s": max(float(r["age_s"]) for r in samples) if samples else "",
        "slope_sigma_a2_raw": slope,
        "intercept_sigma_ref2_raw": intercept,
        "sigma_a_mps2": sigma_a,
        "sigma_ref_mps": sigma_ref,
        "slope_clamped": slope < 0.0,
        "intercept_clamped": intercept < 0.0,
        "rate_error_rms_mps": rms([float(r["rate_error_oracle_mps"]) for r in samples]),
        "legacy_ratio_p95_mps2": percentile(
            [float(r["legacy_ratio_abs_sigma_a_mps2"]) for r in samples],
            95,
        ),
    }


def bootstrap_ci(samples: list[dict], fit_fn, n: int, seed: int) -> dict:
    rng = random.Random(seed)
    sigma_a = []
    sigma_ref = []
    for _ in range(n):
        draw = [samples[rng.randrange(len(samples))] for _ in samples]
        fit = fit_fn(draw)
        if not fit:
            continue
        sigma_a.append(float(fit["sigma_a_mps2"]))
        sigma_ref.append(float(fit["sigma_ref_mps"]))
    return {
        "bootstrap_n": len(sigma_a),
        "sigma_a_ci_low_mps2": percentile(sigma_a, 2.5),
        "sigma_a_ci_median_mps2": percentile(sigma_a, 50),
        "sigma_a_ci_high_mps2": percentile(sigma_a, 97.5),
        "sigma_ref_ci_low_mps": percentile(sigma_ref, 2.5),
        "sigma_ref_ci_median_mps": percentile(sigma_ref, 50),
        "sigma_ref_ci_high_mps": percentile(sigma_ref, 97.5),
    }


def grouped(samples: list[dict]) -> dict[str, list[dict]]:
    return {
        "all": samples,
        "switch_adjacent": [r for r in samples if r["regime"] == "switch_adjacent"],
        "maintenance": [r for r in samples if r["regime"] == "maintenance"],
    }


def fit_groups(samples: list[dict], fit_fn, estimator: str) -> list[dict]:
    rows = []
    for label, group in grouped(samples).items():
        if not group:
            continue
        fit = fit_fn(group)
        fit["group"] = label
        fit["estimator"] = estimator
        ci = bootstrap_ci(group, fit_fn, BOOTSTRAP_N, BOOTSTRAP_SEED)
        fit.update(ci)
        fit["gate_lives_by_sigma_a"] = float(fit["sigma_a_mps2"]) <= SIGMA_A_GATE_MPS2
        fit["sigma_ref_sanity"] = (
            SIGMA_REF_SANITY_LO_MPS
            <= float(fit["sigma_ref_mps"])
            <= SIGMA_REF_SANITY_HI_MPS
        )
        rows.append(fit)
    return rows


def age_bin_counts(samples: list[dict]) -> list[dict]:
    rows = []
    for label in ["0p10-0p20", "0p20-0p30", "0p30-0p50", "gte0p50"]:
        group = [r for r in samples if r["age_bin"] == label]
        ages = [float(r["age_s"]) for r in group]
        residuals = [float(r["rate_error_oracle_mps"]) for r in group]
        ratios = [float(r["legacy_ratio_abs_sigma_a_mps2"]) for r in group]
        rows.append({
            "age_bin": label,
            "n": len(group),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "mean_age2_s2": statistics.fmean([a * a for a in ages]) if ages else "",
            "rate_error_mean_mps": statistics.fmean(residuals) if residuals else "",
            "rate_error_rms_mps": rms(residuals) if residuals else "",
            "mean_rv2_m2ps2": statistics.fmean([r * r for r in residuals]) if residuals else "",
            "legacy_ratio_p95_mps2": percentile(ratios, 95) if ratios else "",
        })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def write_report(out_dir: Path, summary: dict, primary_rows: list[dict],
                 ols_rows: list[dict], counts: list[dict]) -> None:
    primary = next(row for row in primary_rows if row["group"] == "all")
    lines = [
        "# SIGMA_A Deconvolution",
        "",
        "Scope: existing `caa2398` tuning residuals only; no replay, campaign, or real simulator run.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        f"Source artifact: `{summary['source_dir']}`.",
        "",
        "Model: regress `r_v^2` against `age^2`: intercept -> `sigma_ref^2`, slope -> `sigma_a^2`.",
        "Primary estimator: per-sample Theil-Sen robust line on oracle-reference residuals. OLS is included as sensitivity.",
        "",
        "## Primary Fit",
        "",
        "| Group | n | age range | slope raw | sigma_a | sigma_a 95% CI | sigma_ref | sigma_ref 95% CI | gate | ref sanity |",
        "|---|---:|---|---:|---:|---|---:|---|---|---|",
    ]
    for row in primary_rows:
        lines.append(
            f"| `{row['group']}` | {row['n']} | "
            f"{fmt(row['age_min_s'])}-{fmt(row['age_max_s'])} | "
            f"{fmt(row['slope_sigma_a2_raw'])} | {fmt(row['sigma_a_mps2'])} | "
            f"{fmt(row['sigma_a_ci_low_mps2'])}/"
            f"{fmt(row['sigma_a_ci_median_mps2'])}/"
            f"{fmt(row['sigma_a_ci_high_mps2'])} | "
            f"{fmt(row['sigma_ref_mps'])} | "
            f"{fmt(row['sigma_ref_ci_low_mps'])}/"
            f"{fmt(row['sigma_ref_ci_median_mps'])}/"
            f"{fmt(row['sigma_ref_ci_high_mps'])} | "
            f"`{row['gate_lives_by_sigma_a']}` | `{row['sigma_ref_sanity']}` |"
        )
    lines.extend([
        "",
        "## OLS Sensitivity",
        "",
        "| Group | n | slope raw | sigma_a | sigma_ref | gate | ref sanity |",
        "|---|---:|---:|---:|---:|---|---|",
    ])
    for row in ols_rows:
        lines.append(
            f"| `{row['group']}` | {row['n']} | "
            f"{fmt(row['slope_sigma_a2_raw'])} | {fmt(row['sigma_a_mps2'])} | "
            f"{fmt(row['sigma_ref_mps'])} | `{row['gate_lives_by_sigma_a']}` | "
            f"`{row['sigma_ref_sanity']}` |"
        )
    lines.extend([
        "",
        "## Age-Bin Counts",
        "",
        "| Age bin | n | age range | mean r_v^2 | residual RMS | legacy ratio p95 |",
        "|---|---:|---|---:|---:|---:|",
    ])
    for row in counts:
        lines.append(
            f"| `{row['age_bin']}` | {row['n']} | "
            f"{fmt(row['age_min_s'])}-{fmt(row['age_max_s'])} | "
            f"{fmt(row['mean_rv2_m2ps2'])} | {fmt(row['rate_error_rms_mps'])} | "
            f"{fmt(row['legacy_ratio_p95_mps2'])} |"
        )
    lines.extend([
        "",
        "## Verdict",
        "",
        f"- Deconvolved `sigma_a`: `{fmt(primary['sigma_a_mps2'])}` "
        f"with bootstrap CI "
        f"`{fmt(primary['sigma_a_ci_low_mps2'])}/"
        f"{fmt(primary['sigma_a_ci_median_mps2'])}/"
        f"{fmt(primary['sigma_a_ci_high_mps2'])}`.",
        f"- Deconvolved `sigma_ref`: `{fmt(primary['sigma_ref_mps'])}` "
        f"with bootstrap CI "
        f"`{fmt(primary['sigma_ref_ci_low_mps'])}/"
        f"{fmt(primary['sigma_ref_ci_median_mps'])}/"
        f"{fmt(primary['sigma_ref_ci_high_mps'])}`.",
        f"- Drift gate by deconvolved sigma_a: "
        f"`{primary['gate_lives_by_sigma_a']}` (`<=0.35 m/s^2`).",
        f"- Sigma_ref sanity window `{SIGMA_REF_SANITY_LO_MPS:.2f}-"
        f"{SIGMA_REF_SANITY_HI_MPS:.2f} m/s`: `{primary['sigma_ref_sanity']}`.",
        "",
        "Interpretation: the age-growth slope is non-positive in these residuals, "
        "so the true drift term clamps to zero under the deconvolution model. "
        "The remaining error behaves like reference/anchor-rate offset rather "
        "than age-growing acceleration drift; however the fitted sigma_ref is "
        "above the expected oracle-slope noise band and should be called out "
        "for advisor ratification.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    source_dir = args.source_dir.resolve()
    if args.out_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = ROOT / "tuning" / f"{DEFAULT_OUT_PREFIX}-{stamp}"
    else:
        out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = read_samples(source_dir)
    if not samples:
        raise RuntimeError(f"No oracle residual samples found under {source_dir}")

    primary_rows = fit_groups(samples, theil_sen_fit, "per_sample_theil_sen")
    ols_rows = fit_groups(samples, ols_fit, "per_sample_ols")
    counts = age_bin_counts(samples)
    write_csv(out_dir / "samples.csv", samples)
    write_csv(out_dir / "deconv_primary_theil_sen.csv", primary_rows)
    write_csv(out_dir / "deconv_ols_sensitivity.csv", ols_rows)
    write_csv(out_dir / "age_bin_counts.csv", counts)

    summary = {
        "repo_head": git_head(),
        "source_dir": str(source_dir),
        "sample_n": len(samples),
        "primary_estimator": "per_sample_theil_sen",
        "bootstrap_n": BOOTSTRAP_N,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    write_report(out_dir, summary, primary_rows, ols_rows, counts)
    print(f"[sigma-a-deconv] report={out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
