"""Second-mechanism adjudicative update (3a-3d).

CSV-only. No replay and no simulator launch. The generator reads the
committed forced-withhold checkpoints and evaluates the registered
second-mechanism criterion:

* prediction table: cut-aware |b1| vs recorded legacy applied activity;
* intervention run: residuals before/after feeding the recorded plant
  stream into the feed-forward reference;
* A091 sentinel row;
* harness stream disclosure by era and inferred ownership state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tuning" / "ordered-round-A-G-DIAGNOSTIC-de19d88-20260720T220957Z"
OUT_PREFIX = "second-mechanism-update-DIAGNOSTIC"
LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")

SECOND_MECHANISM_CRITERION = ROOT / "docs" / "criteria" / "second_mechanism_refutation_thresholds.md"
RESPONSE55 = ROOT / "docs" / "thinktank" / "RESPONSE55.md"
RESPONSE57 = ROOT / "docs" / "thinktank" / "RESPONSE57.md"

COMPUTATION_COMMIT = "de19d881ce8fa0ddc27dd71d7306d0d366c43e90"
CHECKPOINT_EVIDENCE_COMMIT = "c19602f384bc30b0a53d649238b429f9085b6b8f"
NEAR_ZERO_RMS_MPS = 0.05
LARGE_B1_MPS2 = 0.35
AUTH_FULL = 0.999
A091_CLUSTER = "20260719T201851-50f9dcc8:A1"

CHECKPOINT_FILES = [
    "02_shadow_forced_withhold_samples.csv",
    "02_shadow_b0_new_per_cluster_split.csv",
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


def assert_mock_safe() -> None:
    if LOCK_PATH.exists():
        raise SystemExit(f"SIM lock exists; refusing CSV generation: {LOCK_PATH}")
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process FlightSim,DCGame -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty Id",
            ],
            text=True,
        )
    except subprocess.CalledProcessError:
        out = ""
    if out.strip():
        raise SystemExit(f"FlightSim/DCGame process visible; refusing CSV generation: {out.strip()}")


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
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def committed_sha256(rel_path: str, commit: str = "HEAD") -> str:
    data = subprocess.check_output(["git", "show", f"{commit}:{rel_path}"], cwd=ROOT)
    return hashlib.sha256(data).hexdigest()


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


def median(values: list[float]) -> float | str:
    return statistics.median(values) if values else ""


def rms(values: list[float]) -> float | str:
    return math.sqrt(statistics.fmean([v * v for v in values])) if values else ""


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


def owner_state(cluster_id: str, era: str, recording_regime: str, metrology_only: bool) -> tuple[str, str]:
    if metrology_only or recording_regime == "metrology":
        return "metrology_only", "metrology_only flag or metrology recording_regime"
    if cluster_id == A091_CLUSTER:
        return "physical_TERM_episode_A091", "registered single physical TERM episode"
    if "terminal" in recording_regime or recording_regime in {"r-rate-ab", "block-a", "cohort-2"}:
        return "terminal_era_not_physical_TERM_asserted", "terminal-era recording class; per-row ownership not asserted"
    return "legacy_common_arm", "legacy/common-arm recording class"


def build_packet(head: str, out_dir: Path, source_dir: Path) -> dict[str, Any]:
    inputs = []
    for name in CHECKPOINT_FILES:
        rel = (source_dir / name).relative_to(ROOT).as_posix()
        inputs.append({
            "path": rel,
            "sha256": committed_sha256(rel),
            "checkpoint_evidence_commit": CHECKPOINT_EVIDENCE_COMMIT,
        })
    input_manifest = out_dir / "checkpoint_input_manifest.json"
    write_json(input_manifest, inputs)
    return {
        "creation_time_utc": datetime.now(timezone.utc).isoformat(),
        "computation_commit": COMPUTATION_COMMIT,
        "checkpoint_evidence_commit": CHECKPOINT_EVIDENCE_COMMIT,
        "report_generator_commit": head,
        "source_checkpoint_dir": source_dir.relative_to(ROOT).as_posix(),
        "input_manifest_path": input_manifest.relative_to(ROOT).as_posix(),
        "input_manifest_sha256": sha256_file(input_manifest),
        "criterion_commit": last_commit_for(SECOND_MECHANISM_CRITERION),
        "response55_commit": last_commit_for(RESPONSE55),
        "response57_commit": last_commit_for(RESPONSE57),
        "plant_signal": "rate_feed_forward_mps",
        "plant_signal_formula": (
            "rate_feed_forward_mps = setpoint_vz_up_mps(side exposure) - "
            "setpoint_vz_up_mps(latch exposure), carried from the replay-attached "
            "flight-log setpoint stream"
        ),
        "before_formula": "r_v_before = v_ref_oracle_mps - v_latch_true_mps",
        "after_formula": "r_v_after = v_ref_oracle_mps - (v_latch_true_mps + rate_feed_forward_mps)",
    }


def meta(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_only": True,
        "computation_commit": packet["computation_commit"],
        "checkpoint_evidence_commit": packet["checkpoint_evidence_commit"],
        "report_generator_commit": packet["report_generator_commit"],
        "criterion_commit": packet["criterion_commit"],
        "creation_time_utc": packet["creation_time_utc"],
        "source_checkpoint_dir": packet["source_checkpoint_dir"],
        "input_manifest_path": packet["input_manifest_path"],
        "input_manifest_sha256": packet["input_manifest_sha256"],
    }


def enriched_samples(source_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    samples = read_csv(source_dir / "02_shadow_forced_withhold_samples.csv")
    clusters = {r["cluster_id"]: r for r in read_csv(source_dir / "02_shadow_b0_new_per_cluster_split.csv")}
    out = []
    for row in samples:
        cluster = clusters.get(row["cluster_id"], {})
        v_ref = fnum(row.get("v_ref_oracle_mps"))
        v_latch = fnum(row.get("v_latch_true_mps"))
        legacy_ff = fnum(row.get("rate_feed_forward_mps")) or 0.0
        before = v_ref - v_latch if v_ref is not None and v_latch is not None else ""
        after = v_ref - (v_latch + legacy_ff) if v_ref is not None and v_latch is not None else ""
        checkpoint_after = fnum(row.get("r_v_new_mps"))
        out.append({
            **row,
            "era": cluster.get("era", ""),
            "recording_regime": cluster.get("recording_regime", ""),
            "owner_state": owner_state(
                row["cluster_id"],
                cluster.get("era", ""),
                cluster.get("recording_regime", ""),
                str(row.get("metrology_only", "")).lower() == "true",
            )[0],
            "recorded_legacy_applied_vertical_mps": legacy_ff,
            "r_v_before_no_legacy_mps": before,
            "r_v_after_recorded_legacy_mps": after,
            "checkpoint_r_v_new_mps": checkpoint_after if checkpoint_after is not None else "",
            "after_matches_checkpoint": (
                abs(after - checkpoint_after) <= 1e-9
                if isinstance(after, float) and checkpoint_after is not None else ""
            ),
            "residual_before_formula": "v_ref_oracle_mps - v_latch_true_mps",
            "residual_after_formula": "v_ref_oracle_mps - (v_latch_true_mps + rate_feed_forward_mps)",
        })
    return out, clusters


def cut_rows(packet: dict[str, Any], samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        grouped[(row["cluster_id"], row["cut_id"])].append(row)
    rows = []
    for (cluster_id, cut_id), group in sorted(grouped.items()):
        ages = [x for x in (fnum(r.get("age_s")) for r in group) if x is not None]
        before_vals = [x for x in (fnum(r.get("r_v_before_no_legacy_mps")) for r in group) if x is not None]
        after_vals = [x for x in (fnum(r.get("r_v_after_recorded_legacy_mps")) for r in group) if x is not None]
        activity = [x for x in (fnum(r.get("recorded_legacy_applied_vertical_mps")) for r in group) if x is not None]
        auth_vals = [x for x in (fnum(r.get("auth_at_latch")) for r in group) if x is not None]
        b0_before, b1_before = linreg(ages, before_vals)
        b0_after, b1_after = linreg(ages, after_vals)
        activity_rms = rms(activity)
        near_zero = isinstance(activity_rms, float) and activity_rms < NEAR_ZERO_RMS_MPS
        large_before = isinstance(b1_before, float) and abs(b1_before) > LARGE_B1_MPS2
        large_after = isinstance(b1_after, float) and abs(b1_after) > LARGE_B1_MPS2
        auth_median = median(auth_vals)
        auth_full = isinstance(auth_median, float) and auth_median >= AUTH_FULL
        rows.append({
            **meta(packet),
            "observation_unit": "cut",
            "cluster_id": cluster_id,
            "cut_id": cut_id,
            "flight_id": group[0].get("flight_id", ""),
            "era": group[0].get("era", ""),
            "recording_regime": group[0].get("recording_regime", ""),
            "owner_state": group[0].get("owner_state", ""),
            "command_regimes": ";".join(sorted({r.get("command_regime", "") for r in group if r.get("command_regime", "")})),
            "n_rows": len(group),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "auth_at_latch_median": auth_median,
            "auth_ge_0p999": auth_full,
            "legacy_activity_rms_mps": activity_rms,
            "near_zero_legacy_activity": near_zero,
            "near_zero_threshold_mps": NEAR_ZERO_RMS_MPS,
            "b0_before_no_legacy_mps": b0_before,
            "b1_before_no_legacy_mps2": b1_before,
            "abs_b1_before_no_legacy_mps2": abs(b1_before) if isinstance(b1_before, float) else "",
            "large_b1_before": large_before,
            "b0_after_recorded_legacy_mps": b0_after,
            "b1_after_recorded_legacy_mps2": b1_after,
            "abs_b1_after_recorded_legacy_mps2": abs(b1_after) if isinstance(b1_after, float) else "",
            "large_b1_after": large_after,
            "large_b1_threshold_mps2": LARGE_B1_MPS2,
            "prediction_filter_refutation_cut": auth_full and near_zero and large_before,
            "plant_signal": packet["plant_signal"],
            "before_formula": packet["before_formula"],
            "after_formula": packet["after_formula"],
            "table_role": "FILTER_ONLY",
        })
    return rows


def cluster_rows(packet: dict[str, Any], samples: list[dict[str, Any]],
                 cuts: list[dict[str, Any]], clusters: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    samples_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cuts_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        samples_by_cluster[row["cluster_id"]].append(row)
    for row in cuts:
        cuts_by_cluster[row["cluster_id"]].append(row)
    rows = []
    for cluster_id in sorted(samples_by_cluster):
        group = samples_by_cluster[cluster_id]
        cluster = clusters.get(cluster_id, {})
        activity = [x for x in (fnum(r.get("recorded_legacy_applied_vertical_mps")) for r in group) if x is not None]
        ages = [x for x in (fnum(r.get("age_s")) for r in group) if x is not None]
        before_vals = [x for x in (fnum(r.get("r_v_before_no_legacy_mps")) for r in group) if x is not None]
        after_vals = [x for x in (fnum(r.get("r_v_after_recorded_legacy_mps")) for r in group) if x is not None]
        _, pooled_b1_before = linreg(ages, before_vals)
        _, pooled_b1_after = linreg(ages, after_vals)
        cut_group = cuts_by_cluster[cluster_id]
        before_cut_abs = [
            fnum(r.get("abs_b1_before_no_legacy_mps2")) for r in cut_group
            if fnum(r.get("abs_b1_before_no_legacy_mps2")) is not None
        ]
        after_cut_abs = [
            fnum(r.get("abs_b1_after_recorded_legacy_mps2")) for r in cut_group
            if fnum(r.get("abs_b1_after_recorded_legacy_mps2")) is not None
        ]
        activity_rms = rms(activity)
        state, basis = owner_state(
            cluster_id,
            cluster.get("era", ""),
            cluster.get("recording_regime", ""),
            str(group[0].get("metrology_only", "")).lower() == "true",
        )
        rows.append({
            **meta(packet),
            "observation_unit": "physical_approach_cluster",
            "cluster_id": cluster_id,
            "flight_id": group[0].get("flight_id", ""),
            "flight": group[0].get("flight", ""),
            "fixture_dir": group[0].get("fixture_dir", ""),
            "era": cluster.get("era", ""),
            "recording_regime": cluster.get("recording_regime", ""),
            "owner_state": state,
            "owner_inference_basis": basis,
            "target_set": group[0].get("target_set", ""),
            "regime_labels": cluster.get("regime_labels", ""),
            "n_rows": len(group),
            "n_cuts": len(cut_group),
            "auth_at_latch_median": cluster.get("auth_at_latch_median", ""),
            "delta_latch_median_mps": median([x for x in (fnum(r.get("delta_latch_mps")) for r in group) if x is not None]),
            "legacy_activity_rms_mps": activity_rms,
            "legacy_activity_abs_mean_mps": mean([abs(x) for x in activity]),
            "legacy_activity_abs_median_mps": median([abs(x) for x in activity]),
            "legacy_activity_max_abs_mps": max([abs(x) for x in activity]) if activity else "",
            "near_zero_legacy_activity": isinstance(activity_rms, float) and activity_rms < NEAR_ZERO_RMS_MPS,
            "pooled_b1_before_no_legacy_mps2": pooled_b1_before,
            "pooled_abs_b1_before_no_legacy_mps2": abs(pooled_b1_before) if isinstance(pooled_b1_before, float) else "",
            "pooled_b1_after_recorded_legacy_mps2": pooled_b1_after,
            "pooled_abs_b1_after_recorded_legacy_mps2": abs(pooled_b1_after) if isinstance(pooled_b1_after, float) else "",
            "max_abs_within_cut_b1_before_mps2": max(before_cut_abs) if before_cut_abs else "",
            "median_abs_within_cut_b1_before_mps2": median(before_cut_abs),
            "max_abs_within_cut_b1_after_mps2": max(after_cut_abs) if after_cut_abs else "",
            "median_abs_within_cut_b1_after_mps2": median(after_cut_abs),
            "large_cluster_before": bool(before_cut_abs) and max(before_cut_abs) > LARGE_B1_MPS2,
            "large_cluster_after": bool(after_cut_abs) and max(after_cut_abs) > LARGE_B1_MPS2,
            "refutation_candidate_cuts_before": sum(1 for r in cut_group if str(r.get("prediction_filter_refutation_cut")) == "True"),
            "plant_signal": packet["plant_signal"],
            "plant_signal_formula": packet["plant_signal_formula"],
            "table_role": "FILTER_ONLY for prediction columns; INTERVENTION_JUDGE for after columns",
        })
    return rows


def stream_disclosure(packet: dict[str, Any], samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        key = (
            row.get("era", ""),
            row.get("recording_regime", ""),
            row.get("owner_state", ""),
            row.get("command_regime", ""),
        )
        groups[key].append(row)
    rows = []
    for (era, regime, state, command_regime), group in sorted(groups.items()):
        activity = [x for x in (fnum(r.get("recorded_legacy_applied_vertical_mps")) for r in group) if x is not None]
        rows.append({
            **meta(packet),
            "era": era,
            "recording_regime": regime,
            "owner_state": state,
            "command_regime": command_regime,
            "clusters": len({r["cluster_id"] for r in group}),
            "rows": len(group),
            "plant_signal_fed_as_applied": packet["plant_signal"],
            "plant_signal_formula": packet["plant_signal_formula"],
            "command_semantics": "0.0 is observed zero activity; blank/None is missing; no truthiness filter used",
            "timing": "withheld-window samples only; feed-forward is exposure-aligned side minus latch setpoint; no future-command leakage added by this CSV pass",
            "runtime_model_scope": "archive replay/evaluation-side intervention, not a shipping flight-code change",
            "per_row_owner_logged": False,
            "mixed_ownership_handling": "physical TERM A091 separated; terminal-era/non-TERM/metrology states grouped separately; command_regime split prevents flattening mixed command windows",
            "activity_rms_mps": rms(activity),
            "activity_abs_mean_mps": mean([abs(x) for x in activity]),
            "activity_max_abs_mps": max([abs(x) for x in activity]) if activity else "",
        })
    return rows


def summarize(packet: dict[str, Any], clusters: list[dict[str, Any]], cuts: list[dict[str, Any]]) -> dict[str, Any]:
    large_before = [r for r in clusters if str(r.get("large_cluster_before")) == "True"]
    large_after = [r for r in clusters if str(r.get("large_cluster_after")) == "True"]
    near_zero = [r for r in clusters if str(r.get("near_zero_legacy_activity")) == "True"]
    near_zero_after_large = [
        r for r in near_zero
        if isinstance(fnum(r.get("max_abs_within_cut_b1_after_mps2")), float)
        and fnum(r.get("max_abs_within_cut_b1_after_mps2")) > LARGE_B1_MPS2
    ]
    refutation_clusters = sorted({
        r["cluster_id"] for r in cuts
        if str(r.get("prediction_filter_refutation_cut")) == "True"
    })
    fell_by_half = len(large_after) <= (len(large_before) / 2.0)
    all_near_zero_ok = len(near_zero_after_large) == 0
    confirmed = fell_by_half and all_near_zero_ok
    return {
        "diagnostic_only": True,
        "criterion_commit": packet["criterion_commit"],
        "report_generator_commit": packet["report_generator_commit"],
        "n_clusters": len(clusters),
        "n_cuts": len(cuts),
        "prediction_refutation_candidate_clusters": refutation_clusters,
        "prediction_refutation_branch_met": len(refutation_clusters) >= 2,
        "large_cluster_count_before": len(large_before),
        "large_cluster_count_after": len(large_after),
        "large_count_fell_by_half": fell_by_half,
        "near_zero_cluster_count": len(near_zero),
        "near_zero_after_large_count": len(near_zero_after_large),
        "intervention_collapse_condition_met": confirmed,
        "registered_intervention_verdict": (
            "CONFIRMED" if confirmed else "REFUTED_OR_NOT_CONFIRMED_UNDER_REGISTERED_COLLAPSE_CONDITION"
        ),
        "post_intervention_residual_admissible_input": "post_intervention_residual_samples.csv:r_v_after_recorded_legacy_mps",
        "plant_signal": packet["plant_signal"],
        "plant_signal_formula": packet["plant_signal_formula"],
    }


def run(args: argparse.Namespace) -> Path:
    assert_mock_safe()
    head = git("rev-parse", "HEAD")
    criterion_commit = last_commit_for(SECOND_MECHANISM_CRITERION)
    if not is_ancestor(args.minimum_tip, head):
        raise SystemExit(f"HEAD {head} does not include requested tip {args.minimum_tip}")
    if not is_ancestor(criterion_commit, head):
        raise SystemExit(f"HEAD {head} does not include criterion {criterion_commit}")
    source_dir = args.source_dir.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"{OUT_PREFIX}-{head[:7]}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    packet = build_packet(head, out_dir, source_dir)
    samples, cluster_meta = enriched_samples(source_dir)
    cuts = cut_rows(packet, samples)
    clusters = cluster_rows(packet, samples, cuts, cluster_meta)
    disclosure = stream_disclosure(packet, samples)
    summary = summarize(packet, clusters, cuts)

    sample_out = []
    for row in samples:
        sample_out.append({
            **meta(packet),
            "cluster_id": row["cluster_id"],
            "cut_id": row["cut_id"],
            "frame_id": row["frame_id"],
            "feature_ts_ns": row["feature_ts_ns"],
            "age_s": row["age_s"],
            "era": row.get("era", ""),
            "recording_regime": row.get("recording_regime", ""),
            "owner_state": row.get("owner_state", ""),
            "command_regime": row.get("command_regime", ""),
            "v_ref_oracle_mps": row.get("v_ref_oracle_mps", ""),
            "v_latch_true_mps": row.get("v_latch_true_mps", ""),
            "recorded_legacy_applied_vertical_mps": row.get("recorded_legacy_applied_vertical_mps", ""),
            "r_v_before_no_legacy_mps": row.get("r_v_before_no_legacy_mps", ""),
            "r_v_after_recorded_legacy_mps": row.get("r_v_after_recorded_legacy_mps", ""),
            "after_matches_checkpoint": row.get("after_matches_checkpoint", ""),
            "plant_signal": packet["plant_signal"],
        })
    a091 = [r for r in clusters if r["cluster_id"] == A091_CLUSTER]
    a091_out = []
    if a091:
        row = a091[0]
        b0_old = fnum(cluster_meta[A091_CLUSTER].get("b0_old_mps"))
        b0_new = fnum(cluster_meta[A091_CLUSTER].get("b0_new_mps"))
        auth = fnum(row.get("auth_at_latch_median"))
        reading_rule = (
            auth is not None and auth >= AUTH_FULL
            and b0_old is not None and b0_new is not None
            and abs(b0_old - b0_new) <= 1e-9
            and -0.46 <= b0_new <= -0.42
        )
        a091_out.append({
            **meta(packet),
            "cluster_id": A091_CLUSTER,
            "flight_id": row.get("flight_id", ""),
            "era": row.get("era", ""),
            "recording_regime": row.get("recording_regime", ""),
            "owner_state": row.get("owner_state", ""),
            "auth_at_latch": row.get("auth_at_latch_median", ""),
            "delta_latch": row.get("delta_latch_median_mps", ""),
            "b0_old": cluster_meta[A091_CLUSTER].get("b0_old_mps", ""),
            "b0_new": cluster_meta[A091_CLUSTER].get("b0_new_mps", ""),
            "b1": cluster_meta[A091_CLUSTER].get("b1_new_mps_per_s", ""),
            "recorded_TERM_activity_rms_mps": row.get("legacy_activity_rms_mps", ""),
            "recorded_TERM_activity_abs_mean_mps": row.get("legacy_activity_abs_mean_mps", ""),
            "recorded_TERM_activity_max_abs_mps": row.get("legacy_activity_max_abs_mps", ""),
            "committed_reading_rule_fires": reading_rule,
            "reading_rule": "auth~1 and b0_new~b0_old~-0.44 re-attributes founding -0.437 away from latch attenuation",
        })

    write_csv(out_dir / "prediction_thresholds_cut.csv", cuts)
    write_csv(out_dir / "prediction_thresholds_cluster.csv", clusters)
    write_csv(out_dir / "intervention_cut_b1_before_after.csv", cuts)
    write_csv(out_dir / "intervention_cluster_b1_before_after.csv", clusters)
    write_csv(out_dir / "post_intervention_residual_samples.csv", sample_out)
    write_csv(out_dir / "a091_sentinel_row.csv", a091_out)
    write_csv(out_dir / "harness_stream_disclosure.csv", disclosure)
    write_json(out_dir / "summary.json", summary)
    write_text(
        out_dir / "summary.md",
        "\n".join([
            "# Second-Mechanism Update",
            "",
            "Scope: DIAGNOSTIC, CSV-only; no FlightSim/DCGame launch.",
            f"Report generator commit: `{head}`.",
            f"Criterion commit: `{packet['criterion_commit']}`.",
            f"Input manifest: `{packet['input_manifest_path']}`.",
            f"Input manifest sha256: `{packet['input_manifest_sha256']}`.",
            "",
            "## Prediction Filter",
            "",
            f"Refutation candidate clusters: `{summary['prediction_refutation_candidate_clusters']}`.",
            f"Prediction filter branch met: `{summary['prediction_refutation_branch_met']}`.",
            "",
            "## Intervention Judge",
            "",
            f"Large cluster count before: `{summary['large_cluster_count_before']}`.",
            f"Large cluster count after: `{summary['large_cluster_count_after']}`.",
            f"Collapse condition met: `{summary['intervention_collapse_condition_met']}`.",
            f"Registered intervention verdict: `{summary['registered_intervention_verdict']}`.",
            "",
            "## A091 Sentinel",
            "",
            "See `a091_sentinel_row.csv` for full columns and committed reading-rule result.",
            "",
        ]) + "\n",
    )

    manifest_rows = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            manifest_rows.append({
                "artifact_path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
            })
    write_csv(out_dir / "artifact_manifest.csv", manifest_rows)
    print(out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    ap.add_argument("--minimum-tip", default="20e01e2")
    args = ap.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
