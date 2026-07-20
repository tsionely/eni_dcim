"""Adjudicative regeneration report layer for RESPONSE54/55.

CSV-only and simulator-safe. This generator reads committed checkpoint
outputs from the post-criterion ordered A-G round, binds the exact input
bytes in an input manifest, and emits the fresh verdict layer required by
RESPONSE54/55.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from run_l1_perception_replay import assert_mock_safe  # noqa: E402

SOURCE_DIR = ROOT / "tuning" / "ordered-round-A-G-DIAGNOSTIC-de19d88-20260720T220957Z"
OUT_PREFIX = "adjudicative-regeneration-DIAGNOSTIC"

SHADOW_CRITERION = ROOT / "docs" / "criteria" / "shadow_fit_decision_structure.md"
WRONG_SIGN_CRITERION = ROOT / "docs" / "criteria" / "wrong_sign_rescore_equivalence.md"
SECOND_MECHANISM_CRITERION = ROOT / "docs" / "criteria" / "second_mechanism_refutation_thresholds.md"
RESPONSE54 = ROOT / "docs" / "thinktank" / "RESPONSE54.md"
RESPONSE55 = ROOT / "docs" / "thinktank" / "RESPONSE55.md"

COMPUTATION_COMMIT = "de19d881ce8fa0ddc27dd71d7306d0d366c43e90"
CHECKPOINT_EVIDENCE_COMMIT = "c19602f384bc30b0a53d649238b429f9085b6b8f"
VIEWED_OLD_OUTPUT_STATEMENT = (
    "385b7eb diagnostics and ordered A-G checkpoint outputs were viewed; "
    "this generator emits a post-criterion adjudicative report layer and "
    "does not relabel pre-criterion diagnostics."
)
FIXTURE_LEVEL_SCOPE = (
    "PASS at 1/1 is a FIXTURE-LEVEL pass (one physical approach, "
    "four correlated variants), not population evidence."
)
LEGACY_FORMULA_RECONSTRUCTED = (
    "reconstructed: cmd=terminal_vz_up_mps, e=e_meas, abs(e)>0.03, "
    "cmd*e<-1e-6; zero command has no deadband in the historical mask; "
    "reconstructs 28/68 scored trace rows"
)
NEAR_HOVER_RMS_MPS = 0.05
BOOTSTRAP_N = 2200
BOOTSTRAP_SEED = 20260720
NU = 5.0
SIGMA_A_GATE = 0.35

CHECKPOINT_FILES = [
    "02_shadow_old_vs_new_release_fit_by_set.csv",
    "02_shadow_old_vs_new_cluster_bootstrap_by_set.csv",
    "02_shadow_old_vs_new_loao_by_set.csv",
    "02_shadow_old_vs_new_balanced_coverage_by_set.csv",
    "02_shadow_b0_new_per_cluster_split.csv",
    "02_shadow_b0_exact_maxima.csv",
    "02_shadow_legacy_discovery_appendix_5_listed_4_analyzable.csv",
    "02_shadow_forced_withhold_samples.csv",
    "01_wrong_sign_definition_scorecard.csv",
    "01_wrong_sign_approach_level_rescore.csv",
    "01_wrong_sign_mask_accounting.csv",
    "01_wrong_sign_paired_common_support_events.csv",
    "01_wrong_sign_legacy_28_rows.csv",
    "01_wrong_sign_historical_zero_green_rescore.csv",
    "03_Y_eligible_by_era_with_applicability.csv",
    "03_frozen_compound_signature_2x2.csv",
    "04_old_fit_verdict_taxonomy.csv",
    "summary.json",
]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def last_commit_for(path: Path) -> str:
    return git("log", "-1", "--format=%H", "--", path.relative_to(ROOT).as_posix())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    keys: list[str] = list(fieldnames or [])
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def committed_bytes(rel_path: str, commit: str = "HEAD") -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{rel_path}"], cwd=ROOT)


def committed_sha256(rel_path: str, commit: str = "HEAD") -> str:
    return sha256_bytes(committed_bytes(rel_path, commit))


def fnum(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def mean(values: list[float]) -> float | str:
    return statistics.fmean(values) if values else ""


def rms(values: list[float]) -> float | str:
    return math.sqrt(statistics.fmean([v * v for v in values])) if values else ""


def median(values: list[float]) -> float | str:
    return statistics.median(values) if values else ""


def make_out_dir() -> tuple[str, Path]:
    head = git("rev-parse", "HEAD")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"{OUT_PREFIX}-{head[:7]}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    return head, out_dir


def lineage_packet(head: str, out_dir: Path, source_dir: Path) -> dict[str, Any]:
    created = datetime.now(timezone.utc).isoformat()
    criteria = {
        "shadow_fit_decision_structure": last_commit_for(SHADOW_CRITERION),
        "wrong_sign_rescore_equivalence": last_commit_for(WRONG_SIGN_CRITERION),
        "second_mechanism_refutation_thresholds": last_commit_for(SECOND_MECHANISM_CRITERION),
        "response54": last_commit_for(RESPONSE54),
        "response55": last_commit_for(RESPONSE55),
    }
    input_rows = []
    for name in CHECKPOINT_FILES:
        rel = (source_dir / name).relative_to(ROOT).as_posix()
        input_rows.append({
            "path": rel,
            "sha256": committed_sha256(rel, "HEAD"),
            "checkpoint_evidence_commit": CHECKPOINT_EVIDENCE_COMMIT,
        })
    input_manifest = out_dir / "checkpoint_input_manifest.json"
    write_json(input_manifest, input_rows)
    return {
        "creation_time_utc": created,
        "computation_commit": COMPUTATION_COMMIT,
        "checkpoint_evidence_commit": CHECKPOINT_EVIDENCE_COMMIT,
        "report_generator_commit": head,
        "source_checkpoint_dir": source_dir.relative_to(ROOT).as_posix(),
        "input_manifest_path": input_manifest.relative_to(ROOT).as_posix(),
        "input_manifest_sha256": sha256_file(input_manifest),
        "rng_resample_provenance": (
            f"Student-t nu={NU}; cluster_bootstrap_n={BOOTSTRAP_N}; "
            f"cluster_bootstrap_seed={BOOTSTRAP_SEED}; profile grid from "
            "archive_harvest_release_fit_v21/run_shadow_residual_diagnostics"
        ),
        "criterion_commits": criteria,
        "viewed_old_output_statement": VIEWED_OLD_OUTPUT_STATEMENT,
    }


def report_meta(packet: dict[str, Any], criterion_name: str) -> dict[str, Any]:
    return {
        "diagnostic_only": True,
        "computation_commit": packet["computation_commit"],
        "checkpoint_evidence_commit": packet["checkpoint_evidence_commit"],
        "report_generator_commit": packet["report_generator_commit"],
        "criterion_commit": packet["criterion_commits"][criterion_name],
        "creation_time_utc": packet["creation_time_utc"],
        "source_checkpoint_dir": packet["source_checkpoint_dir"],
        "input_manifest_path": packet["input_manifest_path"],
        "input_manifest_sha256": packet["input_manifest_sha256"],
        "rng_resample_provenance": packet["rng_resample_provenance"],
        "viewed_old_output_statement": packet["viewed_old_output_statement"],
    }


def copy_with_meta(src: Path, dst: Path, meta: dict[str, Any]) -> None:
    rows = []
    for row in read_csv(src):
        out = dict(meta)
        out.update(row)
        rows.append(out)
    write_csv(dst, rows)


def shadow_closure(packet: dict[str, Any], source_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    meta = report_meta(packet, "shadow_fit_decision_structure")
    copies = [
        ("shadow_closure_fit_by_set.csv", "02_shadow_old_vs_new_release_fit_by_set.csv"),
        ("shadow_closure_cluster_bootstrap_by_set.csv", "02_shadow_old_vs_new_cluster_bootstrap_by_set.csv"),
        ("shadow_closure_loao_by_set.csv", "02_shadow_old_vs_new_loao_by_set.csv"),
        ("shadow_closure_balanced_coverage_by_set.csv", "02_shadow_old_vs_new_balanced_coverage_by_set.csv"),
        ("shadow_closure_per_approach_b0.csv", "02_shadow_b0_new_per_cluster_split.csv"),
        ("shadow_closure_exact_maxima.csv", "02_shadow_b0_exact_maxima.csv"),
        ("shadow_closure_legacy_discovery_appendix.csv", "02_shadow_legacy_discovery_appendix_5_listed_4_analyzable.csv"),
    ]
    artifacts = []
    for out_name, src_name in copies:
        path = out_dir / out_name
        copy_with_meta(source_dir / src_name, path, meta)
        artifacts.append({"path": path, "criterion": "shadow_fit_decision_structure"})
    fit_rows = read_csv(out_dir / "shadow_closure_fit_by_set.csv")
    summary_rows = []
    for row in fit_rows:
        if row.get("target_set") == "confirmatory_20" and row.get("anchor_policy") == "shadow_unattenuated_anchor":
            summary_rows.append({
                **meta,
                "closure_target_set": "confirmatory_20",
                "closure_read_note": "Row-3 closure reads the registered 20-confirmatory distribution; overlap-3 and pooled-23 are context.",
                "u95_conservative_mps2": row.get("u95_conservative_mps2"),
                "cluster_bootstrap_u95_sigma_a_mps2": row.get("cluster_bootstrap_u95_sigma_a_mps2"),
                "profile_u95_sigma_a_mps2": row.get("profile_u95_sigma_a_mps2"),
                "point_sigma_a_mps2": row.get("point_sigma_a_mps2"),
                "n_clusters": row.get("n_clusters"),
                "n_rows": row.get("n_rows"),
                "gate_0p35_push": row.get("gate_0p35_push"),
                "verdict": "DO_NOT_MOVE; U95 > 0.35 under diagnostic shadow criterion",
            })
    path = out_dir / "shadow_closure_read_verdict.csv"
    write_csv(path, summary_rows)
    artifacts.append({"path": path, "criterion": "shadow_fit_decision_structure"})
    return artifacts


def wrong_sign(packet: dict[str, Any], source_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    meta = report_meta(packet, "wrong_sign_rescore_equivalence")
    score_rows = read_csv(source_dir / "01_wrong_sign_definition_scorecard.csv")
    event_rows = read_csv(source_dir / "01_wrong_sign_paired_common_support_events.csv")
    mask_rows = read_csv(source_dir / "01_wrong_sign_mask_accounting.csv")
    approach_rows = read_csv(source_dir / "01_wrong_sign_approach_level_rescore.csv")
    legacy_rows = read_csv(source_dir / "01_wrong_sign_legacy_28_rows.csv")

    def count_layer(layer: str) -> str:
        row = next((r for r in mask_rows if r.get("layer") == layer), None)
        return row.get("rows", "") if row else ""

    score_out = []
    for row in score_rows:
        out = dict(meta)
        out.update(row)
        if row.get("definition") == "legacy_harness_raw_e_meas_trace_rows":
            out["formula"] = LEGACY_FORMULA_RECONSTRUCTED
            out["historical_count_status"] = "reconstructed"
            out["historical_denominator_note"] = "28/68 scored trace rows; current event-support denominator is 9 command events"
        if row.get("definition") == "registered_needed_correction_event_support":
            out["verdict_scope_language"] = FIXTURE_LEVEL_SCOPE
            out["paired_event_key"] = "flight_id,trial,mono_ns"
        score_out.append(out)
    score_path = out_dir / "wrong_sign_verdict_rescore.csv"
    write_csv(score_path, score_out)

    event_path = out_dir / "wrong_sign_paired_event_key_rows.csv"
    write_csv(event_path, [{**meta, **r} for r in event_rows])

    support_rows = [{
        **meta,
        "physical_approaches": 1,
        "correlated_variants": 4,
        "trace_rows": count_layer("traceability_term_side_with_new_command"),
        "command_events": count_layer("command_event_support"),
        "sign_evaluable_events": count_layer("sign_evaluable_events"),
        "zero_on_support_events": count_layer("zero_neutral_on_support"),
        "legacy_formula_label": LEGACY_FORMULA_RECONSTRUCTED,
        "legacy_reconstructed_rows": len(legacy_rows),
        "registered_old_violations": next((r.get("violations") for r in score_rows if r.get("definition") == "registered_needed_correction_event_support" and r.get("path") == "old_policy_forecast"), ""),
        "registered_new_violations": next((r.get("violations") for r in score_rows if r.get("definition") == "registered_needed_correction_event_support" and r.get("path") == "new_shadow_forecast"), ""),
        "new_excess_wrong_sign_events": approach_rows[0].get("new_excess_wrong_sign_events", "") if approach_rows else "",
        "verdict_scope_language": FIXTURE_LEVEL_SCOPE,
        "verdict_unit": "command event keyed by flight_id, trial, mono_ns",
        "population_claim": "none",
    }]
    support_path = out_dir / "wrong_sign_event_support_accounting.csv"
    write_csv(support_path, support_rows)

    approach_path = out_dir / "wrong_sign_approach_level_verdict.csv"
    write_csv(approach_path, [{**meta, **r, "verdict_scope_language": FIXTURE_LEVEL_SCOPE} for r in approach_rows])
    return [
        {"path": score_path, "criterion": "wrong_sign_rescore_equivalence"},
        {"path": event_path, "criterion": "wrong_sign_rescore_equivalence"},
        {"path": support_path, "criterion": "wrong_sign_rescore_equivalence"},
        {"path": approach_path, "criterion": "wrong_sign_rescore_equivalence"},
    ]


def linreg(xs: list[float], ys: list[float]) -> tuple[float | str, float | str]:
    if len(xs) < 2 or len(ys) < 2:
        return "", ""
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return my, ""
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return my - slope * mx, slope


def prediction_table(packet: dict[str, Any], source_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    meta = report_meta(packet, "second_mechanism_refutation_thresholds")
    samples = read_csv(source_dir / "02_shadow_forced_withhold_samples.csv")
    per_cluster = read_csv(source_dir / "02_shadow_b0_new_per_cluster_split.csv")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    grouped_cut: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in samples:
        grouped[row["cluster_id"]].append(row)
        grouped_cut[(row["cluster_id"], row["cut_id"])].append(row)

    cut_rows = []
    cut_counts_by_cluster: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (cluster_id, cut_id), rows in sorted(grouped_cut.items()):
        ages = [x for x in (fnum(r.get("age_s")) for r in rows) if x is not None]
        rvs = [x for x in (fnum(r.get("r_v_new_mps")) for r in rows) if x is not None]
        activity = [x for x in (fnum(r.get("rate_feed_forward_mps")) for r in rows) if x is not None]
        b0, b1 = linreg(ages, rvs)
        activity_rms = rms(activity)
        auth_vals = [x for x in (fnum(r.get("auth_at_latch")) for r in rows) if x is not None]
        near_hover = isinstance(activity_rms, float) and activity_rms < NEAR_HOVER_RMS_MPS
        large = isinstance(b1, float) and abs(b1) > SIGMA_A_GATE
        auth1 = bool(auth_vals) and median(auth_vals) >= 0.999
        if near_hover:
            cut_counts_by_cluster[cluster_id]["near_hover_cuts"] += 1
        if near_hover and large:
            cut_counts_by_cluster[cluster_id]["near_hover_large_abs_b1_cuts"] += 1
        if near_hover and large and auth1:
            cut_counts_by_cluster[cluster_id]["refutation_candidate_cuts"] += 1
        cut_rows.append({
            **meta,
            "observation_unit": "cut",
            "cluster_id": cluster_id,
            "cut_id": cut_id,
            "n_rows": len(rows),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "auth_at_latch_median": median(auth_vals),
            "rate_feed_forward_rms_mps": activity_rms,
            "plant_signal": "rate_feed_forward_mps",
            "plant_signal_disclosure": "CSV lacks logged_applied_vz_up_mps; rate_feed_forward_mps is the replay's applied feed-forward/plant vertical input in the withheld window.",
            "near_hover_subset": near_hover,
            "near_hover_threshold_mps": NEAR_HOVER_RMS_MPS,
            "b0_new_within_cut_mps": b0,
            "b1_new_within_cut_mps2": b1,
            "abs_b1_new_within_cut_mps2": abs(b1) if isinstance(b1, float) else "",
            "large_abs_b1_threshold_mps2": SIGMA_A_GATE,
            "large_abs_b1": large,
            "auth_ge_0p999": auth1,
            "refutation_candidate_cut": near_hover and large and auth1,
            "command_regimes": ";".join(sorted({r.get("command_regime", "") for r in rows if r.get("command_regime", "")})),
            "target_set": rows[0].get("target_set", ""),
        })
    cut_path = out_dir / "prediction_table_cut_level_activity.csv"
    write_csv(cut_path, cut_rows)

    cluster_rows = []
    for row in per_cluster:
        cluster_id = row["cluster_id"]
        rows = grouped.get(cluster_id, [])
        activity = [x for x in (fnum(r.get("rate_feed_forward_mps")) for r in rows) if x is not None]
        abs_activity = [abs(x) for x in activity]
        near_activity = [x for x in activity if abs(x) < NEAR_HOVER_RMS_MPS]
        abs_b1 = abs(fnum(row.get("b1_new_mps_per_s")) or 0.0)
        old_abs_b1 = abs(fnum(row.get("b1_old_mps_per_s")) or 0.0)
        counts = cut_counts_by_cluster[cluster_id]
        cluster_rows.append({
            **meta,
            "observation_unit": "physical_approach_cluster",
            "cluster_id": cluster_id,
            "flight_id": row.get("flight_id", ""),
            "target_set": row.get("target_set", ""),
            "era": row.get("era", ""),
            "recording_regime": row.get("recording_regime", ""),
            "regime_labels": row.get("regime_labels", ""),
            "n_rows": row.get("n_rows", len(rows)),
            "n_cuts": len({r.get("cut_id") for r in rows}),
            "auth_at_latch_median": row.get("auth_at_latch_median", ""),
            "v_latch_median_mps": row.get("v_latch_median_mps", ""),
            "b1_old_mps2": row.get("b1_old_mps_per_s", ""),
            "abs_b1_old_mps2": old_abs_b1,
            "b1_new_mps2": row.get("b1_new_mps_per_s", ""),
            "abs_b1_new_mps2": abs_b1,
            "legacy_vertical_activity_rms_mps": rms(activity),
            "legacy_vertical_activity_abs_mean_mps": mean(abs_activity),
            "legacy_vertical_activity_abs_median_mps": median(abs_activity),
            "legacy_vertical_activity_max_abs_mps": max(abs_activity) if abs_activity else "",
            "near_hover_subset_rows": len(near_activity),
            "near_hover_subset_fraction": (len(near_activity) / len(activity)) if activity else "",
            "near_hover_threshold_mps": NEAR_HOVER_RMS_MPS,
            "near_hover_cluster": bool(activity) and (rms(activity) < NEAR_HOVER_RMS_MPS),
            "near_hover_cuts": counts["near_hover_cuts"],
            "near_hover_large_abs_b1_cuts": counts["near_hover_large_abs_b1_cuts"],
            "refutation_candidate_cuts": counts["refutation_candidate_cuts"],
            "plant_signal": "rate_feed_forward_mps",
            "plant_signal_disclosure": "rate_feed_forward_mps selected as the archived applied vertical plant/feed-forward stream; 0.0 is observed zero, blank/None is missing.",
            "withheld_window_timing": "rows in 02_shadow_forced_withhold_samples.csv; age_s from latch/cut to side maintenance sample; no future commands introduced by this report layer",
        })
    cluster_path = out_dir / "prediction_table_cluster_activity.csv"
    write_csv(cluster_path, cluster_rows)

    near_zero_large_clusters = [
        r for r in cluster_rows
        if r["near_hover_cluster"] and r["abs_b1_new_mps2"] > SIGMA_A_GATE and float(r["auth_at_latch_median"] or 0.0) >= 0.999
    ]
    summary_rows = [{
        **meta,
        "n_clusters": len(cluster_rows),
        "n_cuts": len(cut_rows),
        "plant_signal": "rate_feed_forward_mps",
        "near_hover_threshold_mps": NEAR_HOVER_RMS_MPS,
        "large_abs_b1_threshold_mps2": SIGMA_A_GATE,
        "near_zero_large_auth1_clusters": len(near_zero_large_clusters),
        "refutation_branch_met_by_cut_table": len({
            r["cluster_id"] for r in cut_rows
            if r["refutation_candidate_cut"]
        }) >= 2,
        "branch_note": "Correlation table is a filter only; intervention remains the judge under the criterion.",
    }]
    summary_path = out_dir / "prediction_table_summary.csv"
    write_csv(summary_path, summary_rows)
    return [
        {"path": cluster_path, "criterion": "second_mechanism_refutation_thresholds"},
        {"path": cut_path, "criterion": "second_mechanism_refutation_thresholds"},
        {"path": summary_path, "criterion": "second_mechanism_refutation_thresholds"},
    ]


def artifact_manifest(out_dir: Path, artifacts: list[dict[str, Any]], packet: dict[str, Any]) -> Path:
    rows = [{
        "artifact_path": packet["input_manifest_path"],
        "sha256": packet["input_manifest_sha256"],
        "artifact_type": "checkpoint_input_manifest",
        "criterion": "checkpoint_lineage",
    }]
    for rec in artifacts:
        path = Path(rec["path"])
        rows.append({
            "artifact_path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
            "artifact_type": rec.get("criterion", "report"),
            "criterion": rec.get("criterion", ""),
        })
    path = out_dir / "adjudicative_artifact_manifest.csv"
    write_csv(path, rows)
    return path


def run(args: argparse.Namespace) -> Path:
    assert_mock_safe()
    source_dir = args.source_dir.resolve()
    head, out_dir = make_out_dir()
    required = [
        last_commit_for(SHADOW_CRITERION),
        last_commit_for(WRONG_SIGN_CRITERION),
        last_commit_for(SECOND_MECHANISM_CRITERION),
        args.minimum_tip,
    ]
    missing = [c for c in required if c and not is_ancestor(c, head)]
    if missing:
        raise SystemExit(f"HEAD {head} does not include required ancestors: {missing}")

    packet = lineage_packet(head, out_dir, source_dir)
    artifacts = []
    artifacts.extend(shadow_closure(packet, source_dir, out_dir))
    artifacts.extend(wrong_sign(packet, source_dir, out_dir))
    artifacts.extend(prediction_table(packet, source_dir, out_dir))
    manifest_path = artifact_manifest(out_dir, artifacts, packet)

    summary = {
        "repo_head": head,
        "diagnostic_only": True,
        "csv_only_no_sim": True,
        "source_checkpoint_dir": packet["source_checkpoint_dir"],
        "input_manifest_path": packet["input_manifest_path"],
        "input_manifest_sha256": packet["input_manifest_sha256"],
        "computation_commit": packet["computation_commit"],
        "checkpoint_evidence_commit": packet["checkpoint_evidence_commit"],
        "report_generator_commit": packet["report_generator_commit"],
        "criterion_commits": packet["criterion_commits"],
        "rng_resample_provenance": packet["rng_resample_provenance"],
        "viewed_old_output_statement": packet["viewed_old_output_statement"],
        "wrong_sign_event_support": "16 trace rows -> 9 events -> 7 sign-evaluable + 2 zero-on-support",
        "legacy_formula": LEGACY_FORMULA_RECONSTRUCTED,
        "r26_1_verdict_scope": FIXTURE_LEVEL_SCOPE,
        "second_mechanism_table": "per-cluster |b1| vs rate_feed_forward_mps RMS; cut-aware near-hover refutation columns included",
        "artifact_manifest": manifest_path.relative_to(ROOT).as_posix(),
    }
    write_json(out_dir / "summary.json", summary)
    (out_dir / "summary.md").write_text(
        "\n".join([
            "# ADJUDICATIVE REGENERATION ROUND",
            "",
            "Scope: DIAGNOSTIC verdict-layer regeneration, CSV-only, no simulator launch.",
            f"Report generator commit: `{head}`.",
            f"Computation checkpoint commit: `{COMPUTATION_COMMIT}`.",
            f"Checkpoint evidence commit: `{CHECKPOINT_EVIDENCE_COMMIT}`.",
            f"Source checkpoints: `{packet['source_checkpoint_dir']}`.",
            f"Input manifest: `{packet['input_manifest_path']}`.",
            f"Input manifest sha256: `{packet['input_manifest_sha256']}`.",
            "",
            "## Shadow Closure Read",
            "",
            "Generated 3/20/23 tables from the registered split. The 20-confirmatory distribution is the closure read; overlap-3 and pooled-23 are context.",
            "",
            "## Wrong-Sign Re-Score",
            "",
            "Event support: 16 trace rows -> 9 command events -> 7 sign-evaluable + 2 zero-on-support.",
            f"Legacy formula: `{LEGACY_FORMULA_RECONSTRUCTED}`.",
            f"Verdict language: {FIXTURE_LEVEL_SCOPE}",
            "",
            "## RESPONSE55 Prediction Table",
            "",
            "Produced per-cluster and cut-level |b1| vs legacy vertical activity tables using `rate_feed_forward_mps` as the archived applied vertical stream.",
            "",
            "The artifact manifest lists output paths and SHA-256 digests.",
            "",
        ]),
        encoding="utf-8",
    )
    print(out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    ap.add_argument("--minimum-tip", default="36a9b20")
    args = ap.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
