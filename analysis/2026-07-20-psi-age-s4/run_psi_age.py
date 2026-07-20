"""P2 — Psi-age ledger + S4 prep (cohort-4 gate).

Side-rung projective solve holds gate orientation from the last
multi-edge fix. For each SIDE feature in phase6l + 29-sweep replays:
  - age of the orientation prior at feature time (psi_age)
  - side-pair residual vs full-quad truth, stratified by that age

Verdict: if residuals show no material age dependence over the
encountered range → psi-age stays diagnostic-only (state interval);
else propose hard validity limit or sigma_psi(age).
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

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

# Primary: L1 full addendum features (phase6l F2/F4 + 29-sweep material)
FEATURES_CSV = ROOT / "tuning" / "l1-full-addendum-a150ece-a150ece-20260720T094216Z" / "features.csv"
# Fallback / extra: phase6l raw if needed
AGE_BINS = [(0.0, 0.05), (0.05, 0.12), (0.12, 0.25), (0.25, 0.50), (0.50, 1.0), (1.0, 9.0)]


def fnum(x):
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def load_features(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_psi_age_rows(rows: list[dict]) -> list[dict]:
    """Per flight: track last multi-edge FULL timestamp; SIDE psi_age =
    feature_time − that prior. Residual = e_SIDE − e_FULL at same
    exposure ts when paired, else nearest FULL within 40ms.
    """
    by_flight: dict[str, list[dict]] = {}
    for r in rows:
        fid = r.get("flight_id") or r.get("flight") or "?"
        by_flight.setdefault(fid, []).append(r)

    out = []
    for fid, frs in by_flight.items():
        frs = sorted(frs, key=lambda r: fnum(r.get("feature_ts_ns")) or 0.0)
        last_multi_ts = None  # ns
        last_multi_e = None
        # Index FULL by exact ts for pairing
        full_by_ts = {}
        for r in frs:
            mode = r.get("feature_mode") or ""
            if mode == "FULL_QUAD" and fnum(r.get("e_meas")) is not None:
                ts = int(float(r["feature_ts_ns"]))
                full_by_ts[ts] = fnum(r["e_meas"])
                # multi-edge orientation prior: certified FULL_QUAD
                if r.get("cert_status") == "certified":
                    last_multi_ts = ts
                    last_multi_e = fnum(r["e_meas"])

        # Re-scan chronologically for SIDE with running prior
        last_multi_ts = None
        for r in frs:
            mode = r.get("feature_mode") or ""
            ts = int(float(r["feature_ts_ns"]))
            if mode == "FULL_QUAD" and r.get("cert_status") == "certified":
                last_multi_ts = ts
                continue
            if mode not in ("SIDE_PAIR", "SIDE_PAIR_ROW_ONLY"):
                continue
            if last_multi_ts is None:
                continue
            e_side = fnum(r.get("e_meas"))
            e_full = full_by_ts.get(ts)
            residual = None
            if e_side is not None and e_full is not None:
                residual = e_side - e_full
            psi_age = (ts - last_multi_ts) / 1e9
            # Maintenance-relevant: SIDE without same-exposure FULL
            # (orientation held from a prior multi-edge fix).
            maintenance = e_full is None
            out.append({
                "flight_id": fid,
                "flight": r.get("flight"),
                "t_rel_s": fnum(r.get("t_rel_s")),
                "feature_ts_ns": ts,
                "feature_mode": mode,
                "cert_status": r.get("cert_status"),
                "range_z_m": fnum(r.get("range_z_m")),
                "e_side": e_side,
                "e_full_same_ts": e_full,
                "residual_side_minus_full": residual,
                "psi_age_s": psi_age,
                "maintenance_no_same_ts_full": maintenance,
                "e_reject": r.get("e_reject"),
                "span_px": fnum(r.get("span_px")),
                "commit": r.get("commit"),
            })
    return out


def nearest_full_residual(rows: list[dict], side_rows: list[dict]) -> list[dict]:
    """For maintenance SIDE rows, residual vs nearest prior FULL e_meas
    within 0.5s (orientation-prior epoch), not same-ts pair.
    """
    by_flight: dict[str, list[dict]] = {}
    for r in rows:
        fid = r.get("flight_id") or r.get("flight") or "?"
        by_flight.setdefault(fid, []).append(r)
    enriched = []
    for r in side_rows:
        if not r.get("maintenance_no_same_ts_full"):
            continue
        if r.get("feature_mode") != "SIDE_PAIR":
            continue
        if r.get("e_side") is None:
            continue
        fid = r["flight_id"]
        ts = r["feature_ts_ns"]
        best = None
        for f in by_flight.get(fid, []):
            if f.get("feature_mode") != "FULL_QUAD":
                continue
            if f.get("cert_status") != "certified":
                continue
            e = fnum(f.get("e_meas"))
            if e is None:
                continue
            fts = int(float(f["feature_ts_ns"]))
            if fts > ts:
                continue
            dt = (ts - fts) / 1e9
            if dt > 1.0:
                continue
            if best is None or dt < best[0]:
                best = (dt, e)
        if best is None:
            continue
        enriched.append({
            **r,
            "residual_vs_prior_full": r["e_side"] - best[1],
            "dt_to_prior_full_s": best[0],
        })
    return enriched


def stratify(rows: list[dict]) -> list[dict]:
    bins = []
    for lo, hi in AGE_BINS:
        xs = [r for r in rows
              if r.get("residual_side_minus_full") is not None
              and r.get("psi_age_s") is not None
              and lo <= r["psi_age_s"] < hi]
        res = np.array([r["residual_side_minus_full"] for r in xs], float)
        ages = np.array([r["psi_age_s"] for r in xs], float)
        entry = {
            "age_lo_s": lo,
            "age_hi_s": hi,
            "n": len(xs),
            "residual_mean": float(np.mean(res)) if len(res) else None,
            "residual_std": float(np.std(res)) if len(res) else None,
            "residual_mae": float(np.mean(np.abs(res))) if len(res) else None,
            "residual_p90_abs": float(np.percentile(np.abs(res), 90)) if len(res) else None,
            "age_mean": float(np.mean(ages)) if len(ages) else None,
        }
        bins.append(entry)
    return bins


def age_dependence(bins: list[dict], paired: list[dict]) -> dict:
    """Material age dependence: MAE or |mean| grows monotonically across
    populated bins by >2cm, OR linear |corr(age, |residual|)| > 0.3
    with n>=20.
    """
    populated = [b for b in bins if b["n"] >= 5 and b["residual_mae"] is not None]
    grows = False
    if len(populated) >= 2:
        maes = [b["residual_mae"] for b in populated]
        # grow if last bin MAE exceeds first by >0.02m and trend up
        grows = (maes[-1] - maes[0] > 0.02
                 and all(maes[i] <= maes[i + 1] + 0.005
                         for i in range(len(maes) - 1)))

    corr = None
    ages = np.array([r["psi_age_s"] for r in paired
                     if r.get("residual_side_minus_full") is not None], float)
    abs_r = np.array([abs(r["residual_side_minus_full"]) for r in paired
                      if r.get("residual_side_minus_full") is not None], float)
    if len(ages) >= 20 and float(np.std(ages)) > 1e-6:
        corr = float(np.corrcoef(ages, abs_r)[0, 1])

    material = bool(grows or (corr is not None and abs(corr) > 0.30))
    age_max = float(np.max(ages)) if len(ages) else None
    age_p90 = float(np.percentile(ages, 90)) if len(ages) else None

    if not material:
        verdict = (
            "DIAGNOSTIC_ONLY — residuals show no material age dependence "
            f"over the encountered psi_age interval "
            f"[0, {age_max:.3f}]s (p90={age_p90:.3f}s). "
            "No hard validity limit / sigma_psi(age) required for S4."
        )
        proposal = None
    else:
        # Propose validity at first bin where MAE exceeds 0.05 or 2× first bin
        limit = None
        if populated:
            base = populated[0]["residual_mae"]
            for b in populated:
                if b["residual_mae"] > max(0.05, 2.0 * base):
                    limit = b["age_lo_s"]
                    break
        verdict = (
            "AGE_DEPENDENT — residuals grow with orientation-prior age; "
            "propose hard validity limit and/or sigma_psi(age)."
        )
        proposal = {
            "hard_validity_limit_s": limit if limit is not None else age_p90,
            "sigma_psi_age_form": "sigma_e_side(age) = sqrt(sigma0^2 + (k*age)^2)",
            "k_mps": None,  # fit below
            "note": "S4 disposition input — engineering owns the knob",
        }
        if len(ages) >= 20:
            # crude k from rms growth
            # |r| ≈ k * age  (through origin) via least squares
            k = float(np.linalg.lstsq(ages.reshape(-1, 1), abs_r, rcond=None)[0][0])
            proposal["k_mps"] = k

    return {
        "material_age_dependence": material,
        "corr_age_abs_residual": corr,
        "mae_grows_across_bins": grows,
        "psi_age_max_s": age_max,
        "psi_age_p90_s": age_p90,
        "n_paired": int(len(ages)),
        "verdict": verdict,
        "proposal": proposal,
    }


def main() -> None:
    rows = load_features(FEATURES_CSV)
    if not rows:
        raise SystemExit(f"missing features csv: {FEATURES_CSV}")
    side_rows = build_psi_age_rows(rows)
    # Primary S4 population: maintenance SIDE (no same-ts FULL) with
    # residual vs prior FULL e_meas.
    maint = nearest_full_residual(rows, side_rows)
    for r in maint:
        r["residual_side_minus_full"] = r["residual_vs_prior_full"]
        # Use psi_age (= dt to orientation prior) for stratification
    paired = [r for r in maint if r.get("residual_side_minus_full") is not None]
    # Also keep exact-pair residuals for overlap reference
    exact = [r for r in side_rows
             if r.get("residual_side_minus_full") is not None
             and r.get("feature_mode") == "SIDE_PAIR"
             and not r.get("maintenance_no_same_ts_full")]
    bins = stratify(paired)
    dep = age_dependence(bins, paired)

    row_only = [r for r in side_rows if r.get("feature_mode") == "SIDE_PAIR_ROW_ONLY"]

    summary = {
        "ask": "psi-age ledger + S4 prep",
        "source": str(FEATURES_CSV),
        "n_side_features": len(side_rows),
        "n_side_pair_metric": sum(1 for r in side_rows if r["feature_mode"] == "SIDE_PAIR"),
        "n_side_row_only_shadow": len(row_only),
        "n_maintenance_with_prior_full_residual": len(paired),
        "n_exact_same_ts_pairs": len(exact),
        "age_bins": bins,
        "disposition": dep,
        "verdict": ("DIAGNOSTIC_ONLY" if not dep["material_age_dependence"]
                    else "AGE_DEPENDENT"),
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    fields = list(side_rows[0].keys()) if side_rows else []
    with (OUT / "psi_age_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in side_rows:
            w.writerow(r)

    with (OUT / "maintenance_residuals.csv").open(
            "w", newline="", encoding="utf-8") as f:
        if paired:
            w = csv.DictWriter(f, fieldnames=list(paired[0].keys()))
            w.writeheader()
            for r in paired:
                w.writerow(r)

    with (OUT / "age_bins.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(bins[0].keys()) if bins else [])
        w.writeheader()
        for b in bins:
            w.writerow(b)

    lines = [
        "# Psi-age ledger + S4 prep",
        "",
        f"**Verdict: {summary['verdict']}**",
        "",
        dep["verdict"],
        "",
        f"- SIDE features: {summary['n_side_features']} "
        f"(metric SIDE_PAIR={summary['n_side_pair_metric']}, "
        f"ROW_ONLY shadow={summary['n_side_row_only_shadow']})",
        f"- maintenance SIDE with prior-FULL residual: "
        f"{summary['n_maintenance_with_prior_full_residual']}",
        f"- exact same-ts FULL/SIDE pairs (overlap, ψ≈0): "
        f"{summary['n_exact_same_ts_pairs']}",
        f"- psi_age max / p90: {dep['psi_age_max_s']} / {dep['psi_age_p90_s']} s",
        f"- corr(age, |residual|): {dep['corr_age_abs_residual']}",
        "",
        "## Residual vs prior full-quad by ψ-age bin (maintenance)",
        "",
        "| age [s] | n | MAE | std | p90\\|r\\| |",
        "|---------|--:|----:|----:|--------:|",
    ]
    for b in bins:
        if b["n"] == 0:
            lines.append(
                f"| [{b['age_lo_s']:.2f},{b['age_hi_s']:.2f}) | 0 | — | — | — |"
            )
        else:
            lines.append(
                f"| [{b['age_lo_s']:.2f},{b['age_hi_s']:.2f}) | {b['n']} | "
                f"{b['residual_mae']:.4f} | {b['residual_std']:.4f} | "
                f"{b['residual_p90_abs']:.4f} |"
            )
    if dep["proposal"]:
        lines += ["", "## Proposal", "", json.dumps(dep["proposal"], indent=2)]
    lines += [
        "",
        "ψ-age = time since last certified FULL_QUAD (orientation prior). "
        "Maintenance rows = SIDE_PAIR with no same-exposure FULL.",
        "",
        "## Deliverables",
        "",
        "- `psi_age_ledger.csv`, `maintenance_residuals.csv`, "
        "`age_bins.csv`, `summary.json`, this report",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": summary["verdict"],
        "n_maintenance": dep["n_paired"],
        "corr": dep["corr_age_abs_residual"],
        "psi_age_p90": dep["psi_age_p90_s"],
        "psi_age_max": dep["psi_age_max_s"],
    }, indent=2))


if __name__ == "__main__":
    main()
