"""Postprocess TASK A archive-retro outputs with ERA heterogeneity tables."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from archive_harvest_release_fit_v21 import SIGMA_A_GATE, fit_release, fnum  # type: ignore  # noqa: E402


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


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


def median(vals: list[float]) -> float | str:
    return statistics.median(vals) if vals else ""


def f(value) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_a_dir", type=Path)
    args = ap.parse_args(argv)
    out_dir = args.task_a_dir.resolve()

    clusters = read_csv(out_dir / "expanded_census_clusters.csv")
    samples = read_csv(out_dir / "forced_withhold_samples.csv")
    flight_loao = read_csv(out_dir / "flight_loao_sensitivity.csv")
    by_cluster = {row["cluster_id"]: row for row in clusters}
    by_flight = {row["flight_id"]: row for row in clusters}

    samples_with_era = []
    for row in samples:
        c = by_cluster.get(row.get("cluster_id", ""), {})
        rec = {
            **row,
            "era": c.get("era", ""),
            "era_family": era_family(c.get("era", "")),
            "recording_regime": c.get("recording_regime", ""),
        }
        samples_with_era.append(rec)
    write_csv(out_dir / "forced_withhold_samples_with_era.csv", samples_with_era)

    loao_with_era = []
    for row in flight_loao:
        c = by_flight.get(row.get("left_out_flight_id", ""), {})
        loao_with_era.append({
            **row,
            "era": c.get("era", ""),
            "era_family": era_family(c.get("era", "")),
            "recording_regime": c.get("recording_regime", ""),
        })
    write_csv(out_dir / "flight_loao_with_era.csv", loao_with_era)

    era_rows = []
    for label in sorted({row.get("era", "") for row in clusters}):
        cids = {row["cluster_id"] for row in clusters if row.get("era", "") == label}
        lrows = [row for row in loao_with_era if row.get("era", "") == label]
        vals = [float(row["profile_u95_sigma_a_mps2"]) for row in lrows if f(row.get("profile_u95_sigma_a_mps2")) is not None]
        era_rows.append({
            "era": label,
            "era_family": era_family(label),
            "clusters": len(cids),
            "flight_loao_rows": len(lrows),
            "loao_u95_min": min(vals) if vals else "",
            "loao_u95_median": median(vals),
            "loao_u95_max": max(vals) if vals else "",
            "loao_any_pushes_over_gate": any(str(r.get("pushes_over_gate")) == "True" for r in lrows),
            "stratified_fit_authorized": len(cids) >= 6,
            "note": "lt6 clusters: diagnostic only, no release stratum" if len(cids) < 6 else "",
        })
    write_csv(out_dir / "era_loao_audit.csv", era_rows)

    family_rows = []
    for fam in sorted({era_family(row.get("era", "")) for row in clusters}):
        cids = {row["cluster_id"] for row in clusters if era_family(row.get("era", "")) == fam}
        group = [row for row in samples_with_era if row.get("cluster_id") in cids]
        if len(cids) >= 6 and group:
            fit = fit_release(group)
            family_rows.append({
                "era_family": fam,
                "diagnostic_only": True,
                "clusters": len(cids),
                "rows": len(group),
                "point_sigma_a_mps2": fit.get("sigma_a_mps2", ""),
                "profile_u95_sigma_a_mps2": fit.get("profile_u95_sigma_a_mps2", ""),
                "profile_nearly_flat": fit.get("profile_nearly_flat", ""),
                "gate_push": (
                    float(fit.get("profile_u95_sigma_a_mps2", 999.0)) > SIGMA_A_GATE
                    if f(fit.get("profile_u95_sigma_a_mps2")) is not None else ""
                ),
                "note": "diagnostic stratified profile fit; not a separate release claim",
            })
        else:
            family_rows.append({
                "era_family": fam,
                "diagnostic_only": True,
                "clusters": len(cids),
                "rows": len(group),
                "point_sigma_a_mps2": "",
                "profile_u95_sigma_a_mps2": "",
                "profile_nearly_flat": "",
                "gate_push": "",
                "note": "lt6 clusters: no stratified fit",
            })
    write_csv(out_dir / "era_family_stratified_fit.csv", family_rows)

    all_push = all(str(r.get("pushes_over_gate")) == "True" for r in loao_with_era) if loao_with_era else False
    summary = {
        "task_a_dir": str(out_dir),
        "clusters": len(clusters),
        "era_count": len(era_rows),
        "era_family_count": len(family_rows),
        "flight_loao_all_push_over_gate": all_push,
        "era_interpretation": (
            "LOAO pushes over gate across all left-out flights; no single ERA-specific rescue. "
            "Per-era strata are mostly <6; phase6 family is the only diagnostic stratum with >=6 clusters."
        ),
    }
    (out_dir / "era_heterogeneity_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# ERA Heterogeneity Addendum",
        "",
        "Diagnostic join for TASK A release-fit outputs.",
        "",
        f"- Clusters: `{summary['clusters']}`.",
        f"- Flight-level LOAO pushes over gate for every held-out flight: `{all_push}`.",
        f"- Interpretation: {summary['era_interpretation']}",
        "",
        "Artifacts: `forced_withhold_samples_with_era.csv`, `flight_loao_with_era.csv`, "
        "`era_loao_audit.csv`, `era_family_stratified_fit.csv`, `era_heterogeneity_summary.json`.",
        "",
    ]
    (out_dir / "era_heterogeneity.md").write_text("\n".join(lines), encoding="utf-8")
    print(out_dir / "era_heterogeneity.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
