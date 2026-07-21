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
    SOURCE_GENERATOR_PATH,
    STEP_FLOOR_MPS,
    candidate_score,
    committed_attestation_rows,
    detect_step_windows,
    fit_response_model,
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
    expect(meta["fresh_tail_samples"] >= 4 and meta["fresh_tail_span_s"] >= 0.15, "fresh-tail minima were not met")
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


def fixture_null_model_and_grid() -> None:
    windows = detect_step_windows(synthetic_null_rows())
    fit = fit_response_model(windows)
    expect(fit["candidate_count"] == 31 * 60 * 26, "grid candidate count mismatch")
    expect(fit["null_model_score"] is not None, "null-model score missing")
    expect(fit["calibration_status"] == "NULL_CALIBRATED", f"zero response should be NULL_CALIBRATED, got {fit['calibration_status']}")
    expect(float(fit["best"]["g"]) == 0.0, "null-calibrated best did not land at g=0")


def fixture_identifiability_gating() -> None:
    windows = detect_step_windows(synthetic_rows())
    high_tau = candidate_score(windows, Candidate(g=0.5, tau_s=1.20, lag_ticks=0))
    expect(high_tau["eligible"] is False, "tau longer than observed horizon should be ineligible")
    expect(high_tau["ineligible_reason"] == "HORIZON_LT_TAU", "horizon gate reason mismatch")
    high_lag = candidate_score(windows, Candidate(g=0.5, tau_s=0.20, lag_ticks=25))
    expect("eligible" in high_lag and "rows_used" in high_lag, "lag eligibility row missing required fields")


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


def fixture_provenance_and_committed_bytes(repo: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dry = synthetic_dry_run(repo)
    prov = dry["provenance"]
    expect(prov["source_generator_path"] == SOURCE_GENERATOR_PATH, "source generator path not bound")
    expect(prov["source_generator_commit"] == head, "source generator commit does not equal execution tip")
    expect(prov["execution_tip"] == head, "execution tip mismatch")
    expect(prov["reg1_commit"] == "62c9648", "REG-1v2.1 commit binding mismatch")
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
        ("null_model_and_grid", fixture_null_model_and_grid),
        ("identifiability_gating", fixture_identifiability_gating),
        ("direction_applicability", fixture_direction_applicability),
        ("row_level_trace", fixture_row_level_trace),
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
