"""Synthetic fixtures for the REG-1v2 calibration source generator."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tuning.reg1v2_calibration_source_generator import (
    Candidate,
    RowsScoredCommonMismatch,
    SOURCE_GENERATOR_PATH,
    STEP_FLOOR_MPS,
    StepWindow,
    assert_rows_scored_common,
    candidate_score,
    committed_attestation_rows,
    detect_step_windows,
    fit_response_model,
    predict_window,
    reconstruct_v_full_raw,
    synthetic_dry_run,
    synthetic_null_rows,
    synthetic_rows,
)


class FixtureFailure(AssertionError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureFailure(message)


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
        dense.append({"tick": i, "ts_s": ts, "e_meas_m": e_meas, "certified_full": True})
    dense_rate, dense_status, dense_meta = reconstruct_v_full_raw(dense, 0.48)
    expect(dense_status == "VALID", f"dense v2.1 reconstruction invalid: {dense_status}")
    expect(abs(float(dense_rate) - 0.35) < 1e-12, "dense fixture did not use the last-12 cap")
    expect(dense_meta["history_samples"] == 25 and dense_meta["recent_samples"] == 12, "dense fixture did not expose >12 history")

    gapped: list[dict[str, object]] = []
    for i, ts in enumerate([0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34]):
        gapped.append({"tick": i, "ts_s": ts, "e_meas_m": 3.0 - 0.65 * ts, "certified_full": True})
    for i, ts in enumerate([0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68], start=20):
        gapped.append({"tick": i, "ts_s": ts, "e_meas_m": 1.2 - 0.12 * (ts - 0.50), "certified_full": True})
    gap_rate, gap_status, gap_meta = reconstruct_v_full_raw(gapped, 0.68)
    expect(gap_status == "VALID", f"gapped v2.1 reconstruction invalid: {gap_status}")
    expect(abs(float(gap_rate) - 0.12) < 1e-12, "gapped fixture fitted across an outage")
    expect(gap_meta["history_samples"] == 19 and gap_meta["fresh_tail_samples"] == 10, "fresh-tail outage accounting drifted")

    duplicate: list[dict[str, object]] = []
    for i in range(18):
        ts = i * 0.02
        duplicate.append({"tick": i, "ts_s": ts, "e_meas_m": 1.5 - 0.22 * ts, "certified_full": True})
        if i == 10:
            duplicate.append({"tick": 1000, "ts_s": ts, "e_meas_m": 99.0, "certified_full": True})
    dup_rate, dup_status, dup_meta = reconstruct_v_full_raw(duplicate, 0.34)
    expect(dup_status == "VALID", f"duplicate v2.1 reconstruction invalid: {dup_status}")
    expect(abs(float(dup_rate) - 0.22) < 1e-12, "duplicate timestamp was treated as a new exposure")
    expect(dup_meta["history_samples"] == 18, "duplicate timestamp was not rejected from unique history")

    subspan = [
        {"tick": 0, "ts_s": 0.00, "e_meas_m": 1.00, "certified_full": True},
        {"tick": 1, "ts_s": 0.02, "e_meas_m": 0.99, "certified_full": True},
        {"tick": 2, "ts_s": 0.04, "e_meas_m": 0.98, "certified_full": True},
        {"tick": 3, "ts_s": 0.06, "e_meas_m": 0.97, "certified_full": True},
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


def fixture_provenance_and_committed_bytes(repo: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dry = synthetic_dry_run(repo)
    prov = dry["provenance"]
    expect(prov["source_generator_path"] == SOURCE_GENERATOR_PATH, "source generator path not bound")
    expect(prov["source_generator_commit"] == head, "source generator commit does not equal execution tip")
    expect(prov["execution_tip"] == head, "execution tip mismatch")
    expect(prov["reg1_commit"] == "ee0bb6a", "REG-1v2.2 commit binding mismatch")
    expect(prov["input_digests"][0]["path"].startswith("synthetic://"), "synthetic dry-run should not bind A091 input")
    expect("attestation" in prov["attestation_policy"], "attestation child policy missing")

    rows = committed_attestation_rows(repo, head, [SOURCE_GENERATOR_PATH])
    committed_sha = rows[0]["sha256_committed_bytes"]
    expect(rows[0]["path"] == SOURCE_GENERATOR_PATH, "attestation path mismatch")
    expect(rows[0]["reviewed_tip"] == head, "attestation reviewed tip mismatch")
    expect(len(committed_sha) == 64 and all(c in "0123456789abcdef" for c in committed_sha), "committed-byte digest is not a sha256 hex")


def run(repo: Path) -> int:
    fixtures: list[tuple[str, Callable[[], None]]] = [
        ("step_detector_floor_merge_and_windows", fixture_step_detector_floor_merge_and_windows),
        ("response_reconstruction_minima", fixture_response_reconstruction_minima),
        ("response_reconstruction_v21_runtime_rules", fixture_response_reconstruction_v21_runtime_rules),
        ("common_support_objective_bites", fixture_common_support_objective_bites),
        ("rows_scored_common_corruption_stops", fixture_rows_scored_common_corruption_stops),
        ("post_lag_identifiability_gating", fixture_post_lag_identifiability_gating),
        ("null_model_and_grid", fixture_null_model_and_grid),
        ("null_tie_not_null_calibrated", fixture_null_tie_not_null_calibrated),
        ("direction_applicability", fixture_direction_applicability),
        ("row_level_trace", fixture_row_level_trace),
        ("sentinel_disjoint_exclusion", fixture_sentinel_disjoint_exclusion),
        ("provenance_and_committed_bytes", lambda: fixture_provenance_and_committed_bytes(repo)),
    ]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    print("REG-1V2 CALIBRATION SOURCE FIXTURES")
    print(f"repo={repo}")
    print(f"head={head}")
    print("scope=DIAGNOSTIC synthetic dry-run only; no A091; no FlightSim/DCGame; no intervention artifacts")
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
