"""Synthetic fixtures for the REG-1v2 calibration source generator."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tuning.reg1v2_calibration_source_generator import (
    Candidate,
    DT_NS,
    RowsScoredCommonMismatch,
    SOURCE_GENERATOR_PATH,
    STEP_FLOOR_MPS,
    StepWindow,
    assert_rows_scored_common,
    candidate_score,
    committed_attestation_rows,
    detect_step_windows,
    fit_response_model,
    local_open_face,
    normalize_rows_with_metadata,
    parse_certified_full,
    predict_window,
    reconstruct_v_full_raw,
    source_bytes_commit,
    synthetic_dry_run,
    synthetic_null_rows,
    synthetic_rows,
)


class FixtureFailure(AssertionError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureFailure(message)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_generator_cli(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo / SOURCE_GENERATOR_PATH), "--repo", str(repo), *args],
        cwd=repo,
        text=True,
        capture_output=True,
    )


def sentinel_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_step_detector_floor_merge_and_windows() -> None:
    rows = synthetic_rows()
    windows = detect_step_windows(rows)
    expect(len(windows) == 2, f"expected two merged step windows, got {len(windows)}")
    expect([w.direction for w in windows] == ["up", "down"], "detected directions mismatch")
    expect(windows[0].tick == 20 and windows[1].tick == 50, "step ticks mismatch")
    expect(len(windows[0].post_ticks) == 30, "first window did not truncate at any-direction transition")
    expect(len(windows[1].post_ticks) == 50, "second window did not cap at 1.0s/50 ticks")
    expect(STEP_FLOOR_MPS == 0.35, "command-domain step floor changed")

    merge_rows = synthetic_rows()
    for row in merge_rows:
        tick = int(row["tick"])
        if tick == 21:
            row["v_ref_up_mps"] = 0.90
        elif 22 <= tick < 50:
            row["v_ref_up_mps"] = 0.90
    merged = detect_step_windows(merge_rows)
    expect(merged[0].tick == 20, "consecutive qualifying steps did not merge to the first tick")
    expect(sum(1 for w in merged if 20 <= w.tick <= 21) == 1, "consecutive step merge emitted duplicate windows")


def fixture_response_reconstruction_minima() -> None:
    rows = synthetic_rows()
    rate, status, meta = reconstruct_v_full_raw(rows, 1.00)
    expect(status == "VALID", f"synthetic response was not valid: {status}")
    expect(abs(float(rate) - 0.25) < 1e-12, "Theil-Sen response reconstruction mismatch")
    expect(meta["fresh_tail_samples"] >= 4, "fresh-tail sample minimum was not met")
    expect(meta["recent_samples"] <= 12 and meta["last_sample_cap"] == 12, "last-12 cap metadata missing")

    short_rate, short_status, short_meta = reconstruct_v_full_raw(rows[:3], 0.04)
    expect(short_rate is None, "insufficient history returned a rate")
    expect(short_status == "ABSENT_RESPONSE", "insufficient history did not type ABSENT_RESPONSE")
    expect(short_meta["fresh_tail_samples"] < 4, "short-history fixture did not exercise sample minimum")


def fixture_response_reconstruction_v21_runtime_rules() -> None:
    dense: list[dict[str, object]] = []
    for i in range(25):
        ts = i * 0.02
        if ts <= 0.24:
            e_meas = 1.75 - 0.05 * ts
        else:
            e_meas = 1.75 - 0.05 * 0.24 - 0.35 * (ts - 0.24)
        dense.append({"tick": i, "ts_s": ts, "feature_ts_ns": int(round(ts * 1_000_000_000)), "e_meas_m": e_meas, "certified_full": True})
    dense_rate, dense_status, dense_meta = reconstruct_v_full_raw(dense, 0.48)
    expect(dense_status == "VALID", f"dense v2.1 reconstruction invalid: {dense_status}")
    expect(abs(float(dense_rate) - 0.35) < 1e-12, "dense fixture did not use the last-12 cap")
    expect(dense_meta["history_samples"] == 25 and dense_meta["recent_samples"] == 12, "dense fixture did not expose >12 history")

    gapped: list[dict[str, object]] = []
    for i, ts in enumerate([0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34]):
        gapped.append({"tick": i, "ts_s": ts, "feature_ts_ns": int(round(ts * 1_000_000_000)), "e_meas_m": 3.0 - 0.65 * ts, "certified_full": True})
    for i, ts in enumerate([0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68], start=20):
        gapped.append({"tick": i, "ts_s": ts, "feature_ts_ns": int(round(ts * 1_000_000_000)), "e_meas_m": 1.2 - 0.12 * (ts - 0.50), "certified_full": True})
    gap_rate, gap_status, gap_meta = reconstruct_v_full_raw(gapped, 0.68)
    expect(gap_status == "VALID", f"gapped v2.1 reconstruction invalid: {gap_status}")
    expect(abs(float(gap_rate) - 0.12) < 1e-12, "gapped fixture fitted across an outage")
    expect(gap_meta["history_samples"] == 19 and gap_meta["fresh_tail_samples"] == 10, "fresh-tail outage accounting drifted")

    duplicate: list[dict[str, object]] = []
    for i in range(18):
        ts = i * 0.02
        duplicate.append({"tick": i, "ts_s": ts, "feature_ts_ns": int(round(ts * 1_000_000_000)), "e_meas_m": 1.5 - 0.22 * ts, "certified_full": True})
        if i == 10:
            duplicate.append({"tick": 1000, "ts_s": ts, "feature_ts_ns": int(round(ts * 1_000_000_000)), "e_meas_m": 99.0, "certified_full": True})
    dup_rate, dup_status, dup_meta = reconstruct_v_full_raw(duplicate, 0.34)
    expect(dup_status == "VALID", f"duplicate v2.1 reconstruction invalid: {dup_status}")
    expect(abs(float(dup_rate) - 0.22) < 1e-12, "duplicate timestamp was treated as a new exposure")
    expect(dup_meta["history_samples"] == 18, "duplicate timestamp was not rejected from unique history")

    subspan = [
        {"tick": 0, "ts_s": 0.00, "feature_ts_ns": 0, "e_meas_m": 1.00, "certified_full": True},
        {"tick": 1, "ts_s": 0.02, "feature_ts_ns": 20_000_000, "e_meas_m": 0.99, "certified_full": True},
        {"tick": 2, "ts_s": 0.04, "feature_ts_ns": 40_000_000, "e_meas_m": 0.98, "certified_full": True},
        {"tick": 3, "ts_s": 0.06, "feature_ts_ns": 60_000_000, "e_meas_m": 0.97, "certified_full": True},
    ]
    sub_rate, sub_status, sub_meta = reconstruct_v_full_raw(subspan, 0.06)
    expect(sub_status == "VALID", f"sub-span exact-_slope_of fixture returned {sub_status}")
    expect(abs(float(sub_rate) - 0.5) < 1e-12, "sub-span fixture added a non-runtime span gate")
    expect(0.0 < sub_meta["fresh_tail_span_s"] < 0.15, "sub-span fixture did not exercise the removed span gate")


def _manual_window_for_lag_objective() -> StepWindow:
    rows: list[dict[str, object]] = []
    l0_pred = predict_window(
        StepWindow("tmp", 0, "up", 0.0, 1.0, 0.0, list(range(20)), [], ""),
        Candidate(g=1.0, tau_s=0.04, lag_ticks=0),
    )
    l10_pred = predict_window(
        StepWindow("tmp", 0, "up", 0.0, 1.0, 0.0, list(range(20)), [], ""),
        Candidate(g=1.0, tau_s=0.04, lag_ticks=10),
    )
    for tick in range(20):
        meas = l0_pred[tick] if tick < 10 else l10_pred[tick]
        rows.append({
            "event_id": "objective_step",
            "row_key": f"objective_{tick:03d}",
            "tick": tick,
            "relative_tick": tick,
            "ts_s": tick * 0.02,
            "feature_ts_ns": tick * 20_000_000,
            "v_ref_up_mps": 1.0,
            "v_meas_mps": meas,
            "response_status": "VALID",
            "trace_complete": True,
        })
    return StepWindow("objective_step", 0, "up", 0.0, 1.0, 0.0, list(range(20)), rows, "")


def _retired_candidate_specific_sse(window: StepWindow, candidate: Candidate) -> float:
    preds = predict_window(window, candidate)
    total = 0.0
    for row in window.rows:
        rel_tick = int(row["relative_tick"])
        if rel_tick < candidate.lag_ticks:
            continue
        total += (float(row["v_meas_mps"]) - preds[int(row["tick"])]) ** 2
    return total


def fixture_common_support_objective_bites() -> None:
    window = _manual_window_for_lag_objective()
    c0 = Candidate(g=1.0, tau_s=0.04, lag_ticks=0)
    c10 = Candidate(g=1.0, tau_s=0.04, lag_ticks=10)
    new0 = candidate_score([window], c0)
    new10 = candidate_score([window], c10)
    retired0 = _retired_candidate_specific_sse(window, c0)
    retired10 = _retired_candidate_specific_sse(window, c10)
    expect(new0["rows_used"] == new10["rows_used"] == 20, "common-support scoring used candidate-dependent row counts")
    expect(new0["rows_scored_common"] == new10["rows_scored_common"] == 20, "rows_scored_common tripwire was not fixed")
    expect(float(new0["sse"]) < float(new10["sse"]), "common-support scoring did not select the registered lag")
    expect(retired10 < retired0, "fixture does not expose the retired candidate-specific censoring bug")

    fit = fit_response_model([window])
    score_counts = {row["rows_scored_common"] for row in fit["score_rows"]}
    expect(score_counts == {20}, f"artifact-level rows_scored_common mismatch: {score_counts}")
    expect(fit["rows_scored_common"] == 20, "fit summary did not publish rows_scored_common")


def fixture_rows_scored_common_corruption_stops() -> None:
    window = _manual_window_for_lag_objective()
    fit = fit_response_model([window])
    corrupted = [dict(row) for row in fit["score_rows"]]
    expect(corrupted, "no candidate rows available to corrupt")
    corrupted[0]["rows_scored_common"] = int(corrupted[0]["rows_scored_common"]) + 1
    try:
        assert_rows_scored_common(corrupted)
    except RowsScoredCommonMismatch as exc:
        expect(exc.code == "ROWS_SCORED_COMMON_MISMATCH", "rows_scored_common mismatch did not carry typed code")
    else:
        raise FixtureFailure("corrupted rows_scored_common candidate support did not STOP")


def fixture_post_lag_identifiability_gating() -> None:
    windows = detect_step_windows(synthetic_rows())
    high_tau = candidate_score(windows, Candidate(g=0.5, tau_s=1.20, lag_ticks=0))
    expect(high_tau["eligible"] is False, "tau longer than observed post-lag horizon should be ineligible")
    expect(high_tau["candidate_type"] == "UNIDENTIFIABLE", "ineligible candidate did not carry UNIDENTIFIABLE type")
    expect(high_tau["failing_rule"] == "HORIZON_LT_TAU", "horizon gate reason mismatch")

    lag_horizon = candidate_score(windows, Candidate(g=0.5, tau_s=0.50, lag_ticks=25))
    expect(lag_horizon["post_lag_rows"] >= 8, "large-lag fixture failed to retain post-lag rows")
    expect(lag_horizon["eligible"] is False, "large-lag short post-lag horizon should be ineligible")
    expect(lag_horizon["failing_rule"] == "HORIZON_LT_TAU", "post-lag horizon gate reason mismatch")

    too_late = candidate_score(windows, Candidate(g=0.5, tau_s=0.02, lag_ticks=25))
    expect(too_late["rows_used"] >= too_late["post_lag_rows"], "scoring and post-lag support were conflated")


def fixture_null_model_and_grid() -> None:
    windows = detect_step_windows(synthetic_null_rows())
    fit = fit_response_model(windows)
    expect(fit["candidate_count"] == 31 * 60 * 26, "grid candidate count mismatch")
    expect(fit["null_model_score"] is not None, "null-model score missing")
    expect(fit["calibration_status"] == "NULL_CALIBRATED", f"zero response should be NULL_CALIBRATED, got {fit['calibration_status']}")
    expect(float(fit["best"]["g"]) == 0.0, "null-calibrated best did not land at g=0")


def fixture_null_tie_not_null_calibrated() -> None:
    rows = []
    for tick in range(20):
        rows.append({
            "event_id": "null_tie",
            "row_key": f"null_tie_{tick:03d}",
            "tick": tick,
            "relative_tick": tick,
            "ts_s": tick * 0.02,
            "feature_ts_ns": tick * 20_000_000,
            "v_ref_up_mps": 0.0,
            "v_meas_mps": 0.0,
            "response_status": "VALID",
            "trace_complete": True,
        })
    window = StepWindow("null_tie", 0, "up", 0.0, 0.0, 0.0, list(range(20)), rows, "")
    fit = fit_response_model([window])
    expect(fit["calibration_status"] == "NOT_IDENTIFIED", f"null tie must be NOT_IDENTIFIED, got {fit['calibration_status']}")
    expect(fit["null_tied_positive"] is True, "null-tie diagnostic flag missing")


def fixture_direction_applicability() -> None:
    windows = detect_step_windows(synthetic_rows())
    fit_up = fit_response_model(windows, {"up"})
    expect(fit_up["detected_directions"] == ["down", "up"], "detected direction inventory missing a direction")
    expect(fit_up["fit_directions"] == ["up"], "fit direction binding mismatch")


def fixture_row_level_trace() -> None:
    windows = detect_step_windows(synthetic_rows())
    rows = [row for w in windows for row in w.rows if row["response_status"] == "VALID"]
    expect(rows, "no valid synthetic rows for trace fixture")
    expect(all(row["trace_complete"] for row in rows), "row-level owner/actuation trace incomplete")
    for row in rows[:3]:
        for field in ("planner_phase", "term_owner_state", "arbiter_vertical_source", "adapter_input_v_body_z", "post_limit_command_v_body_z", "clip_status"):
            expect(field in row, f"trace field {field} missing")


def fixture_sentinel_disjoint_exclusion() -> None:
    rows = synthetic_rows()
    windows = detect_step_windows(rows, sentinel_keys={"syn_0020"})
    expect(windows[0].exclusion_reason == "SENTINEL_DISJOINT", "sentinel key did not exclude overlapping window")
    fit = fit_response_model(windows)
    expect(fit["usable_window_count"] == 1, "sentinel-excluded window leaked into usable fit set")


def fixture_s4_strict_certified_full_parsing() -> None:
    rows: list[dict[str, object]] = []
    for i, raw in enumerate(["False", "0", "", "invalid"]):
        rows.append({
            "row_key": f"cert_{i}",
            "tick": i,
            "ts_s": i * 0.02,
            "feature_ts_ns": i * DT_NS,
            "e_meas_m": 2.0 - i * 0.01,
            "certified_full": raw,
        })
    parsed = [parse_certified_full(row["certified_full"])[0] for row in rows]
    expect(parsed == [False, False, None, None], f"strict certification parser drifted: {parsed}")
    normalized, meta = normalize_rows_with_metadata(rows)
    expect([row["certified_full_parsed"] for row in normalized] == [False, False, None, None], "normalization defaulted certification")
    expect(len(meta["absent_certification_rows"]) == 2, "blank/invalid certification rows not listed")
    rate, status, _meta = reconstruct_v_full_raw(normalized, 0.06)
    expect(rate is None and status == "ABSENT_RESPONSE", "uncertified/false exposures entered response history")


def fixture_s5_poisoned_duplicate_first_wins() -> None:
    rows: list[dict[str, object]] = []
    for i in range(16):
        ts = i * 0.02
        rows.append({
            "row_key": f"dup_{i:03d}",
            "tick": i,
            "ts_s": ts,
            "feature_ts_ns": i * DT_NS,
            "e_meas_m": 1.5 - 0.31 * ts,
            "certified_full": "True",
        })
        if i == 8:
            rows.append({
                "row_key": "dup_poison",
                "tick": i,
                "ts_s": ts,
                "feature_ts_ns": i * DT_NS,
                "e_meas_m": 99.0,
                "certified_full": "True",
            })
    normalized, meta = normalize_rows_with_metadata(rows)
    expect(meta["discarded_rebroadcast_count"] == 1, "poisoned duplicate was not listed as discarded")
    expect(meta["discarded_rebroadcasts"][0]["discarded_row_key"] == "dup_poison", "duplicate first-wins discarded the wrong row")
    rate, status, rate_meta = reconstruct_v_full_raw(normalized, 0.30)
    expect(status == "VALID", f"duplicate fixture response invalid: {status}")
    expect(abs(float(rate) - 0.31) < 1e-12, "poisoned duplicate affected the reconstructed rate")
    expect(rate_meta["history_samples"] == 16, "duplicate exposure leaked into certified history")


def fixture_s6_feature_time_alignment_and_mismatch_ledger() -> None:
    rows = [
        {
            "row_key": "aligned",
            "tick": 5,
            "ts_s": 0.10,
            "feature_ts_ns": 5 * DT_NS,
            "e_meas_m": 1.0,
            "certified_full": "True",
        },
        {
            "row_key": "mismatched",
            "tick": 5,
            "ts_s": 0.10,
            "feature_ts_ns": 9 * DT_NS,
            "e_meas_m": 0.9,
            "certified_full": "True",
        },
        {
            "row_key": "absent_feature_ts",
            "tick": 6,
            "ts_s": 0.12,
            "e_meas_m": 0.8,
            "certified_full": "True",
        },
    ]
    normalized, meta = normalize_rows_with_metadata(rows)
    expect(any(row["alignment_status"] == "MISMATCH" for row in normalized), "feature/control tick mismatch was not typed")
    expect(meta["mismatch_count"] == 1, "mismatch ledger did not publish the one bad alignment")
    expect(meta["absent_feature_ts_rows"][0]["row_key"] == "absent_feature_ts", "absent feature_ts_ns was not listed")
    absent = next(row for row in normalized if row["row_key"] == "absent_feature_ts")
    expect("feature_ts_ns" not in absent, "missing feature_ts_ns was synthesized")


def fixture_s7_blank_trace_value_incomplete() -> None:
    rows = synthetic_rows()
    rows[20]["clip_status"] = ""
    windows = detect_step_windows(rows)
    target = next(row for window in windows for row in window.rows if row["row_key"] == "syn_0020")
    expect(target["trace_complete"] is False, "blank trace value did not make the row incomplete")
    expect(target["blank_trace_fields"] == "clip_status", "blank trace field was not named")


def fixture_s8_sentinel_overlap_actual_cli(repo: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="reg1v23_s8_") as tmp:
        tmp_path = Path(tmp)
        input_csv = tmp_path / "input.csv"
        sentinel_csv = tmp_path / "sentinel.csv"
        write_csv(input_csv, synthetic_rows())
        write_csv(sentinel_csv, [{"row_key": "syn_0020"}])
        proc = run_generator_cli(repo, [
            "--input-csv", str(input_csv),
            "--out-dir", str(tmp_path / "out"),
            "--direction", "down",
            "--sentinel-keys-csv", str(sentinel_csv),
            "--sentinel-keys-digest", sentinel_digest(sentinel_csv),
            "--sentinel-keys-commit", "e73ca90",
        ])
    expect(proc.returncode != 0, "sentinel overlap CLI unexpectedly succeeded")
    expect("SENTINEL_OVERLAP" in (proc.stderr + proc.stdout), "sentinel overlap did not emit typed failure")


def fixture_s9_direction_argument_refusal(repo: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="reg1v23_s9_") as tmp:
        tmp_path = Path(tmp)
        input_csv = tmp_path / "input.csv"
        sentinel_csv = tmp_path / "sentinel.csv"
        write_csv(input_csv, synthetic_rows())
        write_csv(sentinel_csv, [{"row_key": "non_overlapping_sentinel"}])
        base = [
            "--input-csv", str(input_csv),
            "--out-dir", str(tmp_path / "out"),
            "--sentinel-keys-csv", str(sentinel_csv),
            "--sentinel-keys-digest", sentinel_digest(sentinel_csv),
            "--sentinel-keys-commit", "e73ca90",
        ]
        missing = run_generator_cli(repo, base)
        mismatched = run_generator_cli(repo, [*base, "--direction", "up"])
    expect(missing.returncode != 0 and "DIRECTION_REFUSED" in (missing.stderr + missing.stdout), "missing direction did not fail closed")
    expect(mismatched.returncode != 0 and "DIRECTION_REFUSED" in (mismatched.stderr + mismatched.stdout), "mismatched direction did not fail closed")


def fixture_s10_local_open_face_hidden_by_global_eligibility() -> None:
    best = {"g": 0.50, "tau_s": 0.40, "L_ticks": 10, "eligible": True, "ineligible_reason": ""}
    rows = [
        best,
        {"g": 0.45, "tau_s": 0.40, "L_ticks": 10, "eligible": True, "ineligible_reason": ""},
        {"g": 0.55, "tau_s": 0.40, "L_ticks": 10, "eligible": True, "ineligible_reason": ""},
        {"g": 0.50, "tau_s": 0.38, "L_ticks": 10, "eligible": False, "ineligible_reason": "HORIZON_LT_TAU"},
        {"g": 0.50, "tau_s": 0.42, "L_ticks": 10, "eligible": True, "ineligible_reason": ""},
        {"g": 0.50, "tau_s": 0.60, "L_ticks": 10, "eligible": True, "ineligible_reason": ""},
        {"g": 0.50, "tau_s": 0.40, "L_ticks": 9, "eligible": True, "ineligible_reason": ""},
        {"g": 0.50, "tau_s": 0.40, "L_ticks": 11, "eligible": True, "ineligible_reason": ""},
        {"g": 0.50, "tau_s": 0.40, "L_ticks": 20, "eligible": True, "ineligible_reason": ""},
    ]
    open_face, checks = local_open_face(best, rows)
    expect(open_face, "local open-face neighbor did not open the optimum")
    expect(any(c["face"] == "tau_minus" and c["open_reason"] == "HORIZON_LT_TAU" for c in checks), "local ineligible neighbor not published")


def fixture_s11_multiple_positive_minimizers_not_identified() -> None:
    rows = []
    for tick in range(20):
        rows.append({
            "event_id": "multi_min",
            "row_key": f"multi_min_{tick:03d}",
            "tick": tick,
            "relative_tick": tick,
            "ts_s": tick * 0.02,
            "feature_ts_ns": tick * DT_NS,
            "v_ref_up_mps": 0.0,
            "v_meas_mps": 0.0,
            "response_status": "VALID",
            "trace_complete": True,
        })
    window = StepWindow("multi_min", 0, "down", 0.0, 0.0, 0.0, list(range(20)), rows, "")
    fit = fit_response_model([window], {"down"})
    expect(fit["calibration_status"] == "NOT_IDENTIFIED", f"multiple minimizers should be NOT_IDENTIFIED, got {fit['calibration_status']}")
    expect(fit["positive_global_minimizer_count"] > 1, "distinct positive-g global minimizers were not published")
    expect(fit["prediction_equivalence_status"] == "NOT_EVALUATED_NO_PREREG_EQUIVALENCE", "prediction-equivalence status missing")


def fixture_s12_source_identity_split(repo: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    source_commit = source_bytes_commit(repo)
    dry = synthetic_dry_run(repo)
    prov = dry["provenance"]
    expect(prov["source_generator_commit"] == source_commit, "source_generator_commit did not bind the source-bytes commit")
    expect(prov["execution_tip"] == head, "execution_tip mismatch")
    expect(source_commit != head, "s12 requires an attestation child: source_generator_commit must differ from execution_tip")


def fixture_provenance_and_committed_bytes(repo: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    source_commit = source_bytes_commit(repo)
    dry = synthetic_dry_run(repo)
    prov = dry["provenance"]
    expect(prov["source_generator_path"] == SOURCE_GENERATOR_PATH, "source generator path not bound")
    expect(prov["source_generator_commit"] == source_commit, "source generator commit does not equal source-bytes commit")
    expect(prov["execution_tip"] == head, "execution tip mismatch")
    expect(prov["reg1_commit"] == "e73ca90", "REG-1v2.3 commit binding mismatch")
    expect(prov["input_digests"][0]["path"].startswith("synthetic://"), "synthetic dry-run should not bind A091 input")
    expect("attestation" in prov["attestation_policy"], "attestation child policy missing")
    expect(dry["packet_scope"] == "SYNTHETIC_DIAGNOSTIC", "synthetic packet scope enum missing")

    rows = committed_attestation_rows(repo, head, [SOURCE_GENERATOR_PATH])
    committed_sha = rows[0]["sha256_committed_bytes"]
    expect(rows[0]["path"] == SOURCE_GENERATOR_PATH, "attestation path mismatch")
    expect(rows[0]["reviewed_tip"] == head, "attestation reviewed tip mismatch")
    expect(len(committed_sha) == 64 and all(c in "0123456789abcdef" for c in committed_sha), "committed-byte digest is not a sha256 hex")


def run(repo: Path) -> int:
    fixtures: list[tuple[str, Callable[[], None]]] = [
        ("detector_floor_merge_and_windows", fixture_step_detector_floor_merge_and_windows),
        ("reconstruction_minima", fixture_response_reconstruction_minima),
        ("iv_v_response_reconstruction_v21_runtime_rules", fixture_response_reconstruction_v21_runtime_rules),
        ("s2_common_support_objective_bites", fixture_common_support_objective_bites),
        ("rows_scored_common_corruption_micro_fixture", fixture_rows_scored_common_corruption_stops),
        ("s1_post_lag_identifiability_gating", fixture_post_lag_identifiability_gating),
        ("null_model_and_grid", fixture_null_model_and_grid),
        ("s3_null_tie_not_null_calibrated", fixture_null_tie_not_null_calibrated),
        ("direction_inventory", fixture_direction_applicability),
        ("row_level_trace_happy_path", fixture_row_level_trace),
        ("sentinel_disjoint_detector_exclusion", fixture_sentinel_disjoint_exclusion),
        ("s4_strict_certified_full_parsing", fixture_s4_strict_certified_full_parsing),
        ("s5_poisoned_duplicate_first_wins", fixture_s5_poisoned_duplicate_first_wins),
        ("s6_feature_time_alignment_and_mismatch_ledger", fixture_s6_feature_time_alignment_and_mismatch_ledger),
        ("s7_blank_trace_value_incomplete", fixture_s7_blank_trace_value_incomplete),
        ("s8_sentinel_overlap_actual_cli", lambda: fixture_s8_sentinel_overlap_actual_cli(repo)),
        ("s9_direction_argument_refusal", lambda: fixture_s9_direction_argument_refusal(repo)),
        ("s10_local_open_face_hidden_by_global_eligibility", fixture_s10_local_open_face_hidden_by_global_eligibility),
        ("s11_multiple_positive_minimizers_not_identified", fixture_s11_multiple_positive_minimizers_not_identified),
        ("s12_source_identity_split", lambda: fixture_s12_source_identity_split(repo)),
        ("provenance_and_committed_bytes", lambda: fixture_provenance_and_committed_bytes(repo)),
    ]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    print("REG-1V2.3 CALIBRATION SOURCE FIXTURES")
    print(f"repo={repo}")
    print(f"head={head}")
    print("scope=DIAGNOSTIC synthetic dry-run only; no A091; no FlightSim/DCGame; no checkpoint; no intervention artifacts")
    failures: list[tuple[str, str]] = []
    for name, fn in fixtures:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {name}")
    print(f"SUMMARY passed={len(fixtures) - len(failures)} failed={len(failures)} total={len(fixtures)}")
    if failures:
        print("FAILURES_JSON=" + json.dumps(failures, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run(Path.cwd()))
